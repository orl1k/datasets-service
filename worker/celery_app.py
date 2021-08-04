import os
from celery import Celery
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


@celery_app.task(name="run_script", acks_late=True)
def run_script(**kwargs):
    kwargs["ice_params"] = (
        "age " * kwargs["age"]
        + "concentrat " * kwargs["concentrat"]
        + "age_group" * kwargs["age_group"]
    )
    del kwargs["age"], kwargs["concentrat"], kwargs["age_group"]

    kwargs["simple"] = "all" * kwargs["simple"]
    kwargs["advanced"] = "all" * kwargs["advanced"]

    # Parse dict -> cli command
    script_string = "python test.py" + "".join(
        [f" --{x} {str(y)}" if y else "" for x, y in kwargs.items()]
    )

    print(f"{script_string=}")
    os.system(script_string)

    return True
