import psutil, os
import sys
import logging

handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    format="%(levelname)s:%(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

def log_memory(message):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 ** 2)
    logger.info(f"{message}: {mem:.2f} MB")
