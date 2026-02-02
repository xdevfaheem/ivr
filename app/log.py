import sys
from pathlib import Path
import os
from loguru import logger

def setup():
    """Setup Logger"""

    log_dir = Path(os.getenv("LOG_DIR", "logs"))
    log_dir.mkdir(exist_ok=True)

    logger.remove()

    # Console output
    logger.add(
        sys.stdout,
        level="INFO",
        enqueue=True,
        format="<green>{time:DD-MM-YYYY HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
        "- <level>{message}</level>",
    )

    # File logging
    logger.add(
        log_dir / "app.log",
        level="DEBUG",
        enqueue=True,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        format="{time:DD-MM-YYYY HH:mm:ss} | {level} | {message}",
    )
