import psutil, os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_memory(message):
    process = psutil.Process(os.getpid())
    mem = process.memory_info().rss / (1024 ** 2)
    logger.info(f"{message}: {mem:.2f} MB")
