"""
发布调度器

管理多平台发布，检查发布频率限制
"""

import re
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from .base import BasePublisher, PublishResult
from .xhs_browser_publisher import XHSBrowserPublisher
from .weibo_publisher import WeiboPublisher
from .bilibili_publisher import BilibiliPublisher
from .zhihu_publisher import ZhihuPublisher
from ..utils.file_store import PublishedStore


class PublishEngine:
    """发布调度器"""

    def __init__(self, published_store: PublishedStore):
        self.store = published_store
        self._publishers: dict[str, BasePublisher] = {}

        # 注册默认发布器
        self.register(XHSBrowserPublisher())
        self.register(WeiboPublisher())
        self.register(BilibiliPublisher())
        self.register(ZhihuPublisher())

    def register(self, publisher: BasePublisher):
        """注册发布适配器"""
        self._publishers[publisher.name()] = publisher

    def publish(
        self,
        draft_path: Path,
        platforms: list[str],
        max_per_day: int = 4,
        min_interval_minutes: int = 120,
    ) -> list[PublishResult]:
        """
        发布到多个平台

        Args:
            draft_path: 草稿文件路径
            platforms: 目标平台列表
            max_per_day: 每天最大发布数
            min_interval_minutes: 两篇最小间隔（分钟）

        Returns:
            各平台发布结果列表
        """
        # 读取草稿
        content = draft_path.read_text(encoding="utf-8")

        # 提取标题：优先匹配 "标题：xxx" 格式，其次 "# xxx" 格式
        title = ""
        match = re.match(r"^标题[：:]\s*([^\n]+)", content)
        if match:
            title = match.group(1).strip()
        else:
            match = re.match(r"^#\s+([^\n]+)", content)
            if match:
                title = match.group(1).strip()
            else:
                title = draft_path.stem

        # 检查今日发布数量
        today_count = self.store.count_today()
        if today_count >= max_per_day:
            logger.warning(f"今日已达发布上限 ({today_count}/{max_per_day})，跳过")
            return [PublishResult(success=False, platform="*", error="已达每日上限")]

        # 检查最小间隔
        all_records = self.store.get_all()
        if all_records:
            last_time = datetime.fromisoformat(all_records[-1]["published_at"])
            if datetime.now() - last_time < timedelta(minutes=min_interval_minutes):
                wait_minutes = min_interval_minutes - (datetime.now() - last_time).seconds // 60
                logger.warning(f"距上次发布不足 {min_interval_minutes} 分钟（还需等待 {wait_minutes} 分钟）")
                return [PublishResult(success=False, platform="*", error=f"发布间隔不足，请等待 {wait_minutes} 分钟")]

        results = []
        for platform in platforms:
            publisher = self._publishers.get(platform)
            if publisher is None:
                logger.warning(f"未注册的发布平台: {platform}")
                results.append(PublishResult(success=False, platform=platform, error="平台未注册"))
                continue

            result = publisher.publish(draft_path, title, content)

            if result.success:
                self.store.add(
                    draft_file=draft_path.name,
                    platform=platform,
                    title=title,
                    url=result.url,
                )

            results.append(result)

        return results

    def get_publishers(self) -> list[str]:
        """获取已注册的发布平台列表"""
        return list(self._publishers.keys())
