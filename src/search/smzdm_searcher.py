"""什么值得买搜索适配器"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class SmzdmSearcher(BaseSearcher):
    """什么值得买搜索"""

    def __init__(self):
        super().__init__("smzdm")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        for kw in keywords[:3]:
            try:
                results = run("smzdm", "search", kw, "--limit", "10", "-f", "json", timeout=45)
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            title = item.get("title", item.get("article_title", ""))
                            topics.append(Topic(
                                title=title,
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("worthy", 0) or 0)),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError as e:
                logger.warning(f"[smzdm] search '{kw}' 失败: {e}")

        logger.info(f"[smzdm] 搜索完成: {len(topics)} 个话题")
        return topics
