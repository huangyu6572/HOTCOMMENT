"""
日志模块 — 基于 loguru，按天轮转
"""

import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_dir: Path = Path("logs"), level: str = "INFO"):
    """初始化日志系统"""
    log_dir.mkdir(parents=True, exist_ok=True)

    # 移除默认 handler
    logger.remove()

    # 控制台输出 — 彩色
    logger.add(
        sys.stderr,
        format="<level>{level: <8}</level> | <level>{message}</level>",
        level=level,
        colorize=True,
    )

    # 文件输出 — 按天轮转
    logger.add(
        log_dir / "hotcommenthub_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
        level="DEBUG",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    logger.info("日志系统初始化完成")
    return logger
