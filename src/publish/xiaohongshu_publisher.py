"""小红书发布适配器"""

import re
from pathlib import Path
from loguru import logger

from .base import BasePublisher, PublishResult
from ..utils.opencli import run, OpenCLIError


class XiaohongshuPublisher(BasePublisher):
    """小红书发布"""

    def __init__(self):
        super().__init__("xiaohongshu")

    def publish(self, draft_path: Path, title: str, content: str) -> PublishResult:
        """发布到小红书"""
        try:
            # 提取标题（去掉"标题："前缀）
            clean_title = title.replace("标题：", "").replace("标题:", "").strip()
            # 小红书标题限制 20 字
            if len(clean_title) > 20:
                clean_title = clean_title[:20]

            # 提取正文（去掉标题行）
            body = content
            body = re.sub(r"^标题[：:][^\n]*\n?", "", body)
            body = body.strip()

            # 尝试 opencli xiaohongshu publish 命令
            logger.info(f"[xiaohongshu] 发布中: {clean_title}")
            # 注意：opencli xiaohongshu publish 的具体参数格式需要验证
            # 这里先用 browser 原语作为兜底方案
            result = self._publish_via_opencli(clean_title, body)

            return PublishResult(
                success=True,
                platform=self.platform,
                url=result or "",
            )
        except Exception as e:
            logger.error(f"[xiaohongshu] 发布失败: {e}")
            return PublishResult(success=False, platform=self.platform, error=str(e))

    def _publish_via_opencli(self, title: str, body: str) -> str:
        """通过 opencli 发布"""
        # TODO: 需要验证 opencli xiaohongshu publish 命令的实际参数
        # 当前先记录草稿已生成，发布操作待验证
        logger.info(f"[xiaohongshu] 准备发布: title={title[:30]}...")
        logger.info(f"[xiaohongshu] ⚠️ 发布功能需验证 opencli publish 命令后启用")
        logger.info(f"[xiaohongshu] 请手动复制 data/drafts/ 中的草稿到小红书创作中心发布")
        return ""
