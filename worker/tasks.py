import os
import time
from celery import Celery
from datetime import datetime


celery_app = Celery(
    os.getenv("CELERY_APP_NAME"),
    broker=f"amqp://{os.getenv('RABBITMQ_USERNAME')}:{os.getenv('RABBITMQ_PASSWORD')}@rabbitmq:{os.getenv('RABBITMQ_NODE_PORT_NUMBER')}//",
    backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@redis:6379/0",
)

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
        [f" --{x} {str(y)}" for x, y in kwargs.items()]
    )

    os.system(script_string)

    return True
