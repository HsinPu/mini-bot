"""
minibot/utils/log.py - 日誌模組

功能：
- 每日輪轉日誌檔案
- 自動清理過期日誌（可設定保留天數）

日誌位置：~/.minibot/logs/minibot-YYYY-MM-DD.log
"""

from pathlib import Path
from loguru import logger

# 日誌目錄
LOG_DIR = Path.home() / ".minibot" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def setup_log(config=None):
    """
    初始化日誌
    
    參數：
        config: LogConfig 物件，若為 None 则使用預設值
    """
    # 取得設定值
    if config:
        retention = f"{config.retention_days} days"
        level = config.level
    else:
        retention = "365 days"
        level = "INFO"
    
    # 設定日誌
    logger.add(
        LOG_DIR / "minibot-{time:YYYY-MM-DD}.log",
        rotation="1 day",           # 每日新檔案
        retention=retention,        # 保留天數
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=level,
    )
    
    return logger


# 預設設定（未傳入 config 時使用）
setup_log()

__all__ = ["logger", "setup_log"]
