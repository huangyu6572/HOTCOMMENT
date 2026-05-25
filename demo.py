"""
HotCommentHub 验证 Demo 脚本

测试项目中各模块是否正常工作：
  1. 配置 & 人设加载
  2. opencli 连通性
  3. 各渠道搜索器
  4. 文件存储 (JSON 读写)
  5. 评论分析 (需要 DEEPSEEK_API_KEY)
  6. 内容生成 (需要 DEEPSEEK_API_KEY)
  7. 完整流程 (搜索 + 分析 + 生成)

用法:
  python demo.py           # 运行所有测试
  python demo.py --quick   # 快速测试 (跳过 opencli 网络调用)
  python demo.py --ai      # 仅测试 AI 模块
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()


# ============================================================
# 工具函数
# ============================================================

PASS = "✅"
FAIL = "❌"
SKIP = "⏭️"
WARN = "⚠️"

results = []


def test(name: str):
    """测试装饰器/上下文"""
    def decorator(func):
        def wrapper():
            try:
                func()
                results.append((PASS, name))
                print(f"  {PASS} {name}")
            except Exception as e:
                results.append((FAIL, name, str(e)))
                print(f"  {FAIL} {name}: {e}")
        return wrapper
    return decorator


def test_sync(name, fn):
    """同步测试"""
    try:
        fn()
        results.append((PASS, name))
        print(f"  {PASS} {name}")
    except Exception as e:
        results.append((FAIL, name, str(e)))
        print(f"  {FAIL} {name}: {e}")


# ============================================================
# 测试用例
# ============================================================

def test_config_loading():
    """测试配置加载"""
    import yaml
    config_dir = Path("config")

    # settings.yaml
    settings_path = config_dir / "settings.yaml"
    assert settings_path.exists(), "settings.yaml 不存在"
    settings = yaml.safe_load(settings_path.read_text(encoding="utf-8"))
    assert "persona" in settings, "settings.yaml 缺少 persona 字段"
    assert "channels" in settings, "settings.yaml 缺少 channels 字段"


def test_persona_loading():
    """测试人设加载"""
    from src.personas.manager import PersonaManager

    manager = PersonaManager(Path("config"))
    personas = manager.list_personas()
    assert len(personas) >= 4, f"人设数量不足，期望 >=4，实际 {len(personas)}"

    # 测试加载每个
    for name in personas:
        persona = manager.load(name)
        assert persona is not None, f"无法加载人设: {name}"
        assert "name" in persona
        assert "search_keywords" in persona
        assert "tone" in persona


def test_intent_parser():
    """测试意图解析"""
    from src.intent_parser import parse_intent

    defaults = {"persona": "foodie", "publish": {"platforms": ["xiaohongshu"]}}

    # 测试 1: 基本解析
    intent = parse_intent("我是美食家，帮我搜网红餐厅翻车，发小红书", defaults)
    assert intent.persona == "foodie", f"人设解析错误: {intent.persona}"
    assert "xiaohongshu" in intent.platforms, "平台解析错误"
    assert intent.keyword is not None, "关键词解析为空"

    # 测试 2: 只有人设
    intent2 = parse_intent("帮我搜手机评测", defaults)
    assert intent2.persona == "gadget_reviewer" or intent2.persona == "foodie"

    # 测试 3: 空输入
    intent3 = parse_intent("", defaults)
    assert intent3.persona == "foodie"


def test_file_store():
    """测试 JSON 文件存储"""
    import tempfile, shutil
    from src.utils.file_store import PublishedStore, TopicsCache

    tmp = Path(tempfile.mkdtemp())

    try:
        # PublishedStore
        ps = PublishedStore(tmp)
        ps.add("test.md", "xiaohongshu", "测试标题")
        assert ps.count_today() == 1
        records = ps.get_all()
        assert len(records) == 1
        assert records[0]["title"] == "测试标题"

        # TopicsCache
        tc = TopicsCache(tmp)
        assert not tc.exists("测试话题", "weibo")
        tc.mark("测试话题", "weibo")
        assert tc.exists("测试话题", "weibo")
        tc.mark("测试话题", "weibo")  # 重复 mark 不影响
        assert tc.exists("测试话题", "weibo")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_quality_checker():
    """测试内容质检"""
    from src.ai.quality_checker import QualityChecker

    checker = QualityChecker()

    # 正常内容
    ok_content = """标题：测试标题
这是正文内容，包含足够长度来通过测试验证。
今天我们聊网红餐厅的那些事，网友评论很有料。
#测试 #demo
"""
