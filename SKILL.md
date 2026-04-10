---
name: openrouter-free-helper
description: 监控 OpenRouter 免费模型的到期通知和新模型发现，自动每日检查并推送飞书通知
requires:
  bins: [python3, bb-browser]
  python: [requests, beautifulsoup4]
allowed-tools: Bash, exec
---

# OpenRouter Free Helper

监控 OpenRouter 免费模型的两类关键信息：
1. **到期通知** - 识别 "Going away [日期]" 警告，提前提醒
2. **新模型发现** - 自动发现新加入的免费模型

## 🚀 快速开始

### 前置依赖

**1. 安装 bb-browser**（必需）

```bash
# 使用 Homebrew 安装
brew install bb-browser

# 或使用 npm 全局安装
npm install -g bb-browser
```

**2. 配置 Chrome 调试模式**

bb-browser 需要 Chrome 在调试模式下运行（端口 9222）：

```bash
# 手动启动 Chrome 调试模式
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --no-first-run \
  --no-default-browser-check
```

**或者**：脚本会自动检测并启动 Chrome 调试模式（首次启动可能需要 10-15 秒）

**3. Python 依赖**

```bash
pip3 install requests beautifulsoup4
```

### 安装技能

```bash
# 使用 ClawHub 安装
clawhub install openrouter-free-helper
```

### 配置

编辑配置文件 `~/.openclaw/workspace/skills/openrouter-free-helper/config/config.json`：

```json
{
  "check_time": "08:00",
  "notify_channel": "feishu",
  "notify_target": "user:ou_xxxxxxxxxxxxxxxxxxxxx",
  "status_file": "~/.openclaw/workspace/skills/openrouter-free-helper/data/status.json",
  "openclaw_config": "~/.openclaw/openclaw.json"
}
```

**参数说明**：
- `notify_target`: 飞书用户 ID（格式：`user:ou_xxx`）
- `check_time`: 每日检查时间（24 小时制）
- `status_file`: 状态文件路径（自动创建）

### 启用自动化

技能安装后会自动添加 Cron 任务，每日 08:00 执行检查。

手动检查 Cron 状态：
```bash
openclaw cron list
```

---

## 📖 使用指南

### 手动检查

```bash
# 基础检查（静默模式，仅在变化时通知）
python3 ~/.openclaw/workspace/skills/openrouter-free-helper/scripts/check-models.py

# 详细输出（查看执行过程）
python3 ~/.openclaw/workspace/skills/openrouter-free-helper/scripts/check-models.py --verbose

# 模拟运行（不发送通知）
python3 ~/.openclaw/workspace/skills/openrouter-free-helper/scripts/check-models.py --verbose --dry-run
```

### 查询 bb-browser 适配器

```bash
# 获取所有免费模型列表
bb-browser site openrouter/free-models --json --openclaw

# 查询特定模型的到期信息
bb-browser site openrouter/model-expiry google/gemma-4-26b-a4b-it:free --json --openclaw
```

### 查看状态文件

```bash
cat ~/.openclaw/workspace/skills/openrouter-free-helper/data/status.json
```

**状态文件结构**：
```json
{
  "last_check": "2026-04-10T21:59:06.858640",
  "known_models": ["openrouter/google/gemma-4-26b-a4b-it:free", ...],
  "expiring_soon": [
    {
      "model": "arcee-ai/trinity-large-preview",
      "going_away_date": "2026-04-22",
      "days_left": 11,
      "url": "https://openrouter.ai/arcee-ai/trinity-large-preview"
    }
  ]
}
```

---

## 🔔 通知规则

### 到期提醒（分级推送）

| 级别 | 条件 | 行为 |
|------|------|------|
| 🚨 **紧急** | ≤1 天到期 | 立即推送 |
| ⚠️ **警告** | ≤3 天到期 | 推送提醒 |
| 📅 **预告** | >3 天到期 | 仅首次发现时推送 |

**去重机制**：
- 同一模型的到期通知，只在首次发现或日期变化时推送
- 避免每天重复发送相同提醒

### 新模型发现

- 仅在首次发现时推送
- 每次最多显示 10 个新模型
- 自动过滤已配置的模型

### 静默规则

以下情况**不发送通知**：
- 无新模型发现
- 到期通知无变化（且不在紧急/警告级别）
- 抓取失败（避免误报）

---

## 🛠️ 故障排查

### Chrome 调试模式问题

**症状**：`bb-browser` 报错 "Chrome not connected"

**解决**：
```bash
# 1. 检查 Chrome 是否运行
ps aux | grep "remote-debugging-port=9222"

# 2. 手动启动 Chrome 调试模式
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222

# 3. 验证端口是否可访问
curl http://127.0.0.1:9222/json/version
```

### bb-browser 适配器问题

**症状**：`bb-browser site openrouter/free-models` 返回空列表

**检查**：
```bash
# 查看适配器是否存在
ls -la ~/.bb-browser/sites/openrouter/

# 测试适配器
bb-browser site openrouter/free-models --json --openclaw
```

**修复**：重新安装技能或手动创建适配器（见 `references/openrouter-structure.md`）

### Python 依赖缺失

**症状**：`ModuleNotFoundError: No module named 'requests'`

**解决**：
```bash
pip3 install requests beautifulsoup4
```

---

## 📁 文件结构

```
~/.openclaw/workspace/skills/openrouter-free-helper/
├── SKILL.md                      # 技能文档
├── config/
│   └── config.json               # 配置文件
├── data/
│   └── status.json               # 状态文件（自动生成）
├── scripts/
│   ├── check-models.py           # 主检查脚本
│   └── fetch_page.py             # 网页抓取模块
├── references/
│   └── openrouter-structure.md   # OpenRouter 结构分析
└── adapters/
    └── openrouter/               # bb-browser 适配器（在 ~/.bb-browser/sites/）
```

---

## 🔧 高级配置

### 修改检查频率

编辑 Cron 配置：
```bash
openclaw cron edit
```

将 `0 8 * * *` 改为其他时间（如每小时检查：`0 * * * *`）

### 添加更多监控模型

编辑 `~/.openclaw/openclaw.json`，在 `defaults.models` 或 `agents[].model` 中添加 `:free` 后缀的模型 ID：

```json
{
  "defaults": {
    "models": {
      "openrouter/google/gemma-4-26b-a4b-it:free": {...},
      "openrouter/google/gemma-4-31b-it:free": {...}
    }
  }
}
```

脚本会自动识别并监控这些模型的到期状态。

---

## 📊 技术实现

### 三层抓取 fallback

1. **Layer 1**: `requests` + BeautifulSoup（静态内容）
2. **Layer 2**: `web_fetch` 工具（备用）
3. **Layer 3**: `bb-browser` 适配器（动态内容）

### API fallback

当浏览器自动化失败时，降级使用 OpenRouter 内部 API：
- 端点：`https://openrouter.ai/api/frontend/models`
- 无需认证，直接返回免费模型列表

### 智能 Chrome 管理

- 自动检测 Chrome 调试模式状态
- 端口探活验证（`http://127.0.0.1:9222/json/version`）
- 独立 profile 避免冲突（`/tmp/openclaw-chrome-debug`）
- 不干扰用户现有 Chrome 会话

---

## 🌟 特性亮点

- ✅ **零打扰**：无变化时静默执行
- ✅ **分级提醒**：紧急/警告/预告三级通知
- ✅ **去重机制**：避免重复推送相同信息
- ✅ **自动修复**：Chrome 未运行时自动启动
- ✅ **多层兜底**：三层抓取 + API fallback
- ✅ **时区感知**：所有时间计算基于 Asia/Shanghai

---

## 📝 更新日志

### v1.0.0 (2026-04-10)
- 初始版本发布
- 支持到期通知检测
- 支持新模型发现
- 分级提醒机制
- 智能 Chrome 管理
- 多层 fallback 机制

---

## 🤝 贡献

问题反馈或功能建议，欢迎联系 @neoshi

---

**最后更新**: 2026-04-10  
**维护者**: 银月 (Neo Shi)
