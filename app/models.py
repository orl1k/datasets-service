from pydantic import BaseModel, validator
from fastapi import Form
import pathlib
import inspect
from typing import Type
import datetime


def as_form(cls: Type[BaseModel]):
    """
    Adds an as_form class method to decorated models. The as_form class method
    can be used with FastAPI endpoints
    https://github.com/tiangolo/fastapi/issues/2387
    """
    new_params = [
        inspect.Parameter(
            field.alias,
            inspect.Parameter.POSITIONAL_ONLY,
            default=(Form(field.default) if not field.required else Form(...)),
        )
        for field in cls.__fields__.values()
    ]

    async def _as_form(**data):
        return cls(**data)

    sig = inspect.signature(_as_form)
    sig = sig.replace(parameters=new_params)
    _as_form.__signature__ = sig
    setattr(cls, "as_form", _as_form)
    return cls


bool_handler = {}


@as_form
class Args(BaseModel):
    dataset_date: datetime.date
    rasters_path: pathlib.Path
    datasets_path: pathlib.Path
    icemaps_path: pathlib.Path
    land_path: pathlib.Path
    age: bool = True
    concentrat: bool = True
    age_group: bool = True
    simple: bool = True
    advanced: bool = True
    task_priority: int = 5

    class Config:
        json_encoders = {
            datetime.date: lambda x: datetime.datetime.strptime(
                str(x), "%Y-%m-%d"
            ).strftime("%Y%m%d"),
        }
