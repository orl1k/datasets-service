from pydantic import BaseModel


class ScriptArgs(BaseModel):
    date: int
    rasters_root: str
    ds_root: str
    icemaps_root: str
    land: str
    ice_params: str
    simple: str
    advanced: str

    class Config:
        schema_extra = {
            "example": {
                "date": 20200101,
                "rasters_root": "/mnt/Gold2/rasters",
                "ds_root": "/mnt/Gold1/datasets",
                "icemaps_root": "/mnt/Gold2/ice_maps/KAR",
                "land": "/mnt/Gold2/land/bigger/Shore_20191212.shp",
                "ice_params": "age concentrat age_group",
                "simple": "all",
                "advanced": "all",
            }
        }
