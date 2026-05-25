"""知乎发布适配器"""

from pathlib import Path
from loguru import logger

from .base import BasePublisher, PublishResult
from ..utils.opencli import run, OpenCLIError


class ZhihuPublisher(BasePublisher):
    """知乎发布（回答/文章）"""

    def __init__(self):
        super().__init__("zhihu")

    def publish(self, draft_path: Path, title: str, content: str) -> PublishResult:
        try:
            logger.info(f"[zhihu] 发布中: {title[:30]}...")
            # TODO: 验证 opencli zhihu 的发布命令
            # 知乎可能需指定问题 ID 才能发布回答
            run("zhihu", "answer", content, timeout=30)
            return PublishResult(success=True, platform=self.platform)
        except Exception as e:
            logger.error(f"[zhihu] 发布失败: {e}")
            return PublishResult(success=False, platform=self.platform, error=str(e))
