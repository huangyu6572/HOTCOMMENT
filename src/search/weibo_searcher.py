"""
微博搜索适配器

- opencli weibo hot → 获取热榜
- opencli weibo search → 按关键词搜索
- opencli browser extract → 提取评论（兜底）
"""

from loguru import logger

from .base import BaseSearcher, Topic, Comment
from ..utils.opencli import run, OpenCLIError


class WeiboSearcher(BaseSearcher):
    """微博搜索"""

    def __init__(self):
        super().__init__("weibo")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        # 1. 先获取热榜
        try:
            hot_list = run("weibo", "hot", "--limit", "20", "-f", "json", timeout=45)
            if isinstance(hot_list, list):
                for item in hot_list:
                    if isinstance(item, dict):
                        topics.append(Topic(
                            title=item.get("title", item.get("word", "")),
                            url=item.get("url", ""),
                            hot_score=float(item.get("hot_score", item.get("num", 0))),
                            channel=self.channel,
                            raw_data=item,
                        ))
        except OpenCLIError as e:
            logger.warning(f"[weibo] hot 获取失败: {e}")

        # 2. 按关键词搜索补充
        for kw in keywords[:3]:  # 最多搜索3个关键词
            try:
                results = run("weibo", "search", kw, "--limit", "10", "-f", "json", timeout=45)
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            topics.append(Topic(
                                title=item.get("title", item.get("text", "")),
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("reposts_count", 0))),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError as e:
                logger.warning(f"[weibo] search '{kw}' 失败: {e}")

        # 3. 按关键词过滤热榜话题
        matched = [t for t in topics if self._match_keywords(t.title, keywords)]
        if matched:
            topics = matched

        logger.info(f"[weibo] 搜索完成: {len(topics)} 个话题")
        return topics

    @staticmethod
    def _match_keywords(title: str, keywords: list[str]) -> bool:
        """检查标题是否包含任意关键词"""
        title_lower = title.lower()
        return any(kw.lower() in title_lower for kw in keywords)
