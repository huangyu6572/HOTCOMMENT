"""
opencli CLI 命令封装模块

所有 opencli 调用统一通过此模块：
- 自动重试 3 次（指数退避）
- 超时 60s
- 解析 JSON 输出
- 错误统一转 Python 异常
- 进程级锁（防止多个 opencli 并发导致 Browser Bridge 冲突）
"""

import subprocess
import json
import time
import threading
from typing import Optional
from loguru import logger

# 进程级互斥锁：opencli Browser Bridge 不支持并发，必须串行
_opencli_lock = threading.Lock()


class OpenCLIError(Exception):
    """opencli 命令执行错误"""
    pass


def run(
    *args: str,
    timeout: int = 60,
    retries: int = 3,
    parse_json: bool = True,
) -> str | dict | list:
    """
    执行 opencli 命令并返回结果

    Args:
        *args: opencli 命令参数，如 "weibo", "hot", "--limit", "10", "-f", "json"
        timeout: 超时秒数
        retries: 重试次数
        parse_json: 是否解析 JSON 输出

    Returns:
        字符串或解析后的 JSON

    Raises:
        OpenCLIError: 命令执行失败
    """
    # 自动注入 --profile 确保使用正确的浏览器连接
    cmd = ["opencli", "--profile", "hs9gg2sn", *args]
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"[opencli] attempt {attempt}/{retries}: {' '.join(cmd)}")
            # 需要持有锁才能执行，防止并发导致 Browser Bridge 冲突
            with _opencli_lock:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    encoding="utf-8",
                    shell=True,
                )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                # opencli exit code 66 = empty result (not an error)
                if result.returncode == 66:
                    logger.info(f"[opencli] empty result: {' '.join(cmd)}")
                    return [] if parse_json else ""
                raise OpenCLIError(
                    f"opencli exited with {result.returncode}: {stderr}"
                )

            output = result.stdout.strip()
            if not output:
                logger.info(f"[opencli] no output: {' '.join(cmd)}")
                return [] if parse_json else ""

            if parse_json:
                try:
                    return json.loads(output)
                except json.JSONDecodeError:
                    # Not JSON, return raw string
                    return output
            return output

        except subprocess.TimeoutExpired:
            last_error = f"timeout after {timeout}s"
            logger.warning(f"[opencli] {last_error}, attempt {attempt}/{retries}")
        except OpenCLIError as e:
            last_error = str(e)
            logger.warning(f"[opencli] {last_error}, attempt {attempt}/{retries}")
        except Exception as e:
            last_error = str(e)
            logger.warning(f"[opencli] unexpected error: {last_error}")

        if attempt < retries:
            wait = 2 ** attempt  # 2, 4, 8 seconds
            logger.info(f"[opencli] retrying in {wait}s...")
            time.sleep(wait)

    raise OpenCLIError(f"opencli failed after {retries} retries: {last_error}")


def check_login(platform: str) -> bool:
    """
    检查指定平台是否已登录

    Args:
        platform: 平台名，如 weibo/zhihu/bilibili/xiaohongshu

    Returns:
        True 如果已登录
    """
    try:
        # 尝试用 hot 命令检测 —— 若能返回数据说明已登录
        result = run(platform, "hot", "--limit", "1", "-f", "json", timeout=30)
        return bool(result)
    except OpenCLIError:
        return False


def doctor() -> bool:
    """检查 opencli 整体连通性"""
    try:
        output = run("doctor", parse_json=False, timeout=30)
        logger.info(f"[opencli doctor] {output}")
        return True
    except OpenCLIError as e:
        logger.error(f"[opencli doctor] {e}")
        return False
