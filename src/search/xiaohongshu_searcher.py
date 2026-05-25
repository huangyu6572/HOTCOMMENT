"""小红书搜索适配器"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class XiaohongshuSearcher(BaseSearcher):
    """小红书搜索"""

    def __init__(self):
        super().__init__("xiaohongshu")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        for kw in keywords[:3]:
            try:
                results = run(
                    "xiaohongshu", "search", kw, "--limit", "10", "-f", "json",
                    timeout=45,
                )
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            title = item.get("title", item.get("note_title", item.get("display_title", "")))
                            topics.append(Topic(
                                title=title,
                                url=item.get("url", item.get("note_id", "")),
                                hot_score=float(item.get("hot_score", item.get("likes", item.get("liked_count", 0)))),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError as e:
                logger.warning(f"[xiaohongshu] search '{kw}' 失败: {e}")

        # 也尝试 feed 流
        try:
            feed = run("xiaohongshu", "feed", "--limit", "10", "-f", "json", timeout=45)
            if isinstance(feed, list):
                for item in feed:
                    if isinstance(item, dict):
                        title = item.get("title", item.get("note_title", ""))
                        if any(kw.lower() in title.lower() for kw in keywords):
                            topics.append(Topic(
                                title=title,
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("likes", 0))),
                                channel=self.channel,
                                raw_data=item,
                            ))
        except OpenCLIError:
            pass  # feed 可能失败，不算错误

        logger.info(f"[xiaohongshu] 搜索完成: {len(topics)} 个话题")
        return topics
