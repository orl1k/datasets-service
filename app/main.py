from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from celery.result import AsyncResult
from celery import states

from worker import celery_app
from models import Args

from collections import deque
import pickle
import os

app = FastAPI()

task_queue = deque(maxlen=10)
task_queue_file = "task_queue.pickle"
if os.path.exists(task_queue_file):
    with open("task_queue.pickle", "rb") as f:
        task_queue = pickle.load(f)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request, "tasks": get_tasks()}
    )


@app.post("/script", status_code=201)
async def handle_args(
    request: Request,
    args: Args = Depends(Args.as_form),
):

    print("-" * 100)
    print(jsonable_encoder(args))
    print("-" * 100)

    task = celery_app.send_task("run_script", kwargs=jsonable_encoder(args))
    task_queue.append(task.id)
    response = f"<a href='{app.url_path_for('check_task', task_id=task.id)}'>Check status of {task.id} </a>"

    return JSONResponse({"task_id": task.id, "task_url": response})


@app.get("/check/{task_id}")
def check_task(task_id):
    res = celery_app.AsyncResult(task_id)
    return str(res.state) + " " + str(res.result)


@app.get("/health_check")
def health_check():
    return JSONResponse("OK")


# @app.on_event("startup")
# async def startup_event():
#     with open("task_queue.pickle", "rb") as f:
#         task_queue = pickle.load(f)


@app.on_event("shutdown")
def shutdown_event():
    with open("task_queue.pickle", "wb") as f:
        pickle.dump(task_queue, f)


check_icon = {
    states.SUCCESS: "checkmark",
    states.PENDING: "history",
}
check_class = {
    states.SUCCESS: "positive",
    states.PENDING: "warning",
}


def get_tasks():
    tasks = []
    for task_id in reversed(task_queue):
        res = celery_app.AsyncResult(task_id)
        tasks.append(
            {
                "task_id": task_id,
                "info": res.kwargs,
                "state": res.state,
                "class": check_class[res.state],
                "icon": check_icon[res.state],
            }
        )
    return tasks
