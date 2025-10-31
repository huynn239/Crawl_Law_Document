import sys
from loguru import logger

# Configure logger once for entire application
logger.remove()  # Remove default handler
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    enqueue=False,
    colorize=False
)
