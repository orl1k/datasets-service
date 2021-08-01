import os
from celery import Celery, states
from collections import deque
from dataclasses import dataclass
from typing import ClassVar

celery_app = Celery(
    os.getenv("CELERY_APP_NAME"),
    broker=f"amqp://{os.getenv('RABBITMQ_USERNAME')}:{os.getenv('RABBITMQ_PASSWORD')}@rabbitmq:{os.getenv('RABBITMQ_NODE_PORT_NUMBER')}//",
    backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@redis:6379/0",
)

celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5
celery_app.conf.update(result_extended=True)


@dataclass(frozen=True)
class TaskItem:
    id: str
    kwargs: dict

    @property
    def state(self):
        return State(self.id)


class State:
    icon_mapping: ClassVar[dict] = {
        states.SUCCESS: "checkmark",
        states.PENDING: "history",
        states.FAILURE: "times",
    }
    state_class_mapping: ClassVar[dict] = {
        states.SUCCESS: "positive",
        states.PENDING: "warning",
        states.FAILURE: "error",
    }

    def __init__(self, task_id):
        self.__name = celery_app.AsyncResult(task_id).state

    @property
    def name(self):
        return self.__name

    @property
    def icon(self):
        return self.icon_mapping[self.__name]

    @property
    def state_class(self):
        return self.state_class_mapping[self.__name]