# worker/celery_app.py
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from worker.celery_config import app  # this brings in the Celery app
from worker import trainer  # this is required to ensure task is loaded

# Optional: use autodiscover_tasks if your project structure is more complex
# app.autodiscover_tasks(['worker'])

# app.conf.task_default_queue = 'default'
