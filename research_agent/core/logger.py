# core/logger.py

import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_log_file = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(_log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
# 외부 라이브러리 로그 억제
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
