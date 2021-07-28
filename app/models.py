from pydantic import BaseModel
from fastapi import Form
import inspect
from typing import Type

def as_form(cls: Type[BaseModel]):
    """
    Adds an as_form class method to decorated models. The as_form class method
    can be used with FastAPI endpoints
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


@as_form
class Args(BaseModel):
    dataset_date: str
    rasters_path: str
    datasets_path: str
    icemaps_path: str
    land_path: str
    age: bool
    concentrat: bool
    age_group: bool
    simple: bool
    advanced: bool
