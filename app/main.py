from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from celery.result import AsyncResult
import celery.states as states
from worker import celery_app
from models import Args
import os
import redis

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/script", status_code=201)
async def handle_args(
    request: Request,
    args: Args = Depends(Args.as_form),
):
    print("-" * 100)
    print(jsonable_encoder(args))
    print("-" * 100)

    task = celery_app.send_task("run_script", kwargs=jsonable_encoder(args))
    response = f"<a href='{app.url_path_for('check_task', task_id=task.id)}'>Check status of {task.id} </a>"

    return JSONResponse({"task_id": task.id, "task_url": response})


@app.get("/check/{task_id}")
def check_task(task_id):
    res = celery_app.AsyncResult(task_id)
    return str(res.state) + " " + str(res.result)
    # if res.state == states.PENDING:
    #     return res.state
    # else:
    #     return str(res.result)


@app.get("/health_check")
def health_check():
    return JSONResponse("OK")
