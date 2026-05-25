"""
搜索调度器

并行调用所有启用的搜索渠道，合并去重排序
"""

import asyncio
from dataclasses import dataclass
from loguru import logger

from .base import BaseSearcher, Topic
from ..personas.manager import PersonaManager
from ..utils.file_store import TopicsCache


@dataclass
class SearchResult:
    """搜索汇总结果"""
    topics: list[Topic]         # 排序后的所有话题
    channel_stats: dict[str, int]  # 各渠道话题数


class SearchEngine:
    """多渠道搜索调度器"""

    def __init__(self, persona_manager: PersonaManager, cache: TopicsCache):
        self.persona_manager = persona_manager
        self.cache = cache
        self._searchers: dict[str, BaseSearcher] = {}

    def register(self, searcher: BaseSearcher):
        """注册搜索适配器"""
        self._searchers[searcher.name()] = searcher
        logger.debug(f"注册搜索渠道: {searcher.name()}")

    async def search(
        self,
        keywords: list[str],
        enabled_channels: list[str],
        max_per_channel: int = 10,
    ) -> SearchResult:
        """
        并行执行多渠道搜索

        Args:
            keywords: 搜索关键词
            enabled_channels: 启用的渠道列表
            max_per_channel: 每个渠道最大话题数

        Returns:
            SearchResult
        """
        if not keywords:
            logger.warning("无搜索关键词，跳过搜索")
            return SearchResult(topics=[], channel_stats={})

        logger.info(f"开始 {len(enabled_channels)} 渠道并行搜索，关键词: {keywords}")

        tasks = []
        for channel in enabled_channels:
            searcher = self._searchers.get(channel)
            if searcher is None:
                logger.warning(f"未注册的渠道: {channel}，跳过")
                continue
            tasks.append(self._search_one(searcher, keywords, max_per_channel))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_topics: list[Topic] = []
        channel_stats: dict[str, int] = {}

        for i, result in enumerate(results):
            channel = enabled_channels[i] if i < len(enabled_channels) else "unknown"
            if isinstance(result, Exception):
                logger.error(f"渠道 {channel} 搜索失败: {result}")
                channel_stats[channel] = 0
                continue

            topics: list[Topic] = result or []
            channel_stats[channel] = len(topics)
            all_topics.extend(topics)

        # 去重
        unique_topics = self._deduplicate(all_topics)

        # 按热度排序
        unique_topics.sort(key=lambda t: t.hot_score, reverse=True)

        logger.info(
            f"搜索完成: {sum(channel_stats.values())} 个话题 → "
            f"去重后 {len(unique_topics)} 个"
        )

        return SearchResult(topics=unique_topics, channel_stats=channel_stats)

    async def _search_one(
        self,
        searcher: BaseSearcher,
        keywords: list[str],
        max_topics: int,
    ) -> list[Topic]:
        """执行单个渠道搜索（在线程池中运行同步代码）"""
        loop = asyncio.get_running_loop()
        topics = await loop.run_in_executor(None, searcher.search, keywords)
        return topics[:max_topics]

    def _deduplicate(self, topics: list[Topic]) -> list[Topic]:
        """去重：同一标题+渠道只保留一个"""
        seen = set()
        unique = []
        for t in topics:
            key = (t.title.strip(), t.channel)
            if key not in seen:
                seen.add(key)
                unique.append(t)
        return unique
