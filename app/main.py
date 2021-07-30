from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from celery.result import AsyncResult

from worker import celery_app, get_tasks
from models import Args

from collections import deque
import pickle
import os

app = FastAPI()

task_queue = deque(maxlen=10)
task_queue_file = "task_queue.pickle"
if os.path.exists(task_queue_file):
    with open(task_queue_file, "rb") as f:
        task_queue = pickle.load(f)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request) -> templates.TemplateResponse:
    return templates.TemplateResponse(
        "home.html", {"request": request, "tasks": get_tasks(task_queue)}
    )


@app.post("/script", status_code=201)
async def handle_args(
    request: Request,
    args: Args = Depends(Args.as_form),
) -> JSONResponse:

    json_kwargs = jsonable_encoder(args)

    print("-" * 100)
    print(json_kwargs)
    print("-" * 100)

    task = celery_app.send_task(
        "run_script",
        kwargs=json_kwargs,
        priority=args.task_priority,
    )
    task_queue.append((task.id, json_kwargs))
    response = f"<a href='{app.url_path_for('check_task', task_id=task.id)}'>Check status of {task.id} </a>"

    return JSONResponse({"task_id": task.id, "task_url": response})


@app.get("/check/{task_id}")
def check_task(task_id):
    res = celery_app.AsyncResult(task_id)
    return JSONResponse(str(res.state) + " " + str(res.result))


@app.get("/health_check")
def health_check():
    return JSONResponse("OK")


# @app.on_event("startup")
# async def startup_event():
#     with open(task_queue_file, "rb") as f:
#         task_queue = pickle.load(f)


@app.on_event("shutdown")
def shutdown_event():
    with open(task_queue_file, "wb") as f:
        pickle.dump(task_queue, f)
