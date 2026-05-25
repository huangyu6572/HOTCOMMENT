"""Reddit 搜索适配器"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class RedditSearcher(BaseSearcher):
    """Reddit 搜索"""

    def __init__(self):
        super().__init__("reddit")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        # hot
        try:
            hot = run("reddit", "hot", "--limit", "20", "-f", "json", timeout=45)
            if isinstance(hot, list):
                for item in hot:
                    if isinstance(item, dict):
                        topics.append(Topic(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            hot_score=float(item.get("hot_score", item.get("score", 0))),
                            channel=self.channel,
                            raw_data=item,
                        ))
        except OpenCLIError as e:
            logger.warning(f"[reddit] hot 失败: {e}")

        # 搜索
        for kw in keywords[:2]:
            try:
                results = run("reddit", "search", kw, "--limit", "5", "-f", "json", timeout=45)
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            topics.append(Topic(
                                title=item.get("title", ""),
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("score", 0))),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError:
                pass

        logger.info(f"[reddit] 搜索完成: {len(topics)} 个话题")
        return topics
