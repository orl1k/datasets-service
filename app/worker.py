from celery import Celery, states
from pydantic import BaseModel
from typing import ClassVar
from config import Settings

settings = Settings()
celery_app = Celery(
    settings.celery_app_name,
    broker=f"amqp://{settings.rabbitmq_username}:"
    + f"{settings.rabbitmq_password}@"
    + f"{settings.rabbitmq_hostname}:"
    + f"{settings.rabbitmq_node_port_number}//",
    backend=f"redis://:{settings.redis_password}@"
    + f"{settings.redis_hostname}:6379/0",
)

celery_app.conf.task_queue_max_priority = 10
celery_app.conf.task_default_priority = 5
celery_app.conf.worker_prefetch_multiplier = 1
celery_app.conf.task_track_started = True
celery_app.conf.update(result_extended=True)


class TaskItem(BaseModel):
    name: str
    id: str
    kwargs: dict

    @property
    def state(self):
        return TaskState(name=celery_app.AsyncResult(self.id).state)

    class Config:
        frozen = True


class TaskState(BaseModel):
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

    class Config:
        frozen = True
