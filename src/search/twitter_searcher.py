"""Twitter/X 搜索适配器"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class TwitterSearcher(BaseSearcher):
    """Twitter/X 搜索"""

    def __init__(self):
        super().__init__("twitter")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        # trending
        try:
            trending = run("twitter", "trending", "--limit", "20", "-f", "json", timeout=45)
            if isinstance(trending, list):
                for item in trending:
                    if isinstance(item, dict):
                        topics.append(Topic(
                            title=item.get("title", item.get("name", item.get("trend", ""))),
                            url=item.get("url", ""),
                            hot_score=float(item.get("hot_score", item.get("tweet_volume", 0) or 0)),
                            channel=self.channel,
                            raw_data=item,
                        ))
        except OpenCLIError as e:
            logger.warning(f"[twitter] trending 失败: {e}")

        # 搜索
        for kw in keywords[:2]:
            try:
                results = run("twitter", "search", kw, "--limit", "5", "-f", "json", timeout=45)
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            topics.append(Topic(
                                title=item.get("title", item.get("text", ""))[:100],
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("likes", 0))),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError:
                pass

        logger.info(f"[twitter] 搜索完成: {len(topics)} 个话题")
        return topics
