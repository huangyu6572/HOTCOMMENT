# HotCommentHub — 真实热榜 → 人设化小红书内容

## 一句话
**用真实热榜数据 + 人设语气 → 写内容**

## 快速开始

```bash
# 1. 确保 opencli 连接正常
opencli doctor

# 2. 生成内容
python run_prod.py -p foodie

# 3. 审阅草稿
python main.py review

# 4. 发布
python main.py publish -d 1
```

## 五步固化流程 (run_prod.py)

1. `opencli zhihu hot` → 知乎热榜
2. `opencli bilibili hot` → B站热门
3. `opencli xiaohongshu search` → 小红书搜索
4. 按人设关键词过滤 TOP 3-5
5. AI 分析 + 生成草稿 → `data/drafts/*.md`

## 命令

```bash
python run_prod.py -p foodie              # 美食家
python run_prod.py -p gadget_reviewer     # 数码
python run_prod.py -p beauty_blogger      # 美妆
python run_prod.py -p foodie -k "火锅"    # 指定关键词
python run_prod.py --dry-run              # 只看不生成
python main.py review                     # 审阅
python main.py publish -d 1               # 发布
python main.py status                     # 统计
```

## 渠道

| 渠道 | 命令 | 状态 |
|------|------|------|
| 知乎 | `zhihu hot` | ✅ |
| B站 | `bilibili hot` | ✅ |
| 小红书 | `xiaohongshu search` | ✅ |
| 微博 | - | ❌ 已移除 |

## 内容风格

- 像真人博主聊天，不用"首先其次最后综上所述"
- 不暴露来源（不写"知乎热榜第X名"）
- 引用网友观点自然融入
- 每段 2-3 句，段落留白
- 有态度、有细节、不堆感叹号

## 验证通过的命令

```bash
opencli doctor
opencli zhihu hot --limit 10 -f json
opencli bilibili hot --limit 10 -f json
opencli xiaohongshu search "美食" --limit 5 -f json
```

## 结构

```
HotCommentHub/
├── run_prod.py       # 生产脚本
├── main.py           # CLI (发布/审阅)
├── SKILL.md
├── src/{search,ai,publish,personas,utils}/
├── config/{settings.yaml,personas/*.yaml,prompts/*.txt}
└── data/{drafts/,reports/,published.json}
```
