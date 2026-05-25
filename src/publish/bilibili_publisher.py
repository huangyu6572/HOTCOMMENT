"""B站发布适配器"""

from pathlib import Path
from loguru import logger

from .base import BasePublisher, PublishResult


class BilibiliPublisher(BasePublisher):
    """B站发布（专栏）"""

    def __init__(self):
        super().__init__("bilibili")

    def publish(self, draft_path: Path, title: str, content: str) -> PublishResult:
        logger.info(f"[bilibili] B站专栏发布暂未实现，请手动发布")
        return PublishResult(
            success=False,
            platform=self.platform,
            error="B站发布暂未实现，需通过 browser 原语操作创作中心",
        )
