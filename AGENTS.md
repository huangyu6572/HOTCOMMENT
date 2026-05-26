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

Use a fixed session name (e.g. `xhs_pub`) to retain login state. Execute these 6 `opencli` commands in order:

```bash
SESSION="xhs_pub"
COVER="D:\code\HotCommentHub\data\cover_xxx.jpg"   # absolute path
TITLE="your title ≤20 chars"

# 1. Open publish page (force image tab via URL param)
opencli browser $SESSION open "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"

# 2. Wait for DOM ready + find file input ref (ref varies, always re-detect!)
opencli browser $SESSION eval "var els=document.querySelectorAll('input'); var r=[]; for(var i=0;i<els.length;i++){r.push(i+':'+els[i].type+':'+(els[i].accept||'none'))}; JSON.stringify(r)"
# → find the index of "file:.jpg,.jpeg,.png,.webp", then cross-check with `state` for the DOM ref number

# 3. Upload cover image (use ref number from step 2)
opencli browser $SESSION upload <REF> "$COVER"

# 4. Fill title (--name targets the placeholder text)
opencli browser $SESSION fill --name "填写标题会有更多赞哦" "$TITLE"

# 5. Fill body — MUST use eval + innerHTML, use <br> not \n for line breaks
opencli browser $SESSION eval "var d=document.querySelector('[contenteditable=true]'); var t='line1<br><br>line2<br><br>line3...'; d.innerHTML=t; d.dispatchEvent(new Event('input',{bubbles:true})); 'ok '+d.innerText.length"
# NOTE: embed the full HTML text directly (JS var), do NOT use shell variable substitution $BODY_HTML — it breaks on special chars

# 6. Publish — _onPublish is the ONLY way
opencli browser $SESSION eval "var b=document.querySelector('xhs-publish-btn'); if(b && typeof b._onPublish === 'function') { b._onPublish(); 'called' } else { 'fail: '+typeof b }"

# 7. Verify (wait 5s then check URL)
Start-Sleep -Seconds 5
opencli browser $SESSION eval "window.location.href"
# → must contain "published=true" (新版) or "publish/success" (旧版)
```

### Publish Flow Gotchas (from real runs)

| # | Problem | Root Cause | Fix |
|---|---------|------------|-----|
| 1 | Page auto-redirects to `/new/note-manager` | Session already logged in, `open` sometimes lands on manager | Just `open` again, second time sticks |
| 2 | `eval "input[type=file]"` returns `not ready` | Page not fully rendered yet | Use `querySelectorAll('input')` loop + `JSON.stringify` to inspect all inputs at once |
| 3 | file input ref is NOT always 84 | DOM structure changes between sessions/versions | Always re-detect: `eval` to find file input index → `state` to get ref number |
| 4 | `$BODY_HTML` shell variable breaks on `'` `"` `<` etc. | Shell interpolation conflicts with HTML/JS syntax | Embed body text directly in JS `var t='...'` inside eval, avoid shell vars for body |
| 5 | `\n` in shell string becomes literal backslash-n | PowerShell escaping | Use `<br>` directly in JS string literal, never `replace(/\n/g,'<br>')` |
| 6 | `_onPublish` reports `called` but page may still be processing | Async publish, redirect takes 2-5s | Always `Start-Sleep -Seconds 5` before verifying URL |
| 7 | Cover script generates `.jpg` but filename doesn't auto-match | `--output` doesn't add extension consistently | Check actual output path from script stdout, use that exact path for upload |

### Real Example: 美食摄影教程 (2026-05-26, verified success — refined flow)

```bash
SESSION="xhs_pub"
TITLE="春夏美食怎么拍出治愈感"

# 1. open (first try may redirect to /note-manager, just retry)
opencli browser xhs_pub open "https://creator.xiaohongshu.com/publish/publish?from=tab_switch&target=image"

# 2. detect file input (always re-detect!)
opencli browser xhs_pub eval "var els=document.querySelectorAll('input'); var r=[]; for(var i=0;i<els.length;i++){r.push(i+':'+els[i].type+':'+(els[i].accept||'none'))}; JSON.stringify(r)"
# response: ["0:file:.jpg,.jpeg,.png,.webp"] → index 0, cross-check with `state` → ref [84]

# 3. upload cover
opencli browser xhs_pub upload 84 "D:\code\HotCommentHub\data\cover_food_photo.jpg"

# 4. title (wait for image to settle)
opencli browser xhs_pub fill --name "填写标题会有更多赞哦" "$TITLE"

# 5. body (embedded in JS var, no shell interpolation)
opencli browser xhs_pub eval "var d=document.querySelector('[contenteditable=true]'); var t='春夏的食物是有情绪的。<br><br>一颗刚洗过的杨梅...'; d.innerHTML=t; d.dispatchEvent(new Event('input',{bubbles:true})); 'ok '+d.innerText.length"
# response: ok 639

# 6. publish with fallback check
opencli browser xhs_pub eval "var b=document.querySelector('xhs-publish-btn'); if(b && typeof b._onPublish === 'function') { b._onPublish(); 'called' } else { 'fail: '+typeof b }"
# response: called

# 7. verify (5s wait)
Start-Sleep -Seconds 5
opencli browser xhs_pub eval "window.location.href"
# response: https://creator.xiaohongshu.com/publish/publish?source=&published=true
```

### Critical Do's and Don'ts

| Do | Don't |
|----|-------|
| Use `eval` + `innerHTML` for body content | `opencli fill` on contenteditable (truncates) |
| Call `b._onPublish()` via `eval` with fallback check | `click()` / `dispatchEvent()` on publish btn |
| Use a fixed session name (reuses login) | New session every time (DOM may not render) |
| Verify with `eval "window.location.href"` after 5s wait | Trust `main.py publish` (Python pipeline unstable) |
| **Re-detect file input ref every publish** (eval→state) | Hardcode ref=84 (changes between sessions) |
| **Embed body as JS var directly in eval** | Use shell `$VAR` substitution for body (escaping hell) |
| **Use `<br>` directly, no `\n`** | Use `replace(/\n/g,'<br>')` (PowerShell mangles `\n`) |
| **If page redirects to /note-manager, `open` again** | Give up after first `open` lands on wrong page |
| Copilot writes content → CLI publish (reliable) | DeepSeek API title-body mismatch → manual fix |

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

### DeepSeek API: Title-Body Mismatch

- Problem: run_prod.py calls DeepSeek API via ContentGenerator. Model frequently generates correct title but body belongs to different topic (e.g. title 618 but body about daocheng).
- Workaround: skip AI pipeline, let Copilot write content directly, then CLI publish.
- Always verify title matches body.

### persona search_keywords Matching

- run_prod.py -p <persona> -k <kw> uses persona search_keywords to match hot-list titles, NOT direct search with -k.
- Hot words not matching (e.g. hema, 618, chenkeming) must be added to persona YAML search_keywords.
- Edit YAML with Python, NOT PowerShell replace (pollutes file).

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
8. **Publish retry on redirect**: `open` sometimes lands on `/note-manager` instead of publish page — auto-detect URL and retry `open` once.
9. **File input ref caching**: ref number changes between sessions, always re-detect. Consider a `detect_file_ref()` helper that combines eval+state parsing.
10. **Body content escaping**: shell variable `$BODY_HTML` breaks on quotes/angle brackets. Standardize on JS-embedded `var t='...'` pattern — copilot should generate body with `<br>` already in place.
