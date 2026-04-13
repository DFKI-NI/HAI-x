from ast import literal_eval

import numpy as np
import pathplanner
from fastapi import FastAPI
import json
from pydantic import BaseModel


class AoIs(BaseModel):
    vehicle_capacity: int
    duration: int
    aoi: dict

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/route/{areas}")
async def get_route(areas: str):
    json_dump = areas.replace("\'", "\"")
    inputdict = json.loads(json_dump)

    aois = inputdict['aois']
    vc = inputdict['vc']

    duration = inputdict['duration']

    if len(aois) > 0:
        paths = pathplanner.planning(aois, vc, duration)
        result = {"routes": paths}
    else:
        result = {"routes": []}

    #rDict = {"routes": {}}
    #for p in paths:
        #print(type(paths[p]))
        #rDict["routes"][p] = paths[p].tolist()

    return result

@app.post("/routePos")
async def get_routepos(areas: AoIs):
    aois = areas.aoi
    vc = areas.vehicle_capacity
    duration = areas.duration

    if len(aois) > 0:
        paths = pathplanner.planning(aois, vc, duration)
        result = {"routes": paths}
    else:
        result = {"routes": []}

    # rDict = {"routes": {}}
    # for p in paths:
    # print(type(paths[p]))
    # rDict["routes"][p] = paths[p].tolist()

    return result
