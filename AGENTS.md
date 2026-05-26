# AGENTS.md — HotCommentHub

## Project in a Nutshell

HotCommentHub fetches trending topics from Chinese social platforms (Zhihu, Bilibili, Weibo, Xiaohongshu), generates persona-driven content, and publishes to Xiaohongshu. Think: "hot list → persona ghostwriter → auto-publish."

See [SKILL.md](SKILL.md) for user-facing docs and quickstart commands.

## Quick Commands

```bash
# ── Hot-list Fetch ──
python run_prod.py --dry-run               # Full hot list, per-channel display
python run_prod.py --dry-run -l 20          # 20 per channel

# ── Content Generation ──
python run_prod.py -p <persona> -k "<keyword>"
python run_prod.py -p travel_expert -k "稻城亚丁"
python run_prod.py -p commentator -k "蜜雪冰城"

# ── Cover (optional) ──
python scripts/make_cover.py --title "Title" --subtitle "Subtitle" --output cover_xxx

# ── Publish (auto to XHS) ──
python main.py publish -d 1                # Publish latest draft

# ── Other ──
python main.py review                  # Review drafts
python main.py status                  # Today's stats
python main.py personas                # List personas
```

### End-to-End Publish Flow (solidified)

```
1. python run_prod.py --dry-run               # Browse hot lists, pick topic
2. python run_prod.py -p <persona> -k "<word>" # Generate draft → data/drafts/
3. python scripts/make_cover.py --title "..."  # or manually place at data/cover*.jpg
4. Publish to XHS via opencli CLI (5 steps below)
```

### XHS Publish Steps (the only reliable path)

Use a fixed session name (e.g. `xhs_pub`) to retain login state. Execute these 5 `opencli` commands in order:

```bash
SESSION="xhs_pub"
COVER="D:\code\HotCommentHub\data\cover_xxx.jpg"   # absolute path
TITLE="your title ≤20 chars"
BODY_HTML="<p>paragraph 1</p><p>paragraph 2</p>..."  # innerHTML-safe

# 1. Open publish page
opencli browser $SESSION open "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"

# 2. Upload cover image (ref=84 is the file input; re-check with `state` if DOM changes)
opencli browser $SESSION upload 84 "$COVER"

# 3. Fill title (--name targets the placeholder text)
opencli browser $SESSION fill --name "填写标题会有更多赞哦" "$TITLE"

# 4. Fill body — MUST use eval + innerHTML (opencli fill truncates contenteditable)
opencli browser $SESSION eval "var d=document.querySelector('[contenteditable=true]'); d.innerHTML='$BODY_HTML'.replace(/\\n/g,'<br>'); d.dispatchEvent(new Event('input',{bubbles:true})); 'ok'"

# 5. Publish — _onPublish is the ONLY way (click/dispatchEvent don't work on Vue Web Component)
opencli browser $SESSION eval "var b=document.querySelector('xhs-publish-btn'); b._onPublish(); 'called'"

# Verify
opencli browser $SESSION eval "window.location.href"
# → must contain "publish/success"
```

### Real Example: 蜜雪冰城 AB货 (2026-05-26, verified success)

```bash
SESSION="xhs_whd"
TITLE="流量艺人卖惨为何越来越不好使"

# 1. open
opencli browser xhs_whd open "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"

# 2. upload cover
opencli browser xhs_whd state        # find ref for <input type=file> → [84]
opencli browser xhs_whd upload 84 "D:\code\HotCommentHub\data\cover_whd.jpg"

# 3. title
opencli browser xhs_whd fill --name "填写标题会有更多赞哦" "$TITLE"

# 4. body (402 chars, multi-paragraph, conversational)
opencli browser xhs_whd eval "var d=document.querySelector('[contenteditable=true]'); var t='王鹤棣又上热搜了。<br>这次不是因为新剧，<br>而是因为客栈录制期间不开心。<br><br>紧接着掉粉、卖惨翻车、回旋镖，<br>一套组合拳下来，<br>舆论场直接炸了。<br><br>...'; d.innerHTML=t; d.dispatchEvent(new Event('input',{bubbles:true})); 'ok '+d.innerText.length"
# response: ok 402

# 5. publish
opencli browser xhs_whd eval "var b=document.querySelector('xhs-publish-btn'); b._onPublish(); 'called'"
# response: called

# 6. verify
opencli browser xhs_whd eval "window.location.href"
# response: https://creator.xiaohongshu.com/publish/success?source&bind_status=not_bind...
```

### Critical Do's and Don'ts

| Do | Don't |
|----|-------|
| Use `eval` + `innerHTML` for body | `opencli fill` on contenteditable (truncates) |
| Call `b._onPublish()` via `eval` | `click()` / `dispatchEvent()` on publish btn |
| Use a fixed session name (reuses login) | New session every time (DOM may not render) |
| Verify with `eval "window.location.href"` | Trust `main.py publish` (Python pipeline unstable) |
| `state` to find refs, then `upload`/`fill` by ref | Rely on `--css`/`--name` selectors (inconsistent) |

### Two Search Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Full hot list** | No `-p` | Fetch Zhihu/Bilibili/Weibo in full, no keyword filter |
| **Keyword filter** | `-p <persona>` | Fetch hot lists then match against persona `search_keywords` |

## Architecture

```
main.py / run_prod.py
    └── Orchestrator (src/orchestrator.py)  ← central coordinator
            ├── PersonaManager (src/personas/manager.py)
            ├── SearchEngine (src/search/engine.py)
            │       └── per-platform Searchers (zhihu, bilibili, xiaohongshu, ...)
            ├── CommentAnalyzer (src/ai/comment_analyzer.py)
            ├── ContentGenerator (src/ai/content_generator.py)  ← DeepSeek API
            └── PublishEngine (src/publish/engine.py)
                    └── per-platform Publishers (xhs, bilibili, weibo, zhihu)
```

- **Searchers** and **Publishers** use a plug-in pattern: register new ones in `engine.py`, no need to touch orchestrator.
- **Personas** are YAML files in `config/personas/` defining tone, keywords, and angle preferences.
- **AI prompts** live in `config/prompts/`. Generation uses `content_generation.txt`.

## Key Conventions

- **Python 3.11+**, managed via `pyproject.toml`. Use `uv` or `pip`.
- **DeepSeek API key** in `.env` as `DEEPSEEK_API_KEY`.
- **`opencli` CLI** must be installed and logged in (run `opencli doctor` to verify).
- **Logging** via `loguru` (`from src.utils.logger import setup_logger`).
- **File storage**: drafts in `data/drafts/`, reports in `data/reports/`, published tracking in `data/published.json`.
- **Config**: `config/settings.yaml` — central config for channels, generation params, publish limits, schedule, AI provider.

## Code Patterns

- **Manager/Engine + registration**: `SearchEngine` and `PublishEngine` maintain dicts of registered handlers. To add a platform:
  1. Create `src/search/<platform>_searcher.py` extending `BaseSearcher`
  2. Register it in `src/search/engine.py`'s `_register_searchers()`
- **Orchestrator** coordinates the full pipeline: search → filter → analyze comments → generate → review → publish.
- **Publish limits**: enforced per-day and per-interval in `PublishEngine`. Configurable in `settings.yaml`.
- **Review mode**: `always` (manual review required before publish) or `auto` (publish immediately).

## Editing Guidelines

- **Persona YAMLs** are small and declarative — follow existing format exactly.
- **Prompts** in `config/prompts/` use `{placeholder}` format. Keep variables aligned with what `ContentGenerator` expects.
- **Searchers** rely on `opencli` subprocess calls. New searchers must follow the same `opencli <platform> <command> --limit N -f json` pattern.
- **Drafts** are Markdown files. Don't change the filename pattern: `<date>_<persona>_<index>.md`.

## Potential Pitfalls

- `opencli` must be working or search/publish will fail silently in some cases.
- **Publishing enforces rate limits** — clear `data/published.json` to `[]` if blocked during testing.
- **Title extraction**: `PublishEngine` extracts title from `# Title` line (not `标题：` format).
- **Cover image**: must exist at `data/cover*.jpg` before publishing. Generate with `scripts/make_cover.py` or place manually.
- **XHS tags**: currently skipped — XHS topic tags require clicking from a recommendation list, not yet automated.

## Agent Rules

- **NEVER create throwaway scripts.** If existing tooling (e.g., `run_prod.py`) lacks a feature, extend it in-place rather than writing one-off scripts. All changes should compound in the canonical files.
- **Trust the toolchain. Don't pre-check what tools already handle internally.**
  - `run_prod.py` loads personas, checks API keys, and handles fallbacks on its own — don't read persona YAMLs or `.env` before running it.
  - `run_prod.py` generates drafts; `main.py review` + `main.py publish` handle review & publish — don't try to bypass this pipeline.
  - If a feature is truly missing, add it to the canonical files (e.g., `run_prod.py`, `main.py`). Don't work around it with ad-hoc checks.
- **DO NOT read Python source files** (`src/*.py`, `run_prod.py`, `main.py`) unless:
  - User explicitly asks to see code
  - A runtime error needs debugging
  - An edge case not covered by AGENTS.md / SKILL.md
- AGENTS.md + SKILL.md + config YAMLs + persona YAMLs are sufficient for daily operations.
- Always prefer running commands (`python run_prod.py`, `python main.py`, `opencli`) over reading implementation details.

## Project Layout

```
HotCommentHub/
├── run_prod.py              # Hot-list fetch + draft generation (main entry)
├── main.py                  # Review / publish / stats / schedule (admin entry)
├── AGENTS.md                # This file
├── SKILL.md                 # User-facing documentation
├── config/
│   ├── settings.yaml        # Global config
│   ├── personas/            # Persona YAMLs
│   │   ├── foodie.yaml
│   │   ├── commentator.yaml
│   │   ├── travel_expert.yaml
│   │   ├── gadget_reviewer.yaml
│   │   └── beauty_blogger.yaml
│   └── prompts/             # AI prompt templates
├── scripts/                 # Utility scripts
│   ├── make_cover.py        # Cover image generator (reusable)
│   └── gen_cover_legacy.py  # Legacy (deprecated)
├── src/                     # Core code
│   ├── search/              # Search adapters (per-platform hot lists)
│   ├── publish/             # Publish adapters
│   │   ├── xhs_browser_publisher.py  # XHS browser-based auto-publish
│   │   └── engine.py                 # Publish dispatcher
│   ├── personas/            # Persona manager
│   ├── ai/                  # AI analysis & generation
│   └── utils/               # Utilities
└── data/
    ├── drafts/              # Generated drafts (*.md)
    ├── published.json       # Publish records
    └── cover*.jpg           # Cover images
```

## TODO / Improvement Ideas

1. **Cover automation**: `_find_cover` only globs `data/cover*`. Consider auto-generating covers via `scripts/make_cover.py` at publish time using the topic title.
2. **Tag matching**: XHS topic tags must be clicked from a recommendation list; `add_tags` currently skips all. Needs rework to fetch clickable tag list first then match.
3. **`_onPublish` return value**: `opencli eval` return parsing is unstable (`window.location.href` returns literal). Switch to `opencli state` for URL verification.
4. **Smart title truncation**: 20-char cutoff is hard. Truncate at Chinese punctuation boundaries instead.
5. **Multi-platform publish**: `PublishEngine` has registered Weibo/Bilibili/Zhihu publishers but they are empty shells — fill them in.
6. **Draft management**: `-d 1` picks latest only. Add a list-picker to `python main.py review`.
7. **Cover script standardization**: All cover-gen scripts live under `scripts/`; no one-off scripts at project root.
