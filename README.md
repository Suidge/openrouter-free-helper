# OpenRouter Free Model Monitor

<div align="center">

**监控 OpenRouter 免费模型的到期通知和新模型发现**

*Monitor OpenRouter free models for expiration notices and new model discoveries*

[![ClawHub](https://img.shields.io/badge/ClawHub-openrouter--free--helper-blue)](https://clawhub.ai/skills/openrouter-free-helper)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9+-blue)](https://python.org)

</div>

---

## 📖 简介 | Introduction

**中文**：  
OpenRouter Free Model Monitor 是一个自动化工具，用于监控 OpenRouter 平台上的免费模型。它会自动检测两类关键信息：

1. **到期通知** - 识别模型的 "Going away [日期]" 警告，提前提醒用户
2. **新模型发现** - 自动发现新加入的免费模型并推送通知

该工具设计为 OpenClaw 技能，支持每日自动检查并通过飞书推送通知。

**English**:  
OpenRouter Free Model Monitor is an automated tool for monitoring free models on the OpenRouter platform. It automatically detects two types of critical information:

1. **Expiration Notices** - Identifies "Going away [date]" warnings and alerts users in advance
2. **New Model Discovery** - Automatically discovers newly added free models and sends notifications

This tool is designed as an OpenClaw skill, supporting daily automated checks with Feishu notifications.

---

## ✨ 特性 | Features

| 中文 | English |
|------|---------|
| 🚨 **分级提醒** - 紧急 (≤1 天) / 警告 (≤3 天) / 预告 (>3 天) | 🚨 **Tiered Alerts** - Urgent (≤1 day) / Warning (≤3 days) / Notice (>3 days) |
| 🔕 **智能去重** - 避免重复推送相同通知 | 🔕 **Smart Deduplication** - Avoids duplicate notifications |
| 🌐 **三层抓取** - requests → web_fetch → bb-browser | 🌐 **3-Layer Fallback** - requests → web_fetch → bb-browser |
| 🤖 **自动 Chrome** - 智能管理 Chrome 调试模式 | 🤖 **Auto Chrome** - Intelligent Chrome debug mode management |
| 📅 **定时检查** - 支持 Cron 每日自动执行 | 📅 **Scheduled Checks** - Supports daily Cron automation |
| 📱 **飞书通知** - 无缝集成飞书消息推送 | 📱 **Feishu Integration** - Seamless Feishu message notifications |

---

## 🚀 快速开始 | Quick Start

### 前置要求 | Prerequisites

```bash
# 1. 安装 bb-browser (必需 | Required)
brew install bb-browser
# 或 | Or: npm install -g bb-browser

# 2. Python 依赖 | Python Dependencies
pip3 install requests beautifulsoup4

# 3. Chrome 调试模式 | Chrome Debug Mode
# 脚本会自动启动，或手动运行：
# Script auto-starts, or manually run:
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222
```

### 安装方式 | Installation

**方式 1: 使用 ClawHub (推荐) | Method 1: Via ClawHub (Recommended)**
```bash
clawhub install openrouter-free-helper
```

**方式 2: Git 克隆 | Method 2: Git Clone**
```bash
git clone https://github.com/Suidge/openrouter-free-helper.git \
  ~/.openclaw/workspace/skills/openrouter-free-helper
```

### 配置 | Configuration

编辑配置文件 | Edit config file `config/config.json`:

```json
{
  "check_time": "08:00",
  "notify_channel": "feishu",
  "notify_target": "user:ou_xxxxxxxxxxxxxxxxxxxxx",
  "status_file": "~/.openclaw/workspace/skills/openrouter-free-helper/data/status.json",
  "openclaw_config": "~/.openclaw/openclaw.json"
}
```

| 参数 | Parameter | 说明 | Description |
|------|-----------|------|-------------|
| `check_time` | 检查时间 | 每日检查时间 (24 小时制) | Daily check time (24h format) |
| `notify_target` | 通知目标 | 飞书用户 ID (格式：`user:ou_xxx`) | Feishu user ID (format: `user:ou_xxx`) |

---

## 📖 使用指南 | Usage Guide

### 手动检查 | Manual Check

```bash
# 基础检查 (静默模式) | Basic check (silent mode)
python3 scripts/check-models.py

# 详细输出 | Verbose output
python3 scripts/check-models.py --verbose

# 模拟运行 (不发送通知) | Dry run (no notifications)
python3 scripts/check-models.py --verbose --dry-run
```

### 使用 bb-browser 适配器 | Using bb-browser Adapters

```bash
# 获取所有免费模型 | Get all free models
bb-browser site openrouter/free-models --json --openclaw

# 查询特定模型到期信息 | Check specific model expiry
bb-browser site openrouter/model-expiry google/gemma-4-26b-a4b-it:free --json --openclaw
```

### 查看状态文件 | View Status File

```bash
cat data/status.json
```

**示例输出 | Example Output**:
```json
{
  "last_check": "2026-04-10T21:59:06.858640",
  "known_models": ["openrouter/google/gemma-4-26b-a4b-it:free"],
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

## 🔔 通知规则 | Notification Rules

### 到期提醒分级 | Expiration Alert Tiers

| 级别 | Level | 条件 | Condition | 行为 | Action |
|------|-------|------|-----------|------|--------|
| 🚨 | 紧急 | ≤1 天 | ≤1 day | 立即推送 | Send immediately |
| ⚠️ | 警告 | ≤3 天 | ≤3 days | 推送提醒 | Send reminder |
| 📅 | 预告 | >3 天 | >3 days | 仅首次 | First discovery only |

### 静默规则 | Silent Mode Rules

以下情况**不发送通知** | **No notification** in these cases:
- 无新模型发现 | No new models discovered
- 到期通知无变化 (且不在紧急/警告级别) | No expiration changes (and not urgent/warning level)
- 抓取失败 (避免误报) | Fetch failed (avoid false positives)

---

## 🛠️ 故障排查 | Troubleshooting

### Chrome 调试模式问题 | Chrome Debug Mode Issues

**症状 | Symptom**: `bb-browser` 报错 "Chrome not connected"

**解决方案 | Solution**:
```bash
# 1. 检查 Chrome 是否运行 | Check if Chrome is running
ps aux | grep "remote-debugging-port=9222"

# 2. 手动启动 Chrome 调试模式 | Manually start Chrome debug mode
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222

# 3. 验证端口 | Verify port
curl http://127.0.0.1:9222/json/version
```

### Python 依赖缺失 | Missing Python Dependencies

**症状 | Symptom**: `ModuleNotFoundError: No module named 'requests'`

**解决方案 | Solution**:
```bash
pip3 install requests beautifulsoup4
```

### bb-browser 适配器问题 | bb-browser Adapter Issues

**症状 | Symptom**: 返回空列表 | Returns empty list

**检查 | Check**:
```bash
ls -la ~/.bb-browser/sites/openrouter/
bb-browser site openrouter/free-models --json --openclaw
```

---

## 📁 项目结构 | Project Structure

```
openrouter-free-helper/
├── README.md                    # 项目说明 | Project documentation
├── SKILL.md                     # OpenClaw 技能文档 | OpenClaw skill doc
├── package.json                 # 项目元数据 | Project metadata
├── config/
│   └── config.json              # 配置文件 | Configuration file
├── data/
│   └── status.json              # 状态文件 (自动生成) | Status file (auto-generated)
├── scripts/
│   ├── check-models.py          # 主检查脚本 | Main check script
│   └── fetch_page.py            # 网页抓取模块 | Web scraping module
└── references/
    └── openrouter-structure.md  # OpenRouter 结构分析 | OpenRouter structure analysis
```

---

## 🔧 高级配置 | Advanced Configuration

### 修改检查频率 | Modify Check Frequency

编辑 Cron 配置 | Edit Cron config:
```bash
openclaw cron edit
```

将 `0 8 * * *` 改为其他时间 (如每小时检查：`0 * * * *`)  
Change `0 8 * * *` to other time (e.g., hourly: `0 * * * *`)

### 添加更多监控模型 | Add More Monitored Models

编辑 `~/.openclaw/openclaw.json`，在 `defaults.models` 或 `agents[].model` 中添加 `:free` 后缀的模型 ID：

Edit `~/.openclaw/openclaw.json`, add `:free` suffixed model IDs in `defaults.models` or `agents[].model`:

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
The script will automatically identify and monitor these models' expiration status.

---

## 📊 技术实现 | Technical Implementation

### 三层抓取 Fallback | 3-Layer Fetch Fallback

1. **Layer 1**: `requests` + BeautifulSoup (静态内容 | Static content)
2. **Layer 2**: `web_fetch` 工具 (备用 | Backup)
3. **Layer 3**: `bb-browser` 适配器 (动态内容 | Dynamic content)

### API Fallback

当浏览器自动化失败时，降级使用 OpenRouter 内部 API：  
When browser automation fails, fallback to OpenRouter internal API:

- **端点 | Endpoint**: `https://openrouter.ai/api/frontend/models`
- **无需认证 | No auth required**

### 智能 Chrome 管理 | Smart Chrome Management

- ✅ 自动检测 Chrome 调试模式状态 | Auto-detect Chrome debug mode status
- ✅ 端口探活验证 | Port probing verification
- ✅ 独立 profile 避免冲突 | Isolated profile to avoid conflicts
- ✅ 不干扰用户现有 Chrome 会话 | No interference with existing Chrome sessions

---

## 📝 更新日志 | Changelog

### v1.0.2 (2026-04-10)
- 🌐 Add GitHub repository
- 📝 Update repository URL in package.json

### v1.0.1 (2026-04-10)
- 📝 Fix installation instructions in SKILL.md
- ➕ Add homepage link to ClawHub

### v1.0.0 (2026-04-10)
- 🎉 Initial release
- ✅ Expiration notice detection
- ✅ New model discovery
- ✅ Tiered alert system
- ✅ Smart Chrome management
- ✅ Multi-layer fallback mechanism

---

## 🤝 贡献 | Contributing

欢迎提交 Issue 和 Pull Request！  
Issues and Pull Requests are welcome!

**问题反馈 | Bug Reports**: https://github.com/Suidge/openrouter-free-helper/issues

---

## 📄 许可证 | License

MIT License

---

<div align="center">

**Made with ❤️ by Neo Shi (银月)**

[⬆️ 返回顶部 | Back to Top](#openrouter-free-model-monitor)

</div>
