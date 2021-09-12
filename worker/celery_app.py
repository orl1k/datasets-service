import os
from celery import Celery
from pydantic import BaseModel
from pathlib import Path

import ds_arrays
import multisource
from config import Settings


class BindMounts(BaseModel):
    # /home/user/worker part is taken from dockerfile
    # Sentinel SAR image (raster) sources (dirs)
    rasters_volume: Path = "/home/user/worker/volumes/sar"
    rasters: Path = "/home/user/worker/sar"
    # Ice map sources (dirs)
    icemaps_volume: Path = "/home/user/worker/volumes/icemap"
    icemaps: Path = "/home/user/worker/icemap"
    # Land shp file source (dir)
    land: Path = "/home/user/worker/land"
    # Output directory that will contain final datasets
    output: Path = "/home/user/worker/output"


mounts = BindMounts()
settings = Settings()


def get_dg_app():
    # Create MultiDataGatherer app to collect and sync
    # required input data from multiple sources
    dg_app = multisource.MultiDataGatherer()

    rasters_dg = multisource.DataGatherer(
        mounts.rasters_volume,
        mounts.rasters,
        link_folders_only=settings.link_only_folders,
    )
    dg_app.add_app("rasters", rasters_dg)

    icemaps_dg = multisource.DataGatherer(
        mounts.icemaps_volume,
        mounts.icemaps,
        link_folders_only=settings.link_only_folders,
    )
    dg_app.add_app("icemaps", icemaps_dg)

    return dg_app


dg_app = get_dg_app()

# Main Celery app
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


@celery_app.task(bind=True, name="run_sar_script", acks_late=True)
def run_script(self, **kwargs):
    dg_app.sync()  # sync input all input sources fist

    kwargs["ice_params"] = (
        "age " * kwargs["age"]
        + "concentrat " * kwargs["concentrat"]
        + "age_group" * kwargs["age_group"]
    )
    print("task_id: " + self.request.id)
    print(kwargs)

    ds_arrays.create_ds_arrays(
        kwargs["dataset_date"],
        mounts.icemaps,
        mounts.rasters,
        mounts.output,
        mounts.land,
        kwargs["ice_params"],
        simple_band_nums=ds_arrays.get_band_nums(kwargs["simple"]),
        advanced_band_nums=ds_arrays.get_band_nums(kwargs["advanced"]),
    )

    return True


@celery_app.task(bind=True, name="run_weather_script", acks_late=True)
def run_weather_script(self, **kwargs):
    dg_app.rasters.sync()  # sync input raster sources fist

    print("task_id: " + self.request.id)
    print(kwargs)

    ds_arrays.create_weather_ds(
        mounts.rasters,
        kwargs["dataset_date"],
        mounts.output,
        ds_arrays.weather_params,
    )

    return True
