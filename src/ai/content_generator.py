"""
人设化内容生成器

根据人设 + 话题 + 评论分析 → 生成 2-3 篇不同角度的小红书文案
输出 Markdown 文件
"""

import re
import json
from datetime import datetime
from pathlib import Path
from loguru import logger
import httpx


ANGLE_DESC = {
    "event_report": "以事件报道角度，客观叙述发生了什么，引用网友评论作为佐证",
    "opinion": "以个人观点角度，结合网友讨论发表你的看法，有态度有立场",
    "guide": "以攻略/指南角度，告诉读者怎么做、怎么避坑，实用干货为主",
}


class ContentGenerator:
    """内容生成器"""

    def __init__(
        self,
        api_key: str,
        prompt_path: Path,
        output_dir: Path,
        model: str = "deepseek-chat",
    ):
        self.api_key = api_key
        self.model = model
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.prompt_template = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        persona: dict,
        topic_title: str,
        topic_channel: str,
        analysis: dict,
        angles: list[str],
    ) -> list[Path]:
        """
        生成多篇草稿

        Args:
            persona: 人设配置
            topic_title: 话题标题
            topic_channel: 话题来源渠道
            analysis: 评论分析结果
            angles: 要生成的角度列表

        Returns:
            生成的草稿文件路径列表
        """
        drafts = []

        for angle in angles:
            try:
                path = self._generate_one(persona, topic_title, topic_channel, analysis, angle)
                if path:
                    drafts.append(path)
            except Exception as e:
                logger.error(f"生成 {angle} 角度失败: {e}")

        return drafts

    def _generate_one(
        self,
        persona: dict,
        topic_title: str,
        topic_channel: str,
        analysis: dict,
        angle: str,
    ) -> Path | None:
        """生成单篇草稿"""
        # 构建 prompt
        prompt = self.prompt_template
        prompt = prompt.replace("{{persona_name}}", persona.get("name", ""))
        prompt = prompt.replace("{{persona_description}}", persona.get("description", ""))
        prompt = prompt.replace("{{persona_tone}}", persona.get("tone", ""))
        prompt = prompt.replace("{{persona_domains}}", ", ".join(persona.get("domains", [])))
        prompt = prompt.replace("{{topic_title}}", topic_title)
        prompt = prompt.replace("{{topic_channel}}", topic_channel)
        prompt = prompt.replace("{{narrative}}", analysis.get("narrative", ""))
        prompt = prompt.replace("{{main_opinions}}", "\n".join(f"- {o}" for o in analysis.get("main_opinions", [])))
        prompt = prompt.replace(
            "{{top_comments}}",
            "\n".join(f"- [{c.get('likes', 0)}赞] {c.get('text', '')}" for c in analysis.get("top_comments", [])),
        )
        prompt = prompt.replace("{{angle}}", angle)
        prompt = prompt.replace("{{angle_desc}}", ANGLE_DESC.get(angle, "自由发挥"))

        # 长度范围
        length = persona.get("content_style", {}).get("length", "medium")
        length_map = {"short": "200-400", "medium": "300-800", "long": "500-1000"}
        prompt = prompt.replace("{{length_range}}", length_map.get(length, "300-800"))

        # 标签
        hashtags = persona.get("content_style", {}).get("hashtags", [])
        prompt = prompt.replace("{{hashtags}}", " ".join(hashtags))

        # 调用 API
        content = self._call_deepseek(prompt)

        # 写入文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = re.sub(r"[^\w\u4e00-\u9fff]", "_", topic_title)[:30]
        angle_cn = ANGLE_DESC.get(angle, angle)[:4]
        filename = f"{timestamp}_{angle_cn}_{safe_title}.md"
        filepath = self.output_dir / filename
        filepath.write_text(content, encoding="utf-8")

        logger.info(f"草稿已生成: {filepath}")
        return filepath

    def _call_deepseek(self, prompt: str) -> str:
        """调用 DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "你是一个专业的小红书内容创作者。请严格按照要求的格式和人设撰写内容。",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 3000,
        }

        with httpx.Client(timeout=90) as client:
            response = client.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
        return content
