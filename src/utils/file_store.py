"""
文件存储模块 — 纯 JSON 文件读写，替代数据库

- published.json: 发布历史索引
- topics_cache.json: 已采集话题 hash（去重）
"""

import json
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger


class FileStore:
    """JSON 文件存储基类"""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self._ensure_file()

    def _ensure_file(self):
        """确保文件和目录存在"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.filepath.exists():
            self.filepath.write_text("[]", encoding="utf-8")

    def _read(self) -> list:
        """读取全部数据"""
        try:
            return json.loads(self.filepath.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write(self, data: list):
        """写入全部数据"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self.filepath.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


class PublishedStore(FileStore):
    """发布历史存储"""

    def __init__(self, data_dir: Path):
        super().__init__(data_dir / "published.json")

    def add(self, draft_file: str, platform: str, title: str, url: str = ""):
        """记录一次发布"""
        record = {
            "draft_file": draft_file,
            "platform": platform,
            "title": title,
            "published_at": datetime.now().isoformat(),
            "url": url,
            "views": 0,
            "likes": 0,
            "comments": 0,
            "last_tracked": None,
        }
        data = self._read()
        data.append(record)
        self._write(data)
        logger.info(f"[published] +1 {platform}: {title}")

    def list_today(self) -> list:
        """查询今天发布的记录"""
        today = datetime.now().strftime("%Y-%m-%d")
        return [r for r in self._read() if r["published_at"].startswith(today)]

    def count_today(self) -> int:
        """今日发布数量"""
        return len(self.list_today())

    def get_all(self) -> list:
        """获取全部发布记录"""
        return self._read()

    def update_stats(self, platform: str, url: str, views: int, likes: int, comments: int):
        """更新发布后的数据"""
        data = self._read()
        for record in data:
            if record["url"] == url:
                record["views"] = views
                record["likes"] = likes
                record["comments"] = comments
                record["last_tracked"] = datetime.now().isoformat()
                break
        self._write(data)


class TopicsCache(FileStore):
    """话题去重缓存"""

    def __init__(self, data_dir: Path):
        super().__init__(data_dir / "topics_cache.json")

    @staticmethod
    def hash_topic(title: str, channel: str) -> str:
        """生成话题唯一 hash"""
        raw = f"{channel}:{title}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def exists(self, title: str, channel: str) -> bool:
        """检查话题是否已采集"""
        h = self.hash_topic(title, channel)
        data = self._read()
        return h in data

    def mark(self, title: str, channel: str):
        """标记话题已采集"""
        h = self.hash_topic(title, channel)
        data = self._read()
        if h not in data:
            data.append(h)
            self._write(data)

    def filter_new(self, topics: list[dict]) -> list[dict]:
        """过滤出未采集的话题"""
        existing = set(self._read())
        new_topics = []
        for t in topics:
            h = self.hash_topic(t.get("title", ""), t.get("channel", ""))
            if h not in existing:
                new_topics.append(t)
        return new_topics
