"""
HotCommentHub CLI 入口

使用方法:
  python main.py run                     # 从配置读取人设，全流程执行
  python main.py run -p foodie -k 关键词  # 命令行覆盖
  python main.py interactive             # 交互模式
  python main.py review                  # 审阅草稿
  python main.py publish --all           # 发布所有通过
  python main.py publish -d 1            # 发布指定草稿
  python main.py schedule                # 启动定时调度
  python main.py status                  # 查看今日统计
  python main.py report                  # 生成每日报告
  python main.py check-login             # 检查登录态
  python main.py personas                # 列出人设
  python main.py config                  # 查看当前配置
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 加载 .env
load_dotenv()

# 添加项目根目录到 path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import setup_logging
from src.orchestrator import Orchestrator
from src.scheduler import Scheduler
from src.intent_parser import parse_intent


def get_orchestrator() -> Orchestrator:
    """获取 Orchestrator 实例"""
    base_dir = Path(__file__).parent
    return Orchestrator(
        config_dir=base_dir / "config",
        data_dir=base_dir / "data",
    )


def cmd_run(args):
    """执行全流程"""
    orch = get_orchestrator()
    asyncio.run(orch.run(
        keyword_override=args.keyword or "",
        platform_override=args.platform or "",
        persona_override=args.persona or "",
    ))


def cmd_interactive(args):
    """交互模式"""
    orch = get_orchestrator()
    settings = orch.settings

    print(f"\n🤖 HotCommentHub 交互模式")
    print(f"   当前人设: {settings.get('persona', '?')}")
    print(f"   可用人设: {', '.join(orch.persona_manager.list_personas())}")
    print(f"   输入 'quit' 退出\n")

    user_input = input("> ").strip()
    if not user_input or user_input.lower() == "quit":
        return

    # 解析意图
    intent = parse_intent(user_input, settings)
    print(f"\n📋 解析结果:")
    print(f"   人设: {intent.persona or settings.get('persona', '默认')}")
    print(f"   关键词: {intent.keyword or '(使用默认)'}")
    print(f"   目标平台: {', '.join(intent.platforms) if intent.platforms else '(使用默认)'}")
    print()

    asyncio.run(orch.run(
        keyword_override=intent.keyword or "",
        platform_override=intent.platforms[0] if intent.platforms else "",
        persona_override=intent.persona or "",
    ))


def cmd_review(args):
    """审阅草稿"""
    orch = get_orchestrator()
    drafts = orch.review_drafts()

    if not drafts:
        print("📋 暂无待审阅草稿")
        return

    print(f"\n📋 待审阅草稿 ({len(drafts)} 篇)")
    print("=" * 60)

    for i, d in enumerate(drafts, 1):
        content = d.read_text(encoding="utf-8")
        # 提取标题
        title = "无标题"
        for line in content.split("\n"):
            if line.startswith("标题") or line.startswith("#"):
                title = line.strip("# ：:").strip()
                break

        preview = content[:200].replace("\n", " ")
        print(f"\n{'─' * 60}")
        print(f"[{i}] {title}")
        print(f"    文件: {d.name}")
        print(f"    预览: {preview}...")
        print(f"    {'─' * 40}")

    print(f"\n操作:")
    print(f"  python main.py publish -d <序号>    发布指定草稿")
    print(f"  python main.py publish --all        发布全部")


def cmd_publish(args):
    """发布草稿"""
    orch = get_orchestrator()

    if args.all:
        results = orch.publish_all()
        for r in results:
            if isinstance(r, list):
                for sub in r:
                    status = "✅" if sub.success else "❌"
                    print(f"  {status} {sub.platform}: {sub.url or sub.error}")
            elif hasattr(r, 'success'):
                status = "✅" if r.success else "❌"
                print(f"  {status} {r.platform}: {r.url or r.error}")
        return

    if args.draft:
        results = orch.publish_draft(args.draft)
        for r in results:
            status = "✅" if r.success else "❌"
            print(f"  {status} {r.platform}: {r.url or r.error}")
        return

    print("请指定 --draft <序号> 或 --all")


def cmd_schedule(args):
    """启动定时调度"""
    orch = get_orchestrator()
    scheduler = Scheduler(orch, orch.settings)

    if args.once:
        print("⚡ 执行一次全流程...")
        scheduler.run_once()
    else:
        scheduler.start()
        print("⏰ 调度器已启动，按 Ctrl+C 停止...")
        try:
            import asyncio
            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            scheduler.stop()
            print("\n👋 已停止")


def cmd_status(args):
    """查看今日统计"""
    orch = get_orchestrator()
    status = orch.get_status()

    print(f"\n📊 HotCommentHub 今日统计")
    print(f"   当前人设: {status['persona']}")
    print(f"   待审阅草稿: {status['drafts']} 篇")
    print(f"   今日已发布: {status['published_today']} 篇")
    print()


def cmd_report(args):
    """生成每日报告"""
    orch = get_orchestrator()
    from src.reports.daily_digest import generate_daily_report

    path = generate_daily_report(orch.data_dir, date=args.date)
    print(f"📄 报告已生成: {path}")


def cmd_check_login(args):
    """检查登录态"""
    orch = get_orchestrator()
    results = orch.check_all_logins()

    print(f"\n🔐 平台登录状态:")
    print(f"{'平台':<15} {'状态':<10}")
    print("-" * 25)
    for platform, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{platform:<15} {icon} {'已登录' if status else '未登录'}")
    print()

    if not all(results.values()):
        print("⚠️  请在 Chrome 中登录未通过的平台，opencli 会自动复用登录态")


def cmd_personas(args):
    """列出人设"""
    orch = get_orchestrator()
    personas = orch.persona_manager.list_personas()

    print(f"\n🎭 可用人设 ({len(personas)} 个):")
    for name in personas:
        persona = orch.persona_manager.load(name)
        if persona:
            active = " ⬅ 当前" if name == orch.settings.get("persona") else ""
            print(f"  • {name}: {persona.get('name', '?')}{active}")
    print()


def cmd_config(args):
    """查看当前配置"""
    import yaml
    orch = get_orchestrator()

    print("\n[Config] Current settings:")
    print(yaml.dump(orch.settings, allow_unicode=True, default_flow_style=False))


def main():
    setup_logging(Path("logs"))

    parser = argparse.ArgumentParser(description="HotCommentHub - 人设驱动的多渠道热点聚合 + AI创作 + 多平台发布")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run
    p_run = subparsers.add_parser("run", help="执行全流程")
    p_run.add_argument("-p", "--persona", help="人设名称")
    p_run.add_argument("-k", "--keyword", help="搜索关键词")
    p_run.add_argument("--platform", help="目标发布平台")

    # interactive
    subparsers.add_parser("interactive", aliases=["i"], help="交互模式")

    # review
    subparsers.add_parser("review", aliases=["r"], help="审阅草稿")

    # publish
    p_pub = subparsers.add_parser("publish", aliases=["pub"], help="发布草稿")
    p_pub.add_argument("-d", "--draft", type=int, help="草稿序号")
    p_pub.add_argument("--all", action="store_true", help="发布全部")
    p_pub.add_argument("--platform", help="目标平台")

    # schedule
    p_sch = subparsers.add_parser("schedule", aliases=["sched"], help="定时调度")
    p_sch.add_argument("--once", action="store_true", help="只执行一次")

    # status
    subparsers.add_parser("status", aliases=["st"], help="今日统计")

    # report
    p_rep = subparsers.add_parser("report", help="生成每日报告")
    p_rep.add_argument("--date", help="日期 YYYY-MM-DD")

    # check-login
    subparsers.add_parser("check-login", aliases=["login"], help="检查平台登录态")

    # personas
    subparsers.add_parser("personas", aliases=["p"], help="列出人设")

    # config
    subparsers.add_parser("config", aliases=["cfg"], help="查看当前配置")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    commands = {
        "run": cmd_run,
        "interactive": cmd_interactive,
        "i": cmd_interactive,
        "review": cmd_review,
        "r": cmd_review,
        "publish": cmd_publish,
        "pub": cmd_publish,
        "schedule": cmd_schedule,
        "sched": cmd_schedule,
        "status": cmd_status,
        "st": cmd_status,
        "report": cmd_report,
        "check-login": cmd_check_login,
        "login": cmd_check_login,
        "personas": cmd_personas,
        "p": cmd_personas,
        "config": cmd_config,
        "cfg": cmd_config,
    }

    handler = commands.get(args.command)
    if handler:
        handler(args)


if __name__ == "__main__":
    main()
