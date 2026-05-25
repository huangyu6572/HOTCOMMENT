"""
意图解析器

从用户自然语言输入中提取：
- 人设偏好
- 搜索关键词
- 目标发布平台
"""

import re
from typing import Optional
from pydantic import BaseModel


class Intent(BaseModel):
    """解析后的意图"""
    persona: Optional[str] = None       # 人设名称
    keyword: Optional[str] = None      # 搜索关键词
    platforms: list[str] = []           # 目标发布平台


# 人设关键词映射
PERSONA_KEYWORDS = {
    "foodie": ["美食", "吃货", "探店", "餐厅", "火锅", "奶茶", "小吃", "做饭", "厨房"],
    "gadget_reviewer": ["数码", "手机", "电脑", "评测", "科技", "耳机", "笔记本", "硬件"],
    "beauty_blogger": ["美妆", "护肤", "化妆", "口红", "粉底", "面膜", "成分"],
    "travel_expert": ["旅行", "旅游", "攻略", "酒店", "民宿", "打卡", "自驾", "出国"],
}

# 平台关键词映射
PLATFORM_KEYWORDS = {
    "xiaohongshu": ["小红书", "红薯"],
    "weibo": ["微博"],
    "bilibili": ["B站", "b站", "bilibili"],
    "zhihu": ["知乎"],
}


def parse_intent(text: str, defaults: dict) -> Intent:
    """
    解析用户输入的自然语言意图

    Args:
        text: 用户输入，如 "我是美食家，帮我搜网红餐厅翻车，发小红书"
        defaults: 从 settings.yaml 加载的默认配置

    Returns:
        Intent 对象
    """
    intent = Intent(
        persona=defaults.get("persona"),
        platforms=list(defaults.get("publish", {}).get("platforms", [])),
    )

    text_lower = text.lower()

    # 1. 识别人设
    for persona_name, keywords in PERSONA_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            intent.persona = persona_name
            break

    # 2. 识别目标平台
    detected_platforms = []
    for platform, keywords in PLATFORM_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            detected_platforms.append(platform)
    if detected_platforms:
        intent.platforms = detected_platforms

    # 3. 提取搜索关键词
    # 移除人设和平台相关词后的剩余部分作为关键词
    keyword = _extract_keyword(text)
    if keyword:
        intent.keyword = keyword

    return intent


def _extract_keyword(text: str) -> Optional[str]:
    """从文本中提取核心搜索关键词"""
    # 移除常见人设声明
    patterns = [
        r"我是[一一个]?\S*家",
        r"帮我[搜找查]",
        r"发[一到].*?[。！，]",
        r"[帮我]?[在到].*?发[布表]",
    ]
    cleaned = text
    for pat in patterns:
        cleaned = re.sub(pat, "", cleaned)

    # 移除"小红书""知乎"等平台词
    for keywords in PLATFORM_KEYWORDS.values():
        for kw in keywords:
            cleaned = cleaned.replace(kw, "")

    # 清洗后取剩余内容
    cleaned = cleaned.strip().strip("，。！？、").strip()
    if len(cleaned) >= 2:
        return cleaned

    return None
