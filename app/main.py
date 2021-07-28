from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.encoders import jsonable_encoder
from celery.result import AsyncResult
from worker import run_script
from models import Args
import os


app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})


# @app.post("/", status_code=201)
# async def handle_args(
#     request: Request,
#     args: Args = Depends(Args.as_form),
# ):

#     task = run_script.delay(jsonable_encoder(args))

#     print("-" * 100)
#     print(task)
#     print("-" * 100)

#     # return JSONResponse({"task_id": task.id})
#     return templates.TemplateResponse("home.html", {"request": request})


@app.post("/script", status_code=201)
async def handle_args(
    request: Request,
    args: Args = Depends(Args.as_form),
):
    task = run_script.delay(jsonable_encoder(args))

    print("-" * 100)
    print(task)
    print("-" * 100)

    return JSONResponse({"task_id": task.id})


# @app.get("/tasks/{task_id}")
# def get_status(task_id):
#     task_result = AsyncResult(task_id)
#     result = {
#         "task_id": task_id,
#         "task_status": task_result.status,
#         "task_result": task_result.result,
#     }
#     return JSONResponse(result)


# if __name__ == "__main__":
#     uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
