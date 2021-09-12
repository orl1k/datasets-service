from pydantic import BaseModel, validator
from fastapi import Form
from typing import Callable, Type, Union
import datetime
import inspect


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


def fixed_length_normalizer(max_length: int) -> Callable:
    def normalize(arr: Union[list[str], str]) -> list[str]:
        if not arr:
            return []
        if isinstance(arr, list):
            return arr
        # Если arr типа str, то ожидается список int значений, разделенных запятой
        parts = arr.split(",")
        # Прим: При запросе с веб страницы значения закодированы по прицнипу one-hot-encode
        from_web_page = (len(parts) >= max_length) and (set(parts).issubset({"0", "1"}))
        if from_web_page:
            return [str(i) for i, val in enumerate(parts) if int(val)]
        return parts

    return normalize


@as_form
class SarScriptArgs(BaseModel):
    dataset_date: datetime.date
    age: bool = True
    concentrat: bool = True
    age_group: bool = True
    simple: Union[list[str], str] = []
    advanced: Union[list[str], str] = []
    task_priority: int = 5

    # Количество харалик характеристик типа Simple = 8
    _simple = validator("simple", allow_reuse=True, pre=True)(
        fixed_length_normalizer(max_length=8)
    )
    # Количество харалик характеристик типа Advanced = 11
    _advanced = validator("advanced", allow_reuse=True, pre=True)(
        fixed_length_normalizer(max_length=11)
    )


@as_form
class WeatherScriptArgs(BaseModel):
    dataset_date: datetime.date
    task_priority: int = 5
