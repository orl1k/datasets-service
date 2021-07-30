import os
from celery import Celery, states
from collections import deque

check_icon = {
    states.SUCCESS: "checkmark",
    states.PENDING: "history",
}
check_class = {
    states.SUCCESS: "positive",
    states.PENDING: "warning",
}

celery_app = Celery(
    os.getenv("CELERY_APP_NAME"),
    broker=f"amqp://{os.getenv('RABBITMQ_USERNAME')}:{os.getenv('RABBITMQ_PASSWORD')}@rabbitmq:{os.getenv('RABBITMQ_NODE_PORT_NUMBER')}//",
    backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@redis:6379/0",
)

celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5
celery_app.conf.update(result_extended=True)


def get_tasks(task_queue: deque) -> list[dict]:
    tasks = []
    for task_id, kwargs in reversed(task_queue):
        res = celery_app.AsyncResult(task_id)
        tasks.append(
            {
                "task_id": task_id,
                "info": kwargs,
                "state": res.state,
                "class": check_class[res.state],
                "icon": check_icon[res.state],
            }
        )
    return tasks
