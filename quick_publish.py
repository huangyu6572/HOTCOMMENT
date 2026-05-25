#!/usr/bin/env python3
"""
一键发布小红书笔记 —— 将草稿文件发布到小红书创作者平台

用法:
  python quick_publish.py                          # 发布最新的草稿
  python quick_publish.py -f data/drafts/xxx.md    # 发布指定草稿
  python quick_publish.py -f xxx.md --dry-run      # 预览不发布
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent))

from src.publish.xhs_browser_publisher import XHSBrowserPublisher


def parse_draft(filepath: str) -> dict:
    """解析草稿文件，提取标题、正文、标签"""
    content = Path(filepath).read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    # 提取标题（第一个 # 开头的行）
    title = ""
    body_lines = []
    tags = []
    in_body = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# ") and not title:
            title = stripped[2:].strip()
        elif stripped.startswith("---"):
            in_body = True
            continue
        elif in_body:
            if stripped.startswith("#"):
                # 解析标签行：#时事评论 #社会观察 → ["时事评论", "社会观察"]
                tag_text = stripped.replace("#", " ").strip()
                for t in tag_text.split():
                    t = t.strip()
                    if t and len(t) > 1:
                        tags.append(t)
            elif stripped:
                body_lines.append(stripped)

    body = "\n".join(body_lines).strip()
    return {"title": title, "content": body, "tags": tags}


def find_cover_image(draft_path: str) -> str:
    """根据草稿名查找封面图"""
    draft_name = Path(draft_path).stem
    # 尝试匹配 data/ 下的图片
    data_dir = Path("data")
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        candidates = list(data_dir.glob(f"cover*{ext}"))
        candidates += list(data_dir.glob(f"*cover*{ext}"))
        if candidates:
            return str(candidates[0].resolve())

    # 尝试匹配同名的
    for ext in [".jpg", ".png", ".jpeg", ".webp"]:
        img = data_dir / f"{draft_name}{ext}"
        if img.exists():
            return str(img.resolve())

    return None


def main():
    parser = argparse.ArgumentParser(description="一键发布小红书笔记")
    parser.add_argument("-f", "--file", help="草稿文件路径（默认最新）")
    parser.add_argument("--dry-run", action="store_true", help="只解析不发布")
    parser.add_argument("--tags", default="", help="额外话题标签，逗号分隔")
    parser.add_argument("--session", default="xhs_auto_pub", help="浏览器会话名")
    args = parser.parse_args()

    # 找草稿文件
    draft_path = args.file
    if not draft_path:
        drafts_dir = Path("data/drafts")
        drafts = sorted(drafts_dir.glob("*.md"), key=os.path.getmtime, reverse=True)
        if not drafts:
            print("❌ 没有找到草稿文件")
            sys.exit(1)
        draft_path = str(drafts[0])
        print(f"📄 使用最新草稿: {draft_path}")

    draft_path = str(Path(draft_path).resolve())

    # 解析草稿
    print("📖 解析草稿...")
    draft = parse_draft(draft_path)
    print(f"  标题: {draft['title']}")
    print(f"  正文字数: {len(draft['content'])}")
    print(f"  标签: {draft['tags']}")

    # 找封面图
    image_path = find_cover_image(draft_path)
    if not image_path:
        print("⚠️ 未找到封面图，尝试 data/cover_yangmei.jpg")
        image_path = str(Path("data/cover_yangmei.jpg").resolve())
        if not Path(image_path).exists():
            print("❌ 封面图不存在")
            sys.exit(1)

    print(f"🖼️  封面图: {image_path}")

    # 合并标签 - 优先使用小红书推荐标签映射
    tag_map = {
        "时事评论": "杨梅",
        "社会观察": "食品安全重于泰山", 
        "信任危机": "没有买卖就没有伤害",
        "杨梅事件": "杨梅的季节",
    }
    tags = []
    for t in draft["tags"]:
        if t in tag_map:
            tags.append(tag_map[t])
        else:
            tags.append(t)
    if args.tags:
        tags += [t.strip() for t in args.tags.split(",") if t.strip()]

    if args.dry_run:
        print("\n🔍 --dry-run 模式，跳过发布")
        print(f"  会执行: 上传 {image_path}")
        print(f"  会填写标题: {draft['title']}")
        print(f"  会填写正文: {len(draft['content'])}字")
        print(f"  会添加标签: {tags}")
        sys.exit(0)

    # 发布
    publisher = XHSBrowserPublisher(session=args.session)
    success = publisher.full_flow(
        image_path=image_path,
        title=draft["title"],
        content=draft["content"],
        tags=tags if tags else None,
    )

    if success:
        print("\n✅ 操作完成！请检查浏览器页面确认发布状态。")
        print("💡 提示: 如果发布按钮未激活，可能需要:")
        print("   1. 从草稿箱恢复后手动发布")
        print("   2. 检查是否满足小红书的发布条件（标题≥5字、正文≥10字、至少1张图）")
    else:
        print("\n❌ 发布流程异常，请检查日志。")
        sys.exit(1)


if __name__ == "__main__":
    main()
