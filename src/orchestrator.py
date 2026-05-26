"""
核心编排引擎

Orchestrator 串联完整流程：
  搜索 → 评论采集 → AI 分析 → 内容生成 → 审阅 → 发布
"""

import asyncio
import os
from pathlib import Path
from loguru import logger

from .personas.manager import PersonaManager
from .intent_parser import parse_intent, Intent
from .search.engine import SearchEngine
from .search.weibo_searcher import WeiboSearcher
from .search.zhihu_searcher import ZhihuSearcher
from .search.bilibili_searcher import BilibiliSearcher
from .search.xiaohongshu_searcher import XiaohongshuSearcher
from .search.douyin_searcher import DouyinSearcher
from .search.toutiao_searcher import ToutiaoSearcher
from .search.twitter_searcher import TwitterSearcher
from .search.reddit_searcher import RedditSearcher
from .search.smzdm_searcher import SmzdmSearcher
from .search.base import Topic, Comment
from .ai.comment_analyzer import CommentAnalyzer
from .ai.content_generator import ContentGenerator
from .ai.quality_checker import QualityChecker
from .publish.engine import PublishEngine
from .reports.daily_digest import generate_daily_report
from .utils.file_store import PublishedStore, TopicsCache
from .utils.opencli import check_login


class Orchestrator:
    """核心编排器"""

    def __init__(self, config_dir: Path, data_dir: Path):
        self.config_dir = config_dir
        self.data_dir = data_dir

        # 加载配置
        import yaml
        settings_file = config_dir / "settings.yaml"
        self.settings = yaml.safe_load(settings_file.read_text(encoding="utf-8")) if settings_file.exists() else {}

        # 初始化组件
        self.persona_manager = PersonaManager(config_dir)
        self.topics_cache = TopicsCache(data_dir)
        self.published_store = PublishedStore(data_dir)

        # 搜索引擎
        self.search_engine = SearchEngine(self.persona_manager, self.topics_cache)
        self._register_searchers()

        # AI
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        self.comment_analyzer = CommentAnalyzer(
            api_key=api_key,
            prompt_path=config_dir / "prompts" / "comment_analysis.txt",
            model=self.settings.get("ai", {}).get("model", "deepseek-chat"),
        )
        self.content_generator = ContentGenerator(
            api_key=api_key,
            prompt_path=config_dir / "prompts" / "content_generation.txt",
            output_dir=data_dir / "drafts",
            model=self.settings.get("ai", {}).get("model", "deepseek-chat"),
        )
        self.quality_checker = QualityChecker()

        # 发布
        self.publish_engine = PublishEngine(self.published_store)

    def _register_searchers(self):
        """注册所有搜索渠道"""
        searchers = [
            WeiboSearcher(), ZhihuSearcher(), BilibiliSearcher(),
            XiaohongshuSearcher(), DouyinSearcher(), ToutiaoSearcher(),
            TwitterSearcher(), RedditSearcher(), SmzdmSearcher(),
        ]
        for s in searchers:
            self.search_engine.register(s)

    async def run(self, keyword_override: str = "", platform_override: str = "", persona_override: str = ""):
        """
        执行完整流程

        Args:
            keyword_override: 命令行覆盖的搜索关键词
            platform_override: 命令行覆盖的发布平台
            persona_override: 命令行覆盖的人设
        """
        # 合并命令行覆盖到 settings
        settings = dict(self.settings)
        if keyword_override:
            settings["keyword"] = keyword_override
        if persona_override:
            settings["persona"] = persona_override
        if platform_override:
            settings["publish"] = {**settings.get("publish", {}), "platforms": [platform_override]}

        # 获取人设
        persona = self.persona_manager.get_active(settings)
        if not persona:
            logger.error("无法加载人设，请检查配置")
            return

        persona_name = persona.get("name", "?")
        target_platforms = settings.get("publish", {}).get("platforms", ["xiaohongshu"])

        logger.info("=" * 50)
        logger.info(f"🚀 HotCommentHub | 人设: {persona_name} | 目标: {', '.join(target_platforms)}")
        logger.info("=" * 50)

        # Phase 1: 搜索
        logger.info("🔍 [1/4] 多渠道搜索中...")
        keywords = self.persona_manager.get_search_keywords(settings)
        if not keywords:
            logger.error("无搜索关键词，请配置 keyword 或人设 search_keywords")
            return

        enabled_channels = settings.get("channels", {}).get("enabled", ["weibo", "zhihu"])
        max_per_channel = settings.get("channels", {}).get("max_topics_per_channel", 10)

        search_result = await self.search_engine.search(keywords, enabled_channels, max_per_channel)

        for channel, count in search_result.channel_stats.items():
            logger.info(f"  {'✅' if count > 0 else '⚠️ '} {channel:<10} 找到 {count} 个话题")

        if not search_result.topics:
            logger.warning("未找到相关话题，结束")
            return

        # Phase 2: 精选话题
        logger.info(f"📊 [2/4] 精选 {min(5, len(search_result.topics))} 个高价值话题")
        top_topics = search_result.topics[:5]
        for t in top_topics:
            stars = "🔥" * min(5, max(1, int(t.hot_score / 1000)))
            logger.info(f"  {stars} {t.title[:50]} ({t.channel})")

        # Phase 3: AI 分析
        logger.info("🧠 [3/4] AI 深度分析评论中...")
        analyses = {}
        for topic in top_topics:
            # 无评论时用话题热度构造基础分析数据，让 AI 仍有上下文
            if not topic.comments:
                logger.info(f"  无评论数据，用热度值构造分析上下文: {topic.title[:40]}")
                topic.comments = [
                    Comment(content=f"[热度] 该话题热度值为 {topic.hot_score}", likes=0),
                    Comment(content=f"[来源] 来自 {topic.channel} 平台", likes=0),
                    Comment(content=f"[摘要] {topic.title}", likes=0),
                ]
            analysis = self.comment_analyzer.analyze(
                topic_title=topic.title,
                topic_channel=topic.channel,
                topic_hot_score=topic.hot_score,
                comments=topic.comments,
            )
            analyses[topic.title] = analysis
        logger.info("  ✅ 分析完成")

        # Phase 4: 内容生成
        logger.info("✍️  [4/4] 生成草稿...")
        angles = settings.get("generation", {}).get("angles", ["event_report", "opinion", "guide"])

        all_drafts = []
        for topic in top_topics[:3]:  # 最多 3 个话题
            analysis = analyses.get(topic.title, {})
            # 只要 AI 返回了结果（有 narrative 或 main_opinions 或 controversy），都尝试生成
            if not analysis.get("main_opinions") and not analysis.get("narrative") and not analysis.get("controversy"):
                logger.warning(f"  跳过无分析结果的话题: {topic.title[:40]}")
                continue

            drafts = self.content_generator.generate(
                persona=persona,
                topic_title=topic.title,
                topic_channel=topic.channel,
                analysis=analysis,
                angles=angles,
            )
            for d in drafts:
                logger.info(f"  ✅ {d.name}")
            all_drafts.extend(drafts)

        logger.info("=" * 50)
        if all_drafts:
            logger.info("📋 草稿已生成，请审阅:")
            for i, d in enumerate(all_drafts, 1):
                logger.info(f"  [{i}] {d}")
            logger.info("")
            logger.info("  python main.py review          # 交互审阅")
            logger.info("  python main.py publish --all    # 发布所有通过")
        else:
            logger.info("⚠️  未生成草稿，可能是话题不适合或 AI 调用失败")

        # 生成每日报告
        report_path = generate_daily_report(
            self.data_dir,
            search_result={"channel_stats": search_result.channel_stats},
        )

        return {
            "topics": search_result.topics,
            "drafts": all_drafts,
            "report": report_path,
        }

    def review_drafts(self) -> list[Path]:
        """获取所有待审阅草稿"""
        drafts_dir = self.data_dir / "drafts"
        if not drafts_dir.exists():
            return []
        return sorted(drafts_dir.glob("*.md"), key=lambda f: f.name, reverse=True)

    def publish_draft(self, draft_index: int) -> list:
        """发布指定草稿"""
        drafts = self.review_drafts()
        if not drafts or draft_index < 1 or draft_index > len(drafts):
            logger.error(f"无效的草稿序号: {draft_index}")
            return []

        draft = drafts[draft_index - 1]
        logger.info(f"发布草稿: {draft.name}")

        publish_config = self.settings.get("publish", {})
        platforms = publish_config.get("platforms", ["xiaohongshu"])
        max_per_day = publish_config.get("max_per_day", 4)
        min_interval = publish_config.get("min_interval_minutes", 120)

        return self.publish_engine.publish(draft, platforms, max_per_day, min_interval)

    def publish_all(self) -> list:
        """发布所有待审阅草稿"""
        drafts = self.review_drafts()
        results = []
        for i, _ in enumerate(drafts, 1):
            results.append(self.publish_draft(i))
        return results

    def check_all_logins(self) -> dict[str, bool]:
        """检查所有平台登录态"""
        platforms = ["weibo", "zhihu", "bilibili", "xiaohongshu", "douyin", "twitter", "reddit", "smzdm"]
        results = {}
        for p in platforms:
            results[p] = check_login(p)
        return results

    def get_status(self) -> dict:
        """获取今日统计"""
        drafts = len(self.review_drafts())
        published = self.published_store.count_today()
        return {
            "drafts": drafts,
            "published_today": published,
            "persona": self.settings.get("persona", "?"),
        }
