"""
搜索适配器基类

所有平台搜索器继承此类，统一接口
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Comment:
    """评论"""
    content: str
    author: str = ""
    likes: int = 0


@dataclass
class Topic:
    """搜索话题"""
    title: str
    url: str = ""
    hot_score: float = 0.0
    channel: str = ""
    comments: list[Comment] = field(default_factory=list)
    raw_data: dict = field(default_factory=dict)


class BaseSearcher(ABC):
    """搜索适配器基类"""

    def __init__(self, channel: str):
        self.channel = channel

    @abstractmethod
    def search(self, keywords: list[str]) -> list[Topic]:
        """
        搜索相关话题

        Args:
            keywords: 搜索关键词列表

        Returns:
            Topic 列表
        """
        ...

    def fetch_comments(self, topic: Topic, limit: int = 20) -> list[Comment]:
        """
        采集话题的评论（子类可覆盖）

        Args:
            topic: 话题
            limit: 评论数量上限

        Returns:
            Comment 列表
        """
        return []

    def name(self) -> str:
        return self.channel
