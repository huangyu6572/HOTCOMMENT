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

### 系统架构（纯 Python CLI，无前端）

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
│  Phase 1→4 流程  │  └──────────────────────────┘
└───┬──┬──┬──┬────┘
    │  │  │  │
    ▼  ▼  ▼  ▼
┌────┐┌────┐┌────┐┌──────────┐
│搜索││AI  ││生成││发布&报告  │
│引擎││分析││引擎││引擎      │
└────┘└────┘└────┘└──────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │
│  topics/comm.   │
│  drafts/posts   │
└─────────────────┘
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

每天自动生成 `data/reports/YYYY-MM-DD_daily.md`：

```markdown
# 🔥 每日热点报告 — 2026-05-25

## 📊 概览
采集渠道: 9个 | 采集话题: 87 | 生成草稿: 3 | 已发布: 1

## 🍔 美食领域 (人设匹配)
| # | 话题 | 热度 | 来源 | 观点风向 |
|---|------|------|------|---------|
| 1 | 网红火锅店被曝预制菜 | 🔥🔥🔥🔥🔥 | 微博 | 😡 一边倒批评 |
| 2 | 某奶茶新品翻车 | 🔥🔥🔥🔥 | 小红书 | 🤔 毁誉参半 |

## 📝 今日生成内容 & 📈 昨日数据
...
```

---

### 配置文件 (`config/settings.yaml`)

```yaml
# ===== 人设 =====
persona: "foodie"  # foodie/gadget_reviewer/beauty_blogger/travel_expert

# ===== 搜索关键词（覆盖人设默认值） =====
keyword: ""        # 留空则用人设 search_keywords

# ===== 搜索渠道 =====
channels:
  enabled: [weibo, zhihu, bilibili, xiaohongshu, douyin, toutiao, smzdm]
  max_topics_per_channel: 10

# ===== 内容生成 =====
generation:
  drafts_count: 3           # 每次生成 2-3 篇
  angles: [event_report, opinion, guide]

# ===== 发布平台 =====
publish:
  platforms: [xiaohongshu]  # xiaohongshu/weibo/bilibili/zhihu
  max_per_day: 4
  min_interval_minutes: 120

# ===== 审阅模式 =====
review:
  mode: "always"            # always(人工审阅)/auto(自动发布)

# ===== 调度 =====
schedule:
  enabled: true
  cron: "0 8,14,20 * * *"  # 每8/14/20点

# ===== 通知 =====
notifications:
  enabled: false
  webhook_url: ""

# ===== AI =====
ai:
  provider: "deepseek"
  model: "deepseek-chat"
```

---

### 项目结构（纯 CLI，无前端）

```
HotCommentHub/
├── main.py                          # CLI 入口 (全部命令)
├── src/
│   ├── orchestrator.py              # 核心编排引擎 ⭐
│   ├── intent_parser.py             # 自然语言意图解析
│   ├── personas/
│   │   └── manager.py               # 人设加载/管理
│   ├── search/
│   │   ├── engine.py                # 搜索调度器（并行）
│   │   ├── weibo_searcher.py
│   │   ├── zhihu_searcher.py
│   │   ├── bilibili_searcher.py
│   │   ├── xiaohongshu_searcher.py
│   │   ├── douyin_searcher.py
│   │   ├── toutiao_searcher.py
│   │   ├── twitter_searcher.py
│   │   ├── reddit_searcher.py
│   │   ├── smzdm_searcher.py
│   │   └── base.py                  # 搜索适配器基类
│   ├── ai/
│   │   ├── comment_analyzer.py      # 评论深度分析 ⭐
│   │   ├── content_generator.py     # 人设化内容生成 ⭐
│   │   └── quality_checker.py       # 内容质检
│   ├── publish/
│   │   ├── engine.py                # 发布调度
│   │   ├── xiaohongshu_publisher.py
│   │   ├── weibo_publisher.py
│   │   ├── bilibili_publisher.py
│   │   ├── zhihu_publisher.py
│   │   └── base.py
│   ├── reports/
│   │   └── daily_digest.py          # 每日热点报告生成
│   ├── scheduler.py                 # 定时调度
│   ├── db/
│   │   ├── models.py                # SQLAlchemy models
│   │   └── database.py
│   └── utils/
│       ├── logger.py
│       └── opencli.py               # opencli 命令封装
├── config/
│   ├── settings.yaml                # 全局配置
│   ├── personas/
│   │   ├── foodie.yaml
│   │   ├── gadget_reviewer.yaml
│   │   ├── beauty_blogger.yaml
│   │   └── travel_expert.yaml
│   └── prompts/
│       ├── comment_analysis.txt
│       └── content_generation.txt
├── data/
│   ├── drafts/                      # 生成草稿(Markdown)
│   ├── reports/                     # 每日热点报告
│   └── hotcommenthub.db             # SQLite
├── logs/
├── .env                             # DEEPSEEK_API_KEY
├── pyproject.toml
└── README.md
```

---

### 全部 CLI 命令

```bash
# 核心流程
python main.py run                                    # 从配置读取人设，全流程执行
python main.py run --persona foodie --keyword "奶茶"   # 命令行覆盖
python main.py interactive                            # 交互对话模式

# 审阅发布
python main.py review                                 # 交互审阅所有草稿
python main.py publish --all                          # 发布所有通过草稿
python main.py publish --draft 1                      # 发布指定草稿
python main.py publish --draft 1 --platform weibo     # 发布到指定平台

# 调度
python main.py schedule                               # 启动定时调度器
python main.py schedule --once                        # 只执行一次后退出

# 状态 & 报告
python main.py status                                 # 查看今日统计
python main.py report                                 # 生成每日热点报告
python main.py report --date 2026-05-25               # 指定日期

# 管理
python main.py check-login                            # 检查所有平台登录态
python main.py personas                               # 列出所有人设
python main.py config                                 # 查看当前配置
```



### 实施计划（6 个阶段，一次交付）

#### Phase 1: 基础设施
- 项目骨架、SQLite、opencli 安装、.env 配置
- `src/utils/opencli.py` opencli 命令封装

#### Phase 2: 人设 + 配置
- 4 个 YAML 人设模板、配置加载、人设管理器

#### Phase 3: 多渠道搜索
- 9 个搜索适配器、并行调度、评论采集去重

#### Phase 4: AI 分析 + 生成
- 意图解析、评论深度分析、人设化内容生成、prompt 模板

#### Phase 5: 审阅 + 发布
- CLI 审阅交互、多平台发布、每日报告生成

#### Phase 6: 调度 + 联调
- APScheduler 定时、全流程联调、check-login、异常处理

---

### 风险矩阵

| 风险 | 应对 |
|------|------|
| opencli 命令不稳定 | browser 原语兜底 |
| AI 内容同质化 | 多角度 + 人设变量 + 评论金句 |
| 小红书封号 | 频率限制 ≤4篇/天 + 人工审阅模式 |
| 搜索耗时过长 | 并行搜索 + 超时 + 渠道开关 |
| DeepSeek 不稳定 | 支持切换 OpenAI/Claude |

---

### 验证 Checklist

- [ ] `opencli doctor` 通过
- [ ] 所有渠道 hot 命令能返回数据
- [ ] `python main.py run` 全流程成功
- [ ] drafts/ 目录生成 3 篇 Markdown
- [ ] `python main.py publish` 成功发布到小红书
- [ ] `python main.py report` 生成每日报告
- [ ] `python main.py schedule` 定时运行正常
