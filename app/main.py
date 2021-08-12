from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from worker import celery_app, TaskItem
from models import ScriptArgs
import config

from typing import Deque
from collections import deque
from functools import lru_cache
import pickle
import os

app = FastAPI()


@lru_cache()
def get_settings():
    return config.Settings()


task_queue_web: Deque = deque(maxlen=10)  # Очередь для мониторинга в вебе
task_queue_web_file = "task_queue_web.pickle"
if os.path.exists(task_queue_web_file):
    with open(task_queue_web_file, "rb") as f:
        task_queue = pickle.load(f)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request, "tasks": task_queue_web}
    )


@app.post("/script", status_code=201, response_model=TaskItem)
async def handle_args(
    request: Request,
    args: ScriptArgs = Depends(ScriptArgs.as_form),
) -> TaskItem:
    """
    Выберите аргументы скрипта сборки датасета:
    - **dataset_date**: дата, за которую будет собран датасет
    - **rasters_path**: директория, содержащая снимки
    - **datasets_path**: директория с датасетами
    - **icemaps_path**: директория с датасетами
    - **land_path**: путь к шейпу с землей
    - **age, concentrat, age_group**: характеристики льда, которые будут добавлены в датасет
    - **simple**: добавляемые текстурные характеристики из группы simple
    - **advanced**: добавляемые текстурные характеристики из группы advanced
    """
    try:
        args_dict = args.dict()
        task = celery_app.send_task(
            "run_script",
            kwargs=args_dict,
            priority=args.task_priority,
        )
    except Exception:
        print('Ошибка при отправке задачи')
        
    try:
        task_item = TaskItem(id=task.id, kwargs=args_dict)
        task_queue_web.appendleft(task_item)
    except Exception:
        print('Ошибка очереди веб-интерфейса')
        
    print("-" * 100)
    print(task_item)
    print("-" * 100)

    return task_item


@app.get("/flower", status_code=301)
def flower_redirect(
    request: Request, settings: config.Settings = Depends(get_settings)
):
    redirect_url = str(request.base_url)
    redirect_url = redirect_url.replace(
        str(request.base_url.port), settings.flower_port
    )
    return RedirectResponse(redirect_url)


@app.get("/healthcheck", status_code=200)
def health_check() -> JSONResponse:
    return JSONResponse({"healthcheck": "OK"})


@app.on_event("shutdown")
def shutdown_event():
    with open(task_queue_web_file, "wb") as f:
        pickle.dump(task_queue_web, f)
