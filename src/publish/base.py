"""
发布适配器基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    platform: str
    url: str = ""
    error: str = ""


class BasePublisher(ABC):
    """发布适配器基类"""

    def __init__(self, platform: str):
        self.platform = platform

    @abstractmethod
    def publish(self, draft_path: Path, title: str, content: str) -> PublishResult:
        """
        发布内容

        Args:
            draft_path: 草稿文件路径
            title: 标题
            content: 正文内容

        Returns:
            PublishResult
        """
        ...

    def name(self) -> str:
        return self.platform
