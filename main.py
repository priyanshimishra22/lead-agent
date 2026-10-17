from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field

import services
from db import init_db

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()  # create tables and load sample data if the database is empty
    yield


app = FastAPI(title="Lead Follow-up Agent", lifespan=lifespan)


class NewLead(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    company: str = Field(min_length=1, max_length=100)
    phone: str = Field(default="", max_length=30)
    source: str = Field(default="Other", max_length=50)
    rep: str = Field(min_length=1, max_length=50)


class NewMessage(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    sender: Literal["buyer", "rep"]
    text: str = Field(min_length=1, max_length=2000)


class DraftBody(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    draft: str = Field(min_length=1, max_length=2000)


def _detail_or_404(lead_id: int):
    detail = services.get_lead_detail(lead_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return detail


@app.get("/api/reps")
def get_reps():
    return services.list_reps()


@app.get("/api/leads")
def get_leads(rep: Optional[str] = None):
    return services.list_leads(rep)


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: int):
    return _detail_or_404(lead_id)


@app.post("/api/leads", status_code=201)
def create_lead(body: NewLead):
    lead_id = services.create_lead(body.name, body.company, body.phone, body.source, body.rep)
    return _detail_or_404(lead_id)


@app.post("/api/leads/{lead_id}/messages")
def add_message(lead_id: int, body: NewMessage):
    if services.add_message(lead_id, body.sender, body.text) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _detail_or_404(lead_id)


@app.put("/api/leads/{lead_id}/draft")
def save_draft(lead_id: int, body: DraftBody):
    if services.update_draft(lead_id, body.draft) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _detail_or_404(lead_id)


@app.post("/api/leads/{lead_id}/sent")
def mark_sent(lead_id: int, body: DraftBody):
    if services.mark_sent(lead_id, body.draft) is None:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _detail_or_404(lead_id)


@app.get("/")
def home():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "API is running. Open /docs to try it."}
