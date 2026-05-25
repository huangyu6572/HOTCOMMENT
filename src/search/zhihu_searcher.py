"""知乎搜索适配器"""

from loguru import logger
from .base import BaseSearcher, Topic
from ..utils.opencli import run, OpenCLIError


class ZhihuSearcher(BaseSearcher):
    """知乎搜索"""

    def __init__(self):
        super().__init__("zhihu")

    def search(self, keywords: list[str]) -> list[Topic]:
        topics = []

        # 1. 热榜
        try:
            hot_list = run("zhihu", "hot", "--limit", "20", "-f", "json", timeout=45)
            if isinstance(hot_list, list):
                for item in hot_list:
                    if isinstance(item, dict):
                        title = item.get("title", item.get("target", {}).get("title", ""))
                        topics.append(Topic(
                            title=title,
                            url=item.get("url", ""),
                            hot_score=float(item.get("hot_score", item.get("detail_text", 0) or 0)),
                            channel=self.channel,
                            raw_data=item,
                        ))
        except OpenCLIError as e:
            logger.warning(f"[zhihu] hot 失败: {e}")

        # 2. 关键词搜索
        for kw in keywords[:3]:
            try:
                results = run("zhihu", "search", kw, "--limit", "5", "-f", "json", timeout=45)
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            topics.append(Topic(
                                title=item.get("title", ""),
                                url=item.get("url", ""),
                                hot_score=float(item.get("hot_score", item.get("answer_count", 0))),
                                channel=self.channel,
                                raw_data=item,
                            ))
            except OpenCLIError as e:
                logger.warning(f"[zhihu] search '{kw}' 失败: {e}")

        # 过滤
        matched = [t for t in topics if any(kw.lower() in t.title.lower() for kw in keywords)]
        if matched:
            topics = matched

        logger.info(f"[zhihu] 搜索完成: {len(topics)} 个话题")
        return topics
