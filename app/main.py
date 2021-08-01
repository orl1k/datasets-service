from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from celery.result import AsyncResult

from worker import celery_app, TaskItem
from models import ScriptArgs

from collections import deque
import pickle
import os

app = FastAPI()

task_queue = deque(maxlen=10)
task_queue_file = "task_queue.pickle"
# if os.path.exists(task_queue_file):
#     with open(task_queue_file, "rb") as f:
#         task_queue = pickle.load(f)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request) -> templates.TemplateResponse:
    return templates.TemplateResponse(
        "home.html", {"request": request, "tasks": task_queue}
    )


@app.post("/script", status_code=201)
async def handle_args(
    request: Request,
    args: ScriptArgs = Depends(ScriptArgs.as_form),
    response_model=TaskItem,
) -> JSONResponse:

    json_kwargs = jsonable_encoder(args)
    task = celery_app.send_task(
        "run_script",
        kwargs=json_kwargs,
        priority=args.task_priority,
    )
    task_item = TaskItem(task.id, json_kwargs)

    print("-" * 100)
    print(task_item.kwargs)
    print("-" * 100)

    task_queue.appendleft(task_item)

    return task_item


@app.get("/flower")
def flower_redirect(request: Request):
    redirect_url = str(request.base_url)
    redirect_url = redirect_url.replace(
        str(request.base_url.port), os.getenv("FLOWER_PORT")
    )
    return RedirectResponse(redirect_url)


@app.get("/health_check")
def health_check():
    return JSONResponse({"healthcheck": "OK"})


# @app.on_event("startup")
# async def startup_event():
#     with open(task_queue_file, "rb") as f:
#         task_queue = pickle.load(f)


@app.on_event("shutdown")
def shutdown_event():
    with open(task_queue_file, "wb") as f:
        pickle.dump(task_queue, f)
