from typing import Union

from fastapi import FastAPI
from pydantic import BaseModel

from aviation_hackathon_sf import performer
from aviation_hackathon_sf.checklist_api import create_checklist_endpoints

app = FastAPI(title="Aviation Hackathon SF - Co-Pilot Assistant API")

# Register checklist endpoints
create_checklist_endpoints(app)


class Item(BaseModel):
    name: str
    price: float
    is_offer: Union[bool, None] = None


@app.get("/")
def read_root():
    return {
        "Hello": "World",
        "something": performer.perform_something(),
        "api": "Aviation Hackathon SF - Co-Pilot Assistant",
    }


@app.get("/ping")
def ping():
    return "pong"


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
