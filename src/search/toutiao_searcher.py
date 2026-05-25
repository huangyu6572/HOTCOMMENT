"""今日头条搜索适配器 — 🌐 公开，无需登录"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class ToutiaoSearcher(BaseSearcher):
    """今日头条搜索"""

    def __init__(self):
        super().__init__("toutiao")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        # 热榜
        try:
            hot_list = run("toutiao", "hot", "--limit", "20", "-f", "json", timeout=30)
            if isinstance(hot_list, list):
                for item in hot_list:
                    if isinstance(item, dict):
                        topics.append(Topic(
                            title=item.get("title", ""),
                            url=item.get("url", ""),
                            hot_score=float(item.get("hot_score", item.get("hot_value", 0))),
                            channel=self.channel,
                            raw_data=item,
                        ))
        except OpenCLIError as e:
            logger.warning(f"[toutiao] hot 失败: {e}")

        # 过滤
        matched = [t for t in topics if any(kw.lower() in t.title.lower() for kw in keywords)]
        if matched:
            topics = matched

        logger.info(f"[toutiao] 搜索完成: {len(topics)} 个话题")
        return topics
