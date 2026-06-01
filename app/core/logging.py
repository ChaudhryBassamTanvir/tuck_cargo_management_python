import sys
from loguru import logger

def setup_logging():
    logger.remove()
    logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO", serialize=False)
    logger.add("logs/app.log", rotation="10 MB", retention="7 days", level="INFO")
    return logger