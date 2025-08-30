# worker/celery_config.py
import os
from celery.schedules import crontab
from dotenv import load_dotenv
load_dotenv()

from celery import Celery
app = Celery(
    'worker',
    broker=os.getenv("REDIS_URL"),
    backend=os.getenv("REDIS_URL"),
    include=['worker.trainer'], 
)

# app.conf.update(
#     task_serializer='json',
#     result_serializer='json',
#     accept_content=['json'],
#     timezone='Asia/Singapore',
#     enable_utc=False,
#     result_expires=7200,
#     broker_pool_limit=3,
#     broker_transport_options={"max_connections": 6},
#     worker_concurrency=1,
# )


app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Lagos',
    enable_utc=True,
)

# # app.conf.beat_schedule = {
#     'run-chunk-predictions-twice-daily': {
#         'task': 'worker.trainer.run_all_chunks',
#         'schedule': crontab(minute=5, hour='1,12'),
#     },
# }
