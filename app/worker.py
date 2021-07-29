import os
from celery import Celery


celery_app = Celery(
    os.getenv("CELERY_APP_NAME"),
    broker=f"amqp://{os.getenv('RABBITMQ_USERNAME')}:{os.getenv('RABBITMQ_PASSWORD')}@rabbitmq:{os.getenv('RABBITMQ_NODE_PORT_NUMBER')}//",
    backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@redis:6379/0",
)
