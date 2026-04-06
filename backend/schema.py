from fastapi import FASTAPI
from pydantic import Basemodel

app =FASTAPI()

class Item(BaseModel):
    name: str
    