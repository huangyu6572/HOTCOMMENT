"""
内容质检器
"""

import re
from loguru import logger

SENSITIVE_WORDS = ["赌博", "色情", "违法", "枪支", "毒品"]
MIN_LENGTH = 50
MAX_LENGTH = 1000


class QualityChecker:

    def __init__(self, custom_sensitive_words=None):
        self.sensitive_words = SENSITIVE_WORDS + (custom_sensitive_words or [])

    def check(self, content):
        issues = []
        for word in self.sensitive_words:
            if word in content:
                issues.append(f"包含敏感词: {word}")
        text_only = re.sub(r"[#\s\n]", "", content)
        if len(text_only) < MIN_LENGTH:
            issues.append(f"内容过短 ({len(text_only)}字)，最少 {MIN_LENGTH} 字")
        if len(text_only) > MAX_LENGTH:
            issues.append(f"内容过长 ({len(text_only)}字)，最多 {MAX_LENGTH} 字")
        if not re.search(r"标题[：:]", content):
            issues.append("缺少标题标记")
        if "#" not in content:
            issues.append("缺少话题标签")
        passed = len(issues) == 0
        if not passed:
            logger.warning(f"质检未通过: {issues}")
        return passed, issues
