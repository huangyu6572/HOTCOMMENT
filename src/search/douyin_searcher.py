"""抖音搜索适配器"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class DouyinSearcher(BaseSearcher):
    """抖音搜索"""

    def __init__(self):
        super().__init__("douyin")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        # douyin 不支持 search 命令，用 hashtag 热点词兜底
        try:
            results = run("douyin", "hashtag", "hot", "--limit", "20", "-f", "json", timeout=45)
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict):
                        title = item.get("title", item.get("name", item.get("desc", item.get("word", ""))))
                        view_count = item.get("view_count", item.get("hot_value", 0))
                        topics.append(Topic(
                            title=title,
                            url=item.get("url", ""),
                            hot_score=float(view_count) if view_count else 0,
                            channel=self.channel,
                            raw_data=item,
                        ))
        except OpenCLIError as e:
            logger.warning(f"[douyin] hashtag hot 失败: {e}")

        # 按关键词过滤
        matched = [t for t in topics if any(kw.lower() in t.title.lower() for kw in keywords)]
        if matched:
            topics = matched

        logger.info(f"[douyin] 搜索完成: {len(topics)} 个话题")
        return topics
