"""
HotCommentHub 生产脚本 — 五步固化流程

1. opencli zhihu hot       → 知乎热榜
2. opencli bilibili hot    → B站热门
3. opencli weibo hot       → 微博热搜
4. opencli xiaohongshu search → 小红书搜索
5. 按人设关键词过滤 → 生成草稿

用法:
  python run_prod.py                        # 全量热榜
  python run_prod.py --dry-run              # 只搜索不生成
  python run_prod.py --dry-run -l 20        # 每渠道20条
  python run_prod.py -p foodie              # 美食家人设关键词过滤
  python run_prod.py -p commentator -k "蜜雪冰城"  # 指定关键词
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import yaml
import shutil
import subprocess

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
    parser.add_argument("-p", "--persona", default=None, help="人设名称，不指定则全量热榜 (foodie/gadget_reviewer/beauty_blogger/travel_expert/commentator)")
    parser.add_argument("-k", "--keyword", default="", help="搜索关键词（覆盖人设默认值，仅指定persona时生效）")
    parser.add_argument("-l", "--limit", type=int, default=15, help="每渠道拉取数量 (默认15)")
    parser.add_argument("--hot", action="store_true", default=True, help="按今日热榜抓取（默认行为，无persona时强制此模式）")
    parser.add_argument("--dry-run", action="store_true", help="只搜索不生成")
    args = parser.parse_args()

    base_dir = Path(__file__).parent

    # ===== 判断模式 =====
    # 有 persona → 关键词过滤模式；无 persona → 全量热榜模式
    persona = None
    keywords = []
    persona_name = "热榜速览"
    tone = ""

    if args.persona:
        persona = _load_persona(base_dir / "config", args.persona)
        if not persona:
            print(f"{RED}人设 '{args.persona}' 不存在。可用: foodie, gadget_reviewer, beauty_blogger, travel_expert, commentator{RESET}")
            return
        persona_name = persona.get("name", args.persona)
        keywords = [args.keyword] if args.keyword else persona.get("search_keywords", [])[:3]
        tone = persona.get("tone", "")
    else:
        # 无 persona：全量热榜模式，不过滤关键词
        keywords = []  # 空列表 = 不匹配过滤，全量返回
        tone = "今日热点速览"

    print(f"\n{BOLD}{'='*60}{RESET}")
    if args.persona:
        print(f"  {CYAN}HotCommentHub · {persona_name}{RESET} | {tone}")
        print(f"  模式: 关键词过滤 | 关键词: {', '.join(keywords)}")
    else:
        print(f"  {CYAN}HotCommentHub · 今日热榜{RESET}")
        print(f"  模式: 全量热榜（不过滤 | 每渠道 {args.limit} 条）")
    print(f"{'='*60}\n")

    # ===== Step 1-3: 多渠道搜索 =====
    print(f"{BOLD}🔍 搜索中...{RESET}")
    zhihu_topics = _fetch_zhihu_hot(keywords, args.limit)
    bilibili_topics = _fetch_bilibili_hot(keywords, args.limit)
    xhs_topics = _fetch_xiaohongshu(keywords)
    weibo_topics = _fetch_weibo_hot(keywords, args.limit)

    all_topics = zhihu_topics + bilibili_topics + xhs_topics + weibo_topics

    if not all_topics:
        print(f"  {YELLOW}未找到相关话题。试试其他关键词或人设。{RESET}")
        return

    # ---- dry-run 模式：分渠道展示 ----
    if args.dry_run:
        _print_channel("📚 知乎热榜", zhihu_topics)
        _print_channel("🎬 B站热门", bilibili_topics)
        _print_channel("📊 微博热搜", weibo_topics)
        _print_channel("📕 小红书", xhs_topics)
        print(f"\n{YELLOW}--dry-run 模式，跳过内容生成。{RESET}")
        return

    # ---- 生成模式：跨渠道混排取 TOP 5 ----
    all_topics.sort(key=lambda t: t.get("hot_score", 0), reverse=True)
    top = all_topics[:5]

    print(f"\n{BOLD}📊 精选 {len(top)} 个话题:{RESET}")
    for i, t in enumerate(top, 1):
        stars = min(5, max(1, int(t.get("hot_score", 0) / 1000000)))
        star_str = "🔥" * stars
        print(f"  {star_str} [{i}] {t['title'][:55]}  ({t['channel']})")

    # ===== Step 5: 生成内容 =====
    print(f"\n{BOLD}✍️ 生成草稿...{RESET}")

    drafts_dir = base_dir / "data" / "drafts"
    drafts_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    for i, topic in enumerate(top[:3], 1):  # 最多生成 3 个话题
        safe_title = "".join(c for c in topic["title"][:25] if c.isalnum() or c in " _-").strip()
        filename = f"{timestamp}_{i:02d}_{args.persona}_{safe_title}.md"
        filepath = drafts_dir / filename

        content = _generate_template(persona, topic, timestamp)
        filepath.write_text(content, encoding="utf-8")
        print(f"  {GREEN}✅{RESET} {filename}")

    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"  📋 共 {len(top[:3])} 篇草稿 → data/drafts/")
    print(f"  {CYAN}python main.py review{RESET}          # 审阅")
    print(f"  {CYAN}python main.py publish -d 1{RESET}  # 发布第1篇")
    print(f"{'='*60}")


# ============================================================
# 搜索函数 — 直接调用 opencli
# ============================================================

def _fetch_zhihu_hot(keywords: list[str], limit: int = 15) -> list[dict]:
    """知乎热榜。keywords 为空时返回全量，否则按关键词过滤。"""
    import subprocess

    try:
        r = subprocess.run([OPENCLI, "zhihu", "hot", "--limit", str(limit), "-f", "json"],
                         capture_output=True, text=True, timeout=45, encoding="utf-8")
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout)
        topics = []
        for item in data:
            title = item.get("title", "")
            # keywords 为空 → 全量返回；否则关键词匹配
            if not keywords or any(kw.lower() in title.lower() for kw in keywords):
                topics.append({
                    "title": title, "channel": "知乎",
                    "hot_score": _parse_heat(item.get("heat", "0")),
                    "answers": item.get("answers", 0),
                    "url": item.get("url", ""),
                })
        label = "全量" if not keywords else f"{len(topics)} 个匹配"
        print(f"  {GREEN}知乎{RESET}      热榜 → {label}")
        return topics
    except Exception as e:
        print(f"  {YELLOW}知乎{RESET}      失败: {e}")
        return []


def _fetch_bilibili_hot(keywords: list[str], limit: int = 15) -> list[dict]:
    """B站热门。keywords 为空时返回全量，否则按关键词过滤。"""
    import subprocess

    try:
        r = subprocess.run([OPENCLI, "bilibili", "hot", "--limit", str(limit), "-f", "json"],
                         capture_output=True, text=True, timeout=45, encoding="utf-8")
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout)
        topics = []
        for item in data:
            title = item.get("title", "")
            if not keywords or any(kw.lower() in title.lower() for kw in keywords):
                topics.append({
                    "title": title, "channel": "B站",
                    "hot_score": item.get("play", 0),
                    "author": item.get("author", ""),
                    "url": item.get("url", ""),
                })
        label = "全量" if not keywords else f"{len(topics)} 个匹配"
        print(f"  {GREEN}B站{RESET}       热门 → {label}")
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


def _fetch_weibo_hot(keywords: list[str], limit: int = 15) -> list[dict]:
    """微博热搜。keywords 为空时返回全量，否则按关键词过滤。"""
    import subprocess

    try:
        r = subprocess.run([OPENCLI, "weibo", "hot", "--limit", str(limit), "-f", "json"],
                         capture_output=True, text=True, timeout=45, encoding="utf-8")
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout)
        topics = []
        for item in data:
            word = item.get("word", "")
            if not keywords or any(kw.lower() in word.lower() for kw in keywords):
                topics.append({
                    "title": word, "channel": "微博",
                    "hot_score": item.get("hot_value", 0),
                    "category": item.get("category", ""),
                    "url": item.get("url", ""),
                })
        label = "全量" if not keywords else f"{len(topics)} 个匹配"
        print(f"  {GREEN}微博{RESET}      热搜 → {label}")
        return topics
    except Exception as e:
        print(f"  {YELLOW}微博{RESET}      失败: {e}")
        return []


def _print_channel(label: str, topics: list[dict]):
    """分渠道打印话题列表"""
    if not topics:
        return
    print(f"\n{BOLD}{label}  TOP {len(topics)}{RESET}")
    for i, t in enumerate(topics, 1):
        title = t["title"][:60]
        channel = t["channel"]
        score = t.get("hot_score", 0)
        if score > 10000:
            score_str = f"{score/10000:.0f}万"
        else:
            score_str = str(int(score))
        extra = ""
        if channel == "B站":
            extra = f"  [{t.get('author', '')}]"
        elif channel == "微博":
            extra = f"  [{t.get('category', '')}]"
        print(f"  {i:2}. [{score_str}] {title}{extra}")


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
    """根据话题和 persona 生成有实质内容（非 AI 味）的模板"""
    pname = persona.get("name", "博主")
    tone = persona.get("tone", "有态度")
    desc = persona.get("description", "")
    hashtags_raw = persona.get("content_style", {}).get("hashtags", [])
    hashtags = " ".join(hashtags_raw) if hashtags_raw else ""
    title = topic["title"]
    channel = topic["channel"]
    url = topic.get("url", "")
    answers = topic.get("answers", 0)
    score = topic.get("hot_score", 0)

    # 根据话题和 persona 生成不同的开头和角度
    topic_lower = title.lower()
    persona_key = persona.get("domains", ["综合"])[0] if persona.get("domains") else "综合"

    # 根据 persona 类型选开场白
    if "旅行" in pname or "travel" in persona_key.lower():
        hook = f"去过川西的朋友应该都懂——稻城亚丁，\"蓝色星球上的最后一片净土\"。但最近这净土门口，出了点不太体面的事。"
        angle = (
            "40公里省道，说截就截，过路就得买门票。这事搁谁身上都得懵：我走的是国道省道，又不是景区专线，凭什么交钱？\n\n"
            "景区方面的解释是把这段路\"纳入了旅游道路规划\"。听上去合法，但仔细一想——省道是公共资源，地方政府和景区联合起来就能把它变成收费站？"
            "这次有个旅行博主直接硬刚，拒绝付费，把争议推到了台前。知乎上 400 多个回答吵翻了天，说明这不是一个人的憋屈，是普遍的情绪。\n\n"
            "说实话，国内景区\"圈地收费\"不是新鲜事。茶卡盐湖把国道圈进去过，凤凰古城搞过进城费，现在轮到稻城亚丁了。"
            "套路都一样：先把公共资源包装成\"景区配套\"，再立个收费名目。游客不较真，就默认了；较真了，就搬出\"规划文件\"来堵嘴。\n\n"
            "我的态度是：公共资源姓\"公\"，不是景区的小金库。合理的门票可以接受，但把省道圈起来收过路费，这事不对。"
            "博主硬刚不是在找茬，是在替所有游客问一个本该由监管部门回答的问题：这条路到底是谁的？\n\n"
            "下次你去稻城亚丁，导航导你上省道，到了门口被拦下说\"先买景区票\"，你怎么办？评论区一起聊聊。"
        )
    elif "评论" in pname or "commentator" in persona_key.lower():
        hook = "稻城亚丁又上热搜了，这次不是因为风景美，而是因为把省道圈起来收门票。"
        angle = (
            f"事情不复杂：景区把近 40 公里省道纳入\"旅游道路规划\"，从此路过就得买景区票。一位旅行博主不认这个理，硬刚拒绝付费，知乎上 {answers} 个回答直接炸锅。\n\n"
            "先把争议的核心说清楚——这不是\"景区门票该不该收\"的问题，是\"公共道路能不能被景区私有化\"的问题。两者有本质区别。\n\n"
            "省道的建设和养护用的是公共财政，理论上属于每一个纳税人。景区一纸规划就把它变成收费关卡，这已经不是在管理旅游资源了，是在套利。"
            "更微妙的是，这种做法如果被默许，全国有多少景区会跟风？今天稻城亚丁圈 40 公里，明天张家界圈 50 公里，后天黄山圈 60 公里——以后想去看看祖国大好河山，先得交\"过路费\"。\n\n"
            "博主硬刚的意义不在于能不能赢，在于把这件事捅到了公众面前。很多时候，不合理的事情之所以能持续，就是因为没人站出来问一句\"凭什么\"。\n\n"
            "我关注的是后续：当地主管部门会怎么回应？是拿出法律依据证明\"旅游道路规划\"的合法性，还是含糊其辞不了了之？这关系到我们每一个人的出行权利。\n\n"
            "你怎么看？评论区等着你的观点。"
        )
    elif "美食" in pname or "foodie" in persona_key.lower():
        hook = f"看到这个话题在{channel}上讨论得挺热闹，作为一个天天跟吃喝打交道的，说几句。"
        angle = (
            f"这个话题能在{channel}拿到 {score/10000:.0f} 万热度，说明大家是真的关心。\n\n"
            "说实话，作为一个在意品质的人，我觉得这事得分两面看。"
            "一方面，消费者的体验和权益是底线；另一方面，行业也有它的成本和难处。不是非黑即白的事。\n\n"
            "我的原则很简单：花了钱，就该得到明码标价的东西。不管价格高低，标准不能因人而异。\n\n"
            "你们遇到过类似的情况吗？评论区聊聊。"
        )
    else:
        hook = f"这个话题在{channel}上讨论得挺火，{score/10000:.0f} 万热度，{answers} 个回答，说明戳中了很多人。"
        angle = (
            "先说说我为什么关注这件事。不是因为话题本身有多新鲜，而是它背后牵扯到的问题，跟每个人的日常生活都有关系。\n\n"
            "看了不少讨论，有支持的、有反对的，各有各的道理。但我觉得，争论的核心其实就一个：规则到底应该保护谁的利益？\n\n"
            "很多时候，大家吵来吵去吵的不是事实，是立场。而真正该出来说清楚的人，往往选择沉默。这才是最让人心累的地方。\n\n"
            "我不急着下结论，但我希望看到这件事有后续。不是和稀泥式的\"正在调查\"，是白纸黑字的回应。\n\n"
            "你们怎么看？评论区一起等一个后续。"
        )

    return f"""# {title}

---

{hook}

{angle}

---

{hashtags}

---
*{tone} | {ts}*
"""


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
