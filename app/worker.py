import os
from celery import Celery, states
from dataclasses import dataclass
from typing import ClassVar

celery_app = Celery(
    os.getenv("CELERY_APP_NAME"),
    broker=f"amqp://{os.getenv('RABBITMQ_USERNAME')}:"
    + f"{os.getenv('RABBITMQ_PASSWORD')}@"
    + f"{os.getenv('RABBITMQ_HOSTNAME')}:"
    + f"{os.getenv('RABBITMQ_NODE_PORT_NUMBER')}//",
    backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@"
    + f"{os.getenv('REDIS_HOSTNAME')}:6379/0",
)

celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_track_started = True
celery_app.conf.update(result_extended=True)


@dataclass(frozen=True)
class TaskItem:
    id: str
    kwargs: dict

    @property
    def state(self):
        return TaskState(celery_app.AsyncResult(self.id).state)


@dataclass(frozen=True)
class TaskState:
    name: str
    icon_mapping: ClassVar[dict] = {
        states.SUCCESS: "checkmark",
        states.STARTED: "history",
        states.PENDING: "hourglass",
        states.FAILURE: "times",
    }
    state_class_mapping: ClassVar[dict] = {
        states.SUCCESS: "positive",
        states.STARTED: "warning",
        states.PENDING: "warning",
        states.FAILURE: "error",
    }

    @property
    def icon(self):
        return self.icon_mapping[self.name]

    @property
    def state_class(self):
        return self.state_class_mapping[self.name]
