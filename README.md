# mini-bot 🤖

超輕量個人 AI 助理框架

## 特色

- **極簡核心**：模組化設計，易於擴充
- **多 LLM 支援**：OpenAI、MiniMax、OpenRouter 透過統一介面
- **多對話支援**：每個聊天室有獨立的對話歷史與記憶
- **非同步處理**：訊息佇列、背景處理
- **工具呼叫**：檔案操作、網頁搜尋、Shell 命令執行
- **長期記憶**：支援記憶儲存與檢索

## 架構

```
src/minibot/
├── agent/              # Agent 核心（AgentLoop）
├── llms/               # LLM 實作（可替換）
│   ├── base.py        # LLMProvider 介面
│   ├── openai.py      # OpenAI
│   ├── minimax.py     # MiniMax
│   └── openrouter.py  # OpenRouter
├── channels/           # 訊息來源（可擴充）
│   └── telegram.py    # Telegram Adapter
├── bus/                # 訊息匯流排
│   ├── message.py     # 訊息結構
│   ├── message_queue.py
│   └── events.py
├── storage/            # 儲存提供者
│   ├── base.py        # StorageProvider 介面
│   ├── memory.py      # 記憶體實作
│   └── sqlite.py      # SQLite 實作
├── context/            # Prompt 上下文建構
│   ├── builder.py     # ContextBuilder 介面
│   ├── file_builder.py
│   └── workspace.py
├── tools/              # 工具實作
│   ├── filesystem.py  # 檔案操作
│   ├── shell.py       # Shell 命令
│   ├── web_search.py  # 網頁搜尋
│   └── web_fetch.py   # 網頁抓取
├── skills/             # 技能定義
│   ├── memory/        # 記憶技能
│   └── coding/        # 編碼技能
├── config/             # 設定管理
│   └── schema.py      # Pydantic Schema
├── templates/          # System Prompt 範本
└── main.py            # 入口點
```

## 安裝

```bash
# Clone 後安裝
cd mini-bot
pip install -e .

# 或只安裝依賴
pip install -r requirements.txt
```

## 快速開始

### 1. 設定配置檔

首次執行會自動建立配置檔於 `~/.minibot/minibot.json`

```bash
# 編輯配置檔，填入 API Key
# 位置：~/.minibot/minibot.json
```

配置範例：

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
    "default": "openrouter"
  },
  "channels": {
    "console": {
      "enabled": true
    }
  }
}
```

### 2. 執行（Console 模式）

```bash
python -m minibot.main
```

### 3. 輸入格式

```
你好              → 發送到 default 對話
@123 你好        → 發送到 chat_id=123
@123 /reset      → 清除 chat_id=123 的歷史
/reset           → 清除所有歷史
/exit            → 離開
```

## 執行模式

```bash
# 前景模式（Console）
python -m minibot.main foreground

# 背景模式
python -m minibot.main start
```

## 使用方式

### 基本使用

```python
from minibot.agent import AgentLoop, AgentConfig
from minibot.llms import OpenAILLM
from minibot.storage import MemoryStorage
from minibot.context import FileContextBuilder
from minibot.message import UserMessage

# 1. 建立 LLM
llm = OpenAILLM(
    api_key="sk-xxx",
    base_url=None,
    default_model="gpt-4o-mini"
)

# 2. 建立 Storage
storage = MemoryStorage()

# 3. 建立 ContextBuilder
context_builder = FileContextBuilder()

# 4. 建立 Agent
config = AgentConfig(system_prompt="你是個簡潔的助理。")
agent = AgentLoop(config, llm, storage, context_builder)

# 5. 使用
user_msg = UserMessage(text="你好", chat_id="123")
response = await agent.process(user_msg)
print(response.text)
```

### 使用 Telegram

```python
from minibot.agent import AgentLoop, AgentConfig
from minibot.llms import OpenAILLM
from minibot.channels.telegram import TelegramAdapter

# 建立 Agent
llm = OpenAILLM(api_key="your-key")
agent = AgentLoop(AgentConfig(system_prompt="你是個助理。"), llm)

# 建立 Telegram Adapter
telegram = TelegramAdapter(bot_token="your-telegram-token")

# 處理訊息
async def handle(adapter, raw_update, user_msg):
    response = await agent.process(user_msg)
    await adapter.send(response)

# 啟動
asyncio.run(telegram.run(handle))
```

## 可用工具

| 工具 | 說明 |
|------|------|
| `filesystem` | 讀取、寫入、編輯檔案，列出目錄 |
| `shell` | 執行 Shell 命令 |
| `web_search` | 網頁搜尋（需 Brave API Key） |
| `web_fetch` | 抓取網頁內容 |
| `memory` | 儲存長期記憶 |

## 配置選項

### LLM 提供者

| 提供者 | 說明 |
|--------|------|
| `openrouter` | OpenRouter（支援多種模型） |
| `openai` | OpenAI API |
| `minimax` | MiniMax AI |

### 儲存類型

| 類型 | 說明 |
|------|------|
| `memory` | 記憶體儲存（揮發性） |
| `file` | 檔案儲存 |
| `sqlite` | SQLite 資料庫（預設） |

### 頻道

| 頻道 | 說明 |
|------|------|
| `console` | 終端機介面（預設啟用） |
| `telegram` | Telegram Bot |

## 依賴

```txt
openai>=1.0.0
python-dotenv>=1.0.0
python-daemon>=3.0.0
aiohttp>=3.0.0
python-telegram-bot>=20.0
loguru>=0.7.0
```

## 文件

- [FLOW.md](FLOW.md) - 完整架構與流程圖
- [AGENTS.md](src/minibot/templates/AGENTS.md) - Agent 使用指南
- [SOUL.md](src/minibot/templates/SOUL.md) - Agent 核心設定

## License

MIT
