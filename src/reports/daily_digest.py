"""
每日热点汇总报告生成器

查询 data/drafts/ 和 data/published.json，生成 Markdown 报告
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger


def generate_daily_report(
    data_dir: Path,
    date: str | None = None,
    search_result: dict | None = None,
) -> Path:
    """
    生成每日热点报告

    Args:
        data_dir: data 目录
        date: 日期 (YYYY-MM-DD)，默认今天
        search_result: 可选的搜索统计 dict (channel_stats: {...})

    Returns:
        报告文件路径
    """
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    report_dir = data_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    # 收集数据
    drafts_dir = data_dir / "drafts"
    published_file = data_dir / "published.json"

    drafts_today = []
    if drafts_dir.exists():
        drafts_today = sorted(
            [f for f in drafts_dir.glob("*.md") if f.name.startswith(date.replace("-", ""))],
            key=lambda f: f.name,
        )

    published_today = []
    yesterday_published = []
    if published_file.exists():
        try:
            records = json.loads(published_file.read_text(encoding="utf-8"))
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            for r in records:
                pub_date = r.get("published_at", "")[:10]
                if pub_date == date:
                    published_today.append(r)
                elif pub_date == yesterday:
                    yesterday_published.append(r)
        except (json.JSONDecodeError, FileNotFoundError):
            pass

    # 生成报告
    lines = [
        f"# 🔥 HotCommentHub 每日热点报告 — {date}",
        "",
        "## 📊 概览",
    ]

    channel_stats = (search_result or {}).get("channel_stats", {})
    lines.append(f"- 搜索渠道: {len(channel_stats)} 个")
    lines.append(f"- 采集话题: {sum(channel_stats.values())} 个" if channel_stats else "- 今天暂无搜索记录")
    lines.append(f"- 生成草稿: {len(drafts_today)} 篇")
    lines.append(f"- 已发布: {len(published_today)} 篇")
    lines.append("")

    # 草稿列表
    if drafts_today:
        lines.append("## 📝 今日生成内容")
        lines.append("")
        lines.append("| # | 文件 |")
        lines.append("|---|------|")
        for i, f in enumerate(drafts_today, 1):
            lines.append(f"| {i} | {f.name} |")
        lines.append("")

    # 发布记录
    if published_today:
        lines.append("## 📤 今日发布记录")
        lines.append("")
        lines.append("| 标题 | 平台 | 时间 |")
        lines.append("|------|------|------|")
        for r in published_today:
            title = r.get("title", "?" )[:30]
            platform = r.get("platform", "?" )
            time_str = r.get("published_at", "?" )[:19]
            lines.append(f"| {title} | {platform} | {time_str} |")
        lines.append("")

    # 昨日数据
    if yesterday_published:
        lines.append("## 📈 昨日发布数据")
        lines.append("")
        lines.append("| 标题 | 平台 | 阅读 | 点赞 | 评论 |")
        lines.append("|------|------|------|------|------|")
        for r in yesterday_published:
            title = r.get("title", "?")[:30]
            lines.append(
                f"| {title} | {r.get('platform', '?')} "
                f"| {r.get('views', '-')} | {r.get('likes', '-')} "
                f"| {r.get('comments', '-')} |"
            )
        lines.append("")

    lines.append(f"> 🤖 自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M')} | HotCommentHub")

    # 写入
    report_path = report_dir / f"{date}_daily.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"每日报告已生成: {report_path}")

    return report_path
