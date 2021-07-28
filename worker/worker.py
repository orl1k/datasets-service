import time
import os
from datetime import datetime
from celery import Celery

# celery = Celery(__name__, broker="amqp://rabbitmq:5672", backend="redis://redis:6379/0")
celery = Celery(
    __name__,
    broker=f"amqp://{os.getenv('RABBITMQ_USER')}:{os.getenv('RABBITMQ_PASS')}@rabbitmq:{os.getenv('RABBITMQ_PORT')}//",
    backend=f"redis://:{os.getenv('REDIS_PASSWORD')}@redis:{os.getenv('REDIS_PORT_NUMBER')}/0",
)

celery.conf.update(task_track_started=True)


@celery.task(name="run_script", acks_late=True)
def run_script(args):
    date = (
        datetime.strptime(args["dataset_date"], "%B %d, %Y")
        .date()
        .strftime("%Y%m%d")
    )
    rasters_root = args["rasters_path"]
    ds_root = args["datasets_path"]
    icemaps_root = args["icemaps_path"]
    land = args["land_path"]

    ice_list = []
    if args["age"]:
        ice_list.append("age")
    if args["concentrat"]:
        ice_list.append("concentrat")
    if args["age_group"]:
        ice_list.append("age_group")
    ice_params = " ".join(ice_list)

    simple = "all" if args["simple"] else ""
    advanced = "all" if args["advanced"] else ""

    script_string = (
        "python test.py "
        f"--date {date} "
        f"--rasters_root {rasters_root} "
        f"--ds_root {ds_root} "
        f"--icemaps_root {icemaps_root} "
        f"--land {land} "
        f"--ice_params {ice_params} "
        f"--simple {simple} "
        f"--advanced {advanced} "
    )
    os.system(script_string)
    return True
