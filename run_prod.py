"""
HotCommentHub 生产脚本 — 五步固化流程

1. opencli zhihu hot       → 知乎热榜
2. opencli bilibili hot    → B站热门
3. opencli xiaohongshu search → 小红书搜索
4. 按人设关键词过滤 → 筛选 TOP 3-5 话题
5. AI 分析评论 + 生成 2-3 篇草稿

用法:
  python run_prod.py -p foodie              # 美食家人设
  python run_prod.py -p gadget_reviewer     # 数码评测师
  python run_prod.py -p foodie -k "火锅"    # 指定关键词
  python run_prod.py --dry-run              # 只搜索不生成
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import yaml
import shutil
import subprocess
from loguru import logger

OPENCLI = shutil.which("opencli.cmd") or shutil.which("opencli") or "opencli"

# ---- 不依赖 loguru 的 print 输出 ----
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
RESET = "\033[0m"


def main():
    parser = argparse.ArgumentParser(description="HotCommentHub — 真实热搜 → 小红书内容生成")
    parser.add_argument("-p", "--persona", default="foodie", help="人设名称 (foodie/gadget_reviewer/beauty_blogger/travel_expert)")
    parser.add_argument("-k", "--keyword", default="", help="搜索关键词（覆盖人设默认值）")
    parser.add_argument("--dry-run", action="store_true", help="只搜索不生成")
    args = parser.parse_args()

    # 加载人设
    base_dir = Path(__file__).parent
    persona = _load_persona(base_dir / "config", args.persona)
    if not persona:
        print(f"{RED}人设 '{args.persona}' 不存在。可用: foodie, gadget_reviewer, beauty_blogger, travel_expert{RESET}")
        return

    persona_name = persona.get("name", args.persona)
    keywords = [args.keyword] if args.keyword else persona.get("search_keywords", [])[:3]
    tone = persona.get("tone", "")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"  {CYAN}HotCommentHub · {persona_name}{RESET} | {tone}")
    print(f"  关键词: {', '.join(keywords)}")
    print(f"{'='*60}\n")

    # ===== Step 1-3: 多渠道搜索 =====
    print(f"{BOLD}🔍 搜索中...{RESET}")
    all_topics = _fetch_zhihu_hot(keywords) + _fetch_bilibili_hot(keywords) + _fetch_xiaohongshu(keywords)

    if not all_topics:
        print(f"  {YELLOW}未找到相关话题。试试其他关键词或人设。{RESET}")
        return

    # 排序 + 取 TOP 5
    all_topics.sort(key=lambda t: t.get("hot_score", 0), reverse=True)
    top = all_topics[:5]

    print(f"\n{BOLD}📊 精选 {len(top)} 个话题:{RESET}")
    for i, t in enumerate(top, 1):
        stars = min(5, max(1, int(t.get("hot_score", 0) / 1000000)))
        star_str = "🔥" * stars
        print(f"  {star_str} [{i}] {t['title'][:55]}  ({t['channel']})")

    if args.dry_run:
        print(f"\n{YELLOW}--dry-run 模式，跳过内容生成。{RESET}")
        return

    # ===== Step 5: 生成内容 =====
    print(f"\n{BOLD}✍️ 生成草稿...{RESET}")

    drafts_dir = base_dir / "data" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    generated = []
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    has_ai = api_key and "your-key" not in api_key

    for i, topic in enumerate(top[:3], 1):  # 最多生成 3 个话题
        safe_title = "".join(c for c in topic["title"][:25] if c.isalnum() or c in " _-").strip()
        filename = f"{timestamp}_{i:02d}_{args.persona}_{safe_title}.md"
        filepath = drafts_dir / filename

        if has_ai:
            content = _generate_with_ai(persona, topic, api_key, base_dir)
        else:
            content = _generate_template(persona, topic, timestamp)

        filepath.write_text(content, encoding="utf-8")
        generated.append(filepath)
        print(f"  {GREEN}✅{RESET} {filename}")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"  📋 共 {len(generated)} 篇草稿 → data/drafts/")
    print(f"  {CYAN}python main.py review{RESET}          # 审阅")
    print(f"  {CYAN}python main.py publish -d 1{RESET}  # 发布第1篇")
    print(f"{'='*60}")
    if not has_ai:
        print(f"\n  {YELLOW}💡 未配置 DEEPSEEK_API_KEY，使用模板生成。设置 Key 后可用 AI 生成。{RESET}")


# ============================================================
# 搜索函数 — 直接调用 opencli
# ============================================================

def _fetch_zhihu_hot(keywords: list[str]) -> list[dict]:
    """知乎热榜"""
    import subprocess

    try:
        r = subprocess.run([OPENCLI, "zhihu", "hot", "--limit", "15", "-f", "json"],
                         capture_output=True, text=True, timeout=45, encoding="utf-8")
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout)
        topics = []
        for item in data:
            title = item.get("title", "")
            if any(kw.lower() in title.lower() for kw in keywords):
                topics.append({
                    "title": title, "channel": "知乎",
                    "hot_score": _parse_heat(item.get("heat", "0")),
                    "answers": item.get("answers", 0),
                    "url": item.get("url", ""),
                })
        print(f"  {GREEN}知乎{RESET}      热榜 → {len(topics)} 个匹配")
        return topics
    except Exception as e:
        print(f"  {YELLOW}知乎{RESET}      失败: {e}")
        return []


def _fetch_bilibili_hot(keywords: list[str]) -> list[dict]:
    """B站热门"""
    import subprocess

    try:
        r = subprocess.run([OPENCLI, "bilibili", "hot", "--limit", "15", "-f", "json"],
                         capture_output=True, text=True, timeout=45, encoding="utf-8")
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout)
        topics = []
        for item in data:
            title = item.get("title", "")
            if any(kw.lower() in title.lower() for kw in keywords):
                topics.append({
                    "title": title, "channel": "B站",
                    "hot_score": item.get("play", 0),
                    "author": item.get("author", ""),
                    "url": item.get("url", ""),
                })
        print(f"  {GREEN}B站{RESET}       热门 → {len(topics)} 个匹配")
        return topics
    except Exception as e:
        print(f"  {YELLOW}B站{RESET}       失败: {e}")
        return []


def _fetch_xiaohongshu(keywords: list[str]) -> list[dict]:
    """小红书搜索"""
    topics = []
    for kw in keywords[:3]:
        try:
            import subprocess
        
            r = subprocess.run([OPENCLI, "xiaohongshu", "search", kw, "--limit", "5", "-f", "json"],
                             capture_output=True, text=True, timeout=45, encoding="utf-8")
            if r.returncode != 0:
                continue
            data = json.loads(r.stdout)
            for item in data:
                title = item.get("title", "")
                topics.append({
                    "title": title, "channel": "小红书",
                    "hot_score": _parse_likes(item.get("likes", "0")),
                    "author": item.get("author", ""),
                    "url": item.get("url", ""),
                })
        except Exception:
            pass
    print(f"  {GREEN}小红书{RESET}    搜索 → {len(topics)} 个匹配")
    return topics


def _parse_heat(heat_str: str) -> float:
    """解析 '2832 万热度' → 28320000"""
    import re
    m = re.match(r"([\d.]+)\s*万", heat_str)
    if m:
        return float(m.group(1)) * 10000
    try:
        return float(heat_str)
    except ValueError:
        return 0


def _parse_likes(likes_str) -> float:
    """解析点赞数"""
    try:
        return float(str(likes_str).replace(",", ""))
    except ValueError:
        return 0


# ============================================================
# 内容生成
# ============================================================

def _generate_template(persona: dict, topic: dict, ts: str) -> str:
    """模板生成（无 AI Key 时使用）"""
    pname = persona.get("name", "博主")
    tone_words = persona.get("tone", "有态度")
    hashtags = " ".join(persona.get("content_style", {}).get("hashtags", []))
    title = topic["title"]
    channel = topic["channel"]

    return f"""# {title}

---

最近这个话题挺火的，作为一个{persona.get('description', '普通吃货')}，来聊两句。

说实话，这事儿我关注好几天了。看了不少网友讨论，有说好的也有骂的，挺有意思。

我的感觉是，大家别急着站队。有些东西你得亲自试过才知道。网上那些喊打喊杀的，可能连实物都没见过；反而那些说好的，也未必没收钱。

反正我的原则很简单：好吃就是好吃，不好吃也别硬撑。花了钱就得说实话，这才是对得起关注我的人。

你们怎么看？有没有踩过类似的坑？评论区见。

---

{hashtags}

---
*{tone_words} | 生成时间 {ts}*
"""


def _generate_with_ai(persona: dict, topic: dict, api_key: str, base_dir: Path) -> str:
    """AI 生成（需要 DEEPSEEK_API_KEY）"""
    import httpx

    pname = persona.get("name", "博主")
    tone = persona.get("tone", "")
    desc = persona.get("description", "")
    hashtags = " ".join(persona.get("content_style", {}).get("hashtags", []))
    emoji_style = persona.get("content_style", {}).get("emoji_style", "克制")

    system_prompt = f"""你是{pname}，{desc}。说话风格：{tone}。

请根据以下热点话题写一篇小红书笔记。要求：
- 像真人博主聊天，不要 AI 味。不用"首先其次最后综上所述"这类词。
- 开头要抓人，中间有观点有态度，结尾可以抛问题互动。
- 每段 2-3 句，段落间留白。
- 适当引用网友讨论，但不要暴露数据来源（不写"知乎热榜""B站数据显示"）。
- emoji 使用：{emoji_style}。
- 字数 300-600 字。
- 标签从以下选 3-4 个：{hashtags}
- 输出格式：
标题：xxx

正文：

标签：#xxx #xxx"""

    user_prompt = f"""话题：{topic['title']}

请按以上要求写一篇小红书笔记。"""

    try:
        resp = httpx.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.8,
                "max_tokens": 2000,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.warning(f"AI 调用失败，回退模板: {e}")
        return _generate_template(persona, topic, datetime.now().strftime("%Y%m%d_%H%M%S"))


# ============================================================
# 辅助
# ============================================================

def _load_persona(config_dir: Path, name: str) -> dict | None:
    """加载人设 YAML"""
    filepath = config_dir / "personas" / f"{name}.yaml"
    if not filepath.exists():
        return None
    raw = yaml.safe_load(filepath.read_text(encoding="utf-8"))
    return raw.get("persona", raw)


if __name__ == "__main__":
    main()
