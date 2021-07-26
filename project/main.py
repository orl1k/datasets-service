from celery.result import AsyncResult
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import FastAPI, Request, Depends, BackgroundTasks, Form
from models import ScriptArgs
import os
from worker import create_task


app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def home(
    request: Request,
):
    return templates.TemplateResponse("home.html", {"request": request})


@app.post("/")
async def handle_args(request: Request):
    script_args = await request.form()
    script_args_parsed = parse_args(script_args)
    start_script(script_args_parsed)
    return templates.TemplateResponse("home.html", {"request": request})


async def start_script(args: ScriptArgs):
    script_string = (
        "python test.py "
        f"--date {args.date} "
        f"--rasters_root {args.rasters_root} "
        f"--ds_root {args.ds_root} "
        f"--icemaps_root {args.icemaps_root} "
        f"--land {args.land} "
        f"--ice_params {args.ice_params} "
        f"--simple {args.simple} "
        f"--advanced {args.advanced}"
    )

    os.system(script_string)
    return


def parse_args(args):
    from datetime import date, datetime, time, timedelta

    date = (
        datetime.strptime(args["dataset_date"], "%B %d, %Y")
        .date()
        .strftime("%Y%m%d")
    )
    rasters_root = args["rasters_path"]
    ds_root = args["datasets_path"]
    icemaps_root = args["icemaps_path"]
    land = args["land_path"]

    ice_list = []
    if args["age"] == "on":
        ice_list.append("age")
    if args["concentrat"] == "on":
        ice_list.append("concentrat")
    if args["age_group"] == "on":
        ice_list.append("age_group")
    ice_params = " ".join(ice_list)

    simple = "all" if args["simple"] == "on" else ""
    advanced = "all" if args["advanced"] == "on" else ""

    script_args = ScriptArgs(
        date=date,
        rasters_root=rasters_root,
        ds_root=ds_root,
        icemaps_root=icemaps_root,
        land=land,
        ice_params=ice_params,
        simple=simple,
        advanced=advanced,
    )
    return script_args


# if __name__ == "__main__":
#     uvicorn.run("main:app", port=8000, host="0.0.0.0", reload=True)
