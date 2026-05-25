"""
评论深度分析器

调用 DeepSeek API 对评论进行多维度分析：
- 情感分析
- 观点聚类
- 争议提取
- 金句精选
- 舆论风向
"""

import json
import re
from pathlib import Path
from loguru import logger
import httpx

from ..search.base import Comment


class CommentAnalyzer:
    """评论分析器"""

    def __init__(self, api_key: str, prompt_path: Path, model: str = "deepseek-chat"):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.prompt_template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""

    def analyze(
        self,
        topic_title: str,
        topic_channel: str,
        topic_hot_score: float,
        comments: list[Comment],
    ) -> dict:
        """
        分析评论

        Returns:
            {
                "sentiment": {"positive": 15, "negative": 72, "neutral": 13},
                "main_opinions": ["观点1", ...],
                "controversy": "核心争议",
                "top_comments": [{"text": "...", "likes": 12000}, ...],
                "narrative": "舆论风向总结"
            }
        """
        if not comments:
            logger.warning(f"无评论数据，跳过分析: {topic_title}")
            return self._empty_result()

        # 构建 prompt
        comments_text = "\n".join(
            f"- [{c.likes}赞] {c.content[:200]}"
            for c in sorted(comments, key=lambda x: x.likes, reverse=True)[:50]
        )
        prompt = self.prompt_template
        prompt = prompt.replace("{{topic_title}}", topic_title)
        prompt = prompt.replace("{{topic_channel}}", topic_channel)
        prompt = prompt.replace("{{topic_hot_score}}", str(topic_hot_score))
        prompt = prompt.replace("{{comment_count}}", str(len(comments)))
        prompt = prompt.replace("{{comments_text}}", comments_text)

        try:
            result = self._call_deepseek(prompt)
            return result
        except Exception as e:
            logger.error(f"评论分析失败: {e}")
            return self._empty_result()

    def _call_deepseek(self, prompt: str) -> dict:
        """调用 DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的舆论分析师。请严格按 JSON 格式输出分析结果。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        with httpx.Client(timeout=60) as client:
            response = client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

        # 提取 JSON
        return self._parse_json(content)

    @staticmethod
    def _parse_json(text: str) -> dict:
        """从 AI 输出中提取 JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试提取 code block 中的 JSON
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 {...} 块
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"无法解析 AI 输出为 JSON: {text[:500]}")
        return {
            "sentiment": {"positive": 0, "negative": 0, "neutral": 100},
            "main_opinions": [],
            "controversy": "",
            "top_comments": [],
            "narrative": text[:200],
        }

    @staticmethod
    def _empty_result() -> dict:
        return {
            "sentiment": {"positive": 0, "negative": 0, "neutral": 100},
            "main_opinions": [],
            "controversy": "",
            "top_comments": [],
            "narrative": "暂无评论数据",
        }
