import os
from celery import Celery
from config import Settings
import ds_arrays

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


@celery_app.task(bind=True, name="run_script", acks_late=True)
def run_script(self, **kwargs):
    kwargs["ice_params"] = (
        "age " * kwargs["age"]
        + "concentrat " * kwargs["concentrat"]
        + "age_group" * kwargs["age_group"]
    )
    kwargs["simple"] = "all" * kwargs["simple"]
    kwargs["advanced"] = "all" * kwargs["advanced"]
    print("task_id: " + self.request.id)
    print(kwargs)

    ds_arrays.create_ds_arrays(
        kwargs["dataset_date"],
        kwargs["icemaps_path"],
        kwargs["rasters_path"],
        kwargs["datasets_path"],
        kwargs["land_path"],
        kwargs["ice_params"],
        simple_band_nums=ds_arrays.get_band_nums(kwargs["simple"]),
        advanced_band_nums=ds_arrays.get_band_nums(kwargs["advanced"]),
    )

    ds_arrays.create_weather_ds(
        kwargs["rasters_path"],
        kwargs["dataset_date"],
        kwargs["datasets_path"],
        ds_arrays.weather_params,
    )

    return True
