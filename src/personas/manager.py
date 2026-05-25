"""
人设管理器

加载 YAML 人设模板，提供活跃人设的配置获取
"""

import yaml
from pathlib import Path
from typing import Optional
from loguru import logger


class PersonaManager:
    """人设管理器"""

    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.personas_dir = config_dir / "personas"
        self._cache: dict[str, dict] = {}

    def list_personas(self) -> list[str]:
        """列出所有可用人设名称"""
        if not self.personas_dir.exists():
            return []
        return [
            f.stem
            for f in self.personas_dir.glob("*.yaml")
        ]

    def load(self, name: str) -> Optional[dict]:
        """加载指定人设"""
        if name in self._cache:
            return self._cache[name]

        filepath = self.personas_dir / f"{name}.yaml"
        if not filepath.exists():
            logger.error(f"人设文件不存在: {filepath}")
            return None

        try:
            raw = yaml.safe_load(filepath.read_text(encoding="utf-8"))
            persona = raw.get("persona", raw)
            self._cache[name] = persona
            logger.info(f"加载人设: {persona.get('name', name)}")
            return persona
        except yaml.YAMLError as e:
            logger.error(f"解析人设文件失败 {filepath}: {e}")
            return None

    def get_active(self, settings: dict) -> Optional[dict]:
        """获取当前激活的人设（从 settings 读取 persona 字段）"""
        name = settings.get("persona", "foodie")
        return self.load(name)

    def get_search_keywords(self, settings: dict) -> list[str]:
        """获取搜索关键词：命令行 > settings > 人设默认值"""
        # 命令行 keyword
        cli_keyword = settings.get("keyword", "")
        if cli_keyword:
            return [cli_keyword]

        # 人设默认 search_keywords
        persona = self.get_active(settings)
        if persona:
            return persona.get("search_keywords", [])

        return []
