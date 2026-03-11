# mini-bot

超輕量個人 AI 助理框架

## 簡介

mini-bot 是一個模組化的個人 AI 助理框架，提供統一的 LLM 介面、多頻道支援、工具呼叫與長期記憶功能。

## 核心概念

### 設計原則

1. **依賴注入**：所有元件（LLM、Storage、ContextBuilder、Tools）皆可替換
2. **統一訊息格式**：`UserMessage` 和 `AssistantMessage` 抽象化頻道差異
3. **非同步優先**：基於 asyncio 的非阻塞操作
4. **多對話支援**：每個聊天室擁有獨立的對話歷史
5. **訊息佇列**：非同步處理，支援背景執行

### 訊息流程

```
使用者 → Channel → MessageQueue → AgentLoop → LLM → Storage
                                    ↓
                                 Tools
                                    ↓
使用者 ← Channel ← MessageQueue ← Response
```

## 安裝

### 安裝依賴

```bash
cd mini-bot
pip install -r requirements.txt
```

### 可編輯模式安裝（開發用）

```bash
pip install -e .
```

### 解除安裝

```bash
# 移除套件
pip uninstall minibot

# 清除配置檔與資料（可選）
rm -rf ~/.minibot
```

### 啟動

```bash
# 直接執行
python -m minibot.main

# 或使用前景模式（Console）
python -m minibot.main foreground

# 背景模式
python -m minibot.main start
```

## 快速開始

### 1. 配置

首次執行會自動建立 `~/.minibot/minibot.json`：

```json
{
  "llm": {
    "providers": {
      "openrouter": {
        "api_key": "your-api-key",
        "enabled": true,
        "model": "openai/gpt-4o-mini",
        "base_url": "https://openrouter.ai/api/v1"
      }
    },
    "default": "openrouter",
    "temperature": 0.7,
    "max_tokens": 8192
  },
  "storage": {
    "type": "sqlite",
    "path": "~/.minibot/data/sessions.db"
  },
  "channels": {
    "console": {
      "enabled": true
    }
  },
  "tools": {
    "brave_api_key": "",
    "max_tool_iterations": 100
  },
  "memory": {
    "max_history": 50,
    "threshold": 30
  }
}
```

### 2. 執行

```bash
# Console 模式
python -m minibot.main

# 前景模式
python -m minibot.main foreground

# 背景模式
python -m minibot.main start
```

### 3. Console 指令

| 指令 | 說明 |
|------|------|
| `你好` | 發送到 default 對話 |
| `@123 你好` | 發送到 chat_id=123 |
| `@123 /reset` | 清除 chat_id=123 的歷史 |
| `/reset` | 清除所有歷史 |
| `/exit` | 離開 |

## 使用方式

### Python API

```python
from minibot.agent import AgentLoop, AgentConfig
from minibot.llms import OpenAILLM
from minibot.storage import MemoryStorage
from minibot.context import FileContextBuilder
from minibot.message import UserMessage

# 初始化
llm = OpenAILLM(api_key="sk-xxx", default_model="gpt-4o-mini")
storage = MemoryStorage()
context_builder = FileContextBuilder()
agent = AgentLoop(AgentConfig(), llm, storage, context_builder)

# 處理訊息
user_msg = UserMessage(text="你好", chat_id="123")
response = await agent.process(user_msg)
print(response.text)
```

### Telegram

```python
from minibot.channels.telegram import TelegramAdapter

telegram = TelegramAdapter(bot_token="your-token")
asyncio.run(telegram.run(handle))
```

## 架構

```
src/minibot/
├── agent/           # AgentLoop 核心
├── llms/            # LLM Providers
│   ├── base.py     # LLMProvider 介面
│   ├── openai.py
│   ├── minimax.py
│   └── openrouter.py
├── bus/             # Message Bus
│   ├── message.py
│   ├── message_queue.py
│   └── events.py
├── storage/         # Storage Providers
│   ├── base.py
│   ├── memory.py
│   └── sqlite.py
├── context/         # Context Builders
│   ├── builder.py
│   ├── file_builder.py
│   └── workspace.py
├── tools/           # Tool Implementations
│   ├── filesystem.py
│   ├── shell.py
│   ├── web_search.py
│   └── web_fetch.py
├── memory/          # Long-term Memory
├── skills/          # Skill Definitions
├── config/          # Configuration
├── channels/        # Channel Adapters
├── templates/       # System Prompt Templates
└── main.py         # Entry Point
```

## 元件說明

### LLM Providers

| Provider | 說明 |
|----------|------|
| OpenAI | OpenAI API |
| MiniMax | MiniMax AI |
| OpenRouter | 多模型聚合平台 |

### Storage

| Type | 說明 |
|------|------|
| Memory | 記憶體儲存 |
| File | 檔案儲存 |
| SQLite | SQLite 資料庫（預設） |

### Channels

| Channel | 說明 |
|---------|------|
| Console | 終端機介面 |
| Telegram | Telegram Bot |

### Tools

| Tool | 說明 |
|------|------|
| ReadFile | 讀取檔案 |
| WriteFile | 寫入檔案 |
| EditFile | 編輯檔案 |
| ListDir | 列出目錄 |
| Exec | 執行 Shell 命令 |
| WebSearch | 網頁搜尋（Brave API） |
| WebFetch | 抓取網頁內容 |
| SaveMemory | 儲存長期記憶 |

## 配置選項

### LLM 設定

```json
{
  "llm": {
    "providers": {
      "openrouter": {
        "api_key": "",
        "model": "",
        "base_url": "https://openrouter.ai/api/v1",
        "enabled": false
      }
    },
    "default": "openrouter",
    "temperature": 0.7,
    "max_tokens": 8192
  }
}
```

### 記憶設定

```json
{
  "memory": {
    "max_history": 50,
    "threshold": 30
  }
}
```

- `max_history`: 對話歷史最大訊息數
- `threshold`: 觸發記憶 consolidation 的訊息數

### 日誌設定

```json
{
  "log": {
    "enabled": true,
    "retention_days": 365,
    "level": "INFO",
    "log_system_prompt": true,
    "log_system_prompt_lines": 0
  }
}
```

## 依賴

```txt
openai>=1.0.0
python-dotenv>=1.0.0
python-daemon>=3.0.0
aiohttp>=3.0.0
python-telegram-bot>=20.0
loguru>=0.7.0
```

## 開發

```bash
# 安裝開發依賴
pip install -e ".[dev]"

# 執行測試
pytest
```

## 文件

- [FLOW.md](FLOW.md) - 完整架構與流程圖
- [AGENTS.md](src/minibot/templates/AGENTS.md) - Agent 使用指南
- [SOUL.md](src/minibot/templates/SOUL.md) - Agent 核心設定

## License

MIT
