"""微博发布适配器"""

from pathlib import Path
from loguru import logger

from .base import BasePublisher, PublishResult
from ..utils.opencli import run, OpenCLIError


class WeiboPublisher(BasePublisher):
    """微博发布"""

    def __init__(self):
        super().__init__("weibo")

    def publish(self, draft_path: Path, title: str, content: str) -> PublishResult:
        try:
            import re
            body = re.sub(r"^标题[：:][^\n]*\n?", "", content).strip()
            # 微博 140 字限制
            if len(body) > 140:
                body = body[:137] + "..."

            logger.info(f"[weibo] 发布中: {body[:30]}...")
            # TODO: 验证 opencli weibo publish 命令
            run("weibo", "publish", body, timeout=30)
            return PublishResult(success=True, platform=self.platform)
        except Exception as e:
            logger.error(f"[weibo] 发布失败: {e}")
            return PublishResult(success=False, platform=self.platform, error=str(e))
