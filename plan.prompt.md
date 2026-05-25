## Plan: HotCommentHub — CLI 驱动的多渠道热点聚合 + AI 创作 + 发布

### 产品一句话
**配置人设+渠道 → CLI 一句话指令 → AI 全网搜热点 → 生成草稿(Markdown) → 人工审阅 → 一键发布多平台**

---

### 核心交互（纯 CLI + 文件）

```bash
# 方式1：命令行直接指定
python main.py run --persona foodie --keyword "网红餐厅翻车" --platform xiaohongshu

# 方式2：从配置文件读取（最常用）
# 编辑 config/settings.yaml → 人设/渠道/关键词/发布平台已预设
python main.py run

# 方式3：交互模式
python main.py interactive
> 我是美食家，帮我搜网红餐厅翻车，发小红书

# 方式4：定时自动运行
python main.py schedule  # 启动定时调度器，按配置频率自动执行
```

**交互输出**：
```
🚀 HotCommentHub v1.0 | 人设: 美食家 | 目标平台: 小红书
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔍 [1/4] 多渠道搜索中...
  ✅ 微博      找到 12 个相关话题
  ✅ 知乎      找到 8 个相关话题
  ✅ 小红书    找到 6 个相关话题
  ✅ B站       找到 5 个相关话题
  ✅ 抖音      找到 7 个相关话题
  ✅ 今日头条  找到 3 个相关话题

📊 [2/4] 过滤合并 → 精选 5 个高价值话题
  🔥🔥🔥🔥🔥 网红火锅店被曝使用预制菜 (微博)
  🔥🔥🔥🔥   某奶茶品牌新品翻车 (小红书)
  🔥🔥🔥🔥   米其林新增街头小吃推荐 (知乎)
  ...

🧠 [3/4] AI 深度分析评论中...
  ✅ 情感分析完成 | 观点提取完成 | 金句筛选完成

✍️  [4/4] 生成 3 篇草稿...
  ✅ 角度1: 事件报道 → data/drafts/2026-05-25_01_event.md
  ✅ 角度2: 观点评论 → data/drafts/2026-05-25_02_opinion.md
  ✅ 角度3: 避坑指南 → data/drafts/2026-05-25_03_guide.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 草稿已生成，请审阅:
   python main.py review                    # 进入审阅模式
   python main.py publish --draft 1         # 直接发布指定草稿
   python main.py publish --all             # 发布所有通过的草稿
```

---

### 系统架构（纯 Python CLI，无前端，零数据库）

```
┌────────────────────────────────────────────────┐
│                  main.py (CLI 入口)             │
│  run | interactive | review | publish |        │
│  schedule | status | report | check-login      │
└────────┬───────────────────┬───────────────────┘
         │                   │
         ▼                   ▼
┌─────────────────┐  ┌──────────────────────────┐
│  Orchestrator   │  │  Scheduler (APScheduler)  │
│  编排引擎        │  │  定时触发 or 手动触发      │
│  搜索→分析→生成  │  └──────────────────────────┘
└───┬──┬──┬──┬────┘
    │  │  │  │
    ▼  ▼  ▼  ▼
┌────┐┌────┐┌────┐┌──────────┐
│搜索││AI  ││生成││发布&报告  │
│引擎││分析││引擎││引擎      │
└────┘└────┘└────┘└──────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│         文件系统 (零数据库)               │
│  data/drafts/*.md    data/reports/*.md   │
│  data/published.json data/topics_cache.json │
│  logs/*.log                              │
└─────────────────────────────────────────┘
```

---

### 模块详解

#### 1. 人设系统 (`src/personas/`)

YAML 定义 → 搜索关键词/语气/标签/发布偏好一步到位。

```yaml
# config/personas/foodie.yaml
persona:
  name: "美食家"
  tone: "犀利、有态度、偶尔幽默"
  domains: [美食探店, 网红餐厅, 食品安全, 特色小吃]
  search_keywords: [网红餐厅, 踩雷, 美食探店, 外卖, 奶茶新品]
  content_style:
    length: "medium"
    emoji_style: "克制"
    hashtags: ["#美食探店", "#避雷指南", "#真实测评"]
  publish_preferences:
    platforms: [xiaohongshu]
    best_times: ["11:30", "17:30", "21:00"]
```

#### 2. 多渠道搜索引擎 (`src/search/`)

| 渠道 | opencli 命令 | 登录 |
|------|-------------|------|
| 微博 | `weibo hot` + `search` | 🔐 |
| 知乎 | `zhihu hot` + `search` | 🔐 |
| B站 | `bilibili hot` + `search` | 🔐 |
| 小红书 | `xiaohongshu search` + `feed` | 🔐 |
| 抖音 | `douyin hot` + `search` | 🔐 |
| 今日头条 | `toutiao hot` | 🌐 |
| Twitter/X | `twitter trending` + `search` | 🔐 |
| Reddit | `reddit hot` + `search` | 🔐 |
| 什么值得买 | `smzdm search` | 🔐 |

> 全部通过 opencli Browser Bridge 复用 Chrome 登录态。`config/settings.yaml` 可开关任何渠道。

#### 3. 评论深度分析 (`src/ai/comment_analyzer.py`)

- 情感分析（正面/负面/中性比例）
- 观点聚类（主流观点提取）
- 争议点提取
- 高赞评论精选（去水军）
- 舆论风向一句话总结

#### 4. 人设化内容生成 (`src/ai/content_generator.py`)

生成 2-3 篇不同角度 → 输出 Markdown 文件：
- 角度1: 事件报道型
- 角度2: 观点评论型
- 角度3: 攻略/指南型

#### 5. 审阅与发布（纯 CLI）

```bash
python main.py review           # 交互式审阅所有待发草稿
python main.py publish --all    # 发布所有通过的
python main.py publish -d 1     # 发布指定草稿
```

**支持发布平台**: 小红书、微博、B站、知乎（通过 opencli publish 命令）

#### 6. 每日热点汇总报告

每天自动生成 `data/reports/YYYY-MM-DD_daily.md`

#### 7. 数据存储（纯文件，零数据库）

```
data/
├── drafts/                           # AI 生成草稿 (.md)
├── reports/                          # 每日报告 (.md)
├── topics_cache.json                 # 话题 hash → 去重
├── published.json                    # 发布历史索引
└── logs/                             # 日志
```

---

### 配置文件 (`config/settings.yaml`)

```yaml
persona: "foodie"
keyword: ""
channels:
  enabled: [weibo, zhihu, bilibili, xiaohongshu, douyin, toutiao, smzdm]
  max_topics_per_channel: 10
generation:
  drafts_count: 3
  angles: [event_report, opinion, guide]
publish:
  platforms: [xiaohongshu]
  max_per_day: 4
  min_interval_minutes: 120
review:
  mode: "always"
schedule:
  enabled: true
  cron: "0 8,14,20 * * *"
ai:
  provider: "deepseek"
  model: "deepseek-chat"
```

---

### 项目结构

```
HotCommentHub/
├── main.py
├── src/
│   ├── orchestrator.py
│   ├── intent_parser.py
│   ├── personas/manager.py
│   ├── search/
│   │   ├── engine.py
│   │   ├── base.py
│   │   ├── weibo_searcher.py
│   │   ├── zhihu_searcher.py
│   │   ├── bilibili_searcher.py
│   │   ├── xiaohongshu_searcher.py
│   │   ├── douyin_searcher.py
│   │   ├── toutiao_searcher.py
│   │   ├── twitter_searcher.py
│   │   ├── reddit_searcher.py
│   │   └── smzdm_searcher.py
│   ├── ai/
│   │   ├── comment_analyzer.py
│   │   ├── content_generator.py
│   │   └── quality_checker.py
│   ├── publish/
│   │   ├── engine.py
│   │   ├── base.py
│   │   ├── xiaohongshu_publisher.py
│   │   ├── weibo_publisher.py
│   │   ├── bilibili_publisher.py
│   │   └── zhihu_publisher.py
│   ├── reports/daily_digest.py
│   ├── scheduler.py
│   └── utils/
│       ├── logger.py
│       ├── opencli.py
│       └── file_store.py
├── config/
│   ├── settings.yaml
│   ├── personas/{foodie,gadget_reviewer,beauty_blogger,travel_expert}.yaml
│   └── prompts/{comment_analysis,content_generation}.txt
├── data/
│   ├── drafts/
│   ├── reports/
│   ├── topics_cache.json
│   └── published.json
├── logs/
├── .env
├── pyproject.toml
└── SKILL.md
```

---

### 全部 CLI 命令

```bash
python main.py run                                     # 读配置全流程
python main.py run --persona foodie --keyword "奶茶"    # 覆盖参数
python main.py interactive                             # 对话模式
python main.py review                                  # 审阅草稿
python main.py publish --all                           # 发布全部
python main.py publish --draft 1                       # 发布指定
python main.py schedule                                # 启动定时器
python main.py status                                  # 今日统计
python main.py report                                  # 每日报告
python main.py check-login                             # 登录检查
python main.py personas                                # 人设列表
```

---

### 实施计划（6 Phase）

| Phase | 内容 |
|-------|------|
| 1 | 项目骨架、opencli 封装、file_store |
| 2 | 4 个人设 YAML、配置加载 |
| 3 | 9 渠道搜索适配器、并行调度 |
| 4 | 意图解析、评论分析、内容生成、prompt |
| 5 | CLI 审阅、多平台发布、每日报告 |
| 6 | APScheduler 定时、联调、异常处理 |

---

### 依赖

```toml
[project]
name = "hotcommenthub"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.28.0", "pyyaml>=6.0", "python-dotenv>=1.0.0",
    "loguru>=0.7.0", "apscheduler>=3.10.0", "pydantic>=2.0.0",
]
```
