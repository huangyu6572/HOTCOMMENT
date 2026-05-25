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

        for kw in keywords[:3]:
            try:
                # 抖音搜索：先搜内容
                results = run("douyin", "search", kw, "--limit", "10", "-f", "json", timeout=45)
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            topics.append(Topic(
                                title=item.get("title", item.get("desc", "")),
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("statistics", {}).get("digg_count", 0))),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError as e:
                logger.warning(f"[douyin] search '{kw}' 失败: {e}")

        logger.info(f"[douyin] 搜索完成: {len(topics)} 个话题")
        return topics
