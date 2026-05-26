# HotCommentHub — Trending to XHS, Persona-Driven

## One-Liner

**Real hot-list data + persona voice → publish to Xiaohongshu.**

## Two Search Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Full hot list** | No `-p` | Fetch Zhihu / Bilibili / Weibo top posts, no keyword filter |
| **Keyword filter** | `-p <persona>` | Fetch hot lists then match against persona `search_keywords` |

## Quickstart

```bash
opencli doctor                                   # 1. Verify opencli

python run_prod.py --dry-run                     # 2. Browse hot lists
python run_prod.py --dry-run -l 20               #    20 per channel

python run_prod.py -p travel_expert -k "稻城亚丁" # 3. Generate draft
python run_prod.py -p commentator -k "蜜雪冰城"

python scripts/make_cover.py                     # 4. Cover image (optional)
    --title "Title\\nSubtitle"
    --subtitle "Description"
    --output cover_xxx

python main.py publish -d 1                      # 5. Publish to XHS
```

## Personas

| Name | Key | Keywords |
|------|-----|----------|
| Foodie | `foodie` | 杨梅, 水果, 火锅 |
| Commentator | `commentator` | 社会, 经济, 政策, 产业, 争议 |
| Travel Expert | `travel_expert` | 旅行, 景区, 攻略, 小众 |
| Gadget Reviewer | `gadget_reviewer` | 数码, 手机, 耳机, 评测 |
| Beauty Blogger | `beauty_blogger` | 护肤, 彩妆, 美妆, 成分 |

## Content Style

- Conversational, no AI-slop ("首先其次最后综上所述")
- Never expose data source ("知乎热榜第X名")
- Weave in netizen opinions naturally
- 2-3 sentences per paragraph, leave breathing room
- Opinionated, specific, not exclamation-mark spam

## Verified opencli Commands

```bash
opencli doctor
opencli zhihu hot --limit 10 -f json
opencli bilibili hot --limit 10 -f json
opencli weibo hot --limit 10 -f json
opencli xiaohongshu search "美食" --limit 5 -f json
```

## Project Layout

```
HotCommentHub/
├── run_prod.py              # Hot-list fetch + draft generation
├── main.py                  # Review / publish / status / schedule
├── AGENTS.md                # Agent rules & pitfalls
├── SKILL.md                 # This file
├── config/
│   ├── settings.yaml        # Global config (channels, limits, schedule)
│   ├── personas/            # Persona YAMLs (tone, keywords, hashtags)
│   └── prompts/             # AI prompt templates
├── scripts/
│   └── make_cover.py        # Reusable cover-image generator
├── src/
│   ├── search/              # Platform searchers (zhihu, bilibili, weibo, ...)
│   ├── publish/             # Platform publishers (xhs_browser_publisher is the active one)
│   ├── personas/            # Persona manager
│   ├── ai/                  # AI analysis & content generation
│   └── utils/               # Helpers (opencli, file store, logger)
└── data/
    ├── drafts/              # Generated drafts (*.md)
    ├── published.json       # Publish records (clear to [] if rate-limited)
    └── cover*.jpg           # Cover images
```
