"""HTTP API for the app. Run: uvicorn hug_guardian.api:app --port 8000 --host 0.0.0.0"""

import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .agent import screen
from .harness import HarnessFormula
from .loop import diff
from .store import Store
from .tools import USERS

app = FastAPI(title="Hug Guardian")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
store = Store()


class BookingRequest(BaseModel):
    user_id: str
    location: str
    when: str
    duration_minutes: int = 30
    message: str = ""


def _harness(version: Optional[int] = None):
    h = store.get_harness(version) if version else store.active_harness()
    if not h:
        raise HTTPException(404, "No harness yet. Run scripts/loop.py first.")
    return h


@app.post("/screen")
def screen_booking(req: BookingRequest, version: Optional[int] = None):
    h = _harness(version)
    booking_id = f"b_{uuid.uuid4().hex[:6]}"
    decision, _ = screen(HarnessFormula(h), req.model_dump(), request_id=booking_id, store=store)
    out = {**decision.model_dump(), "harness_version": h["version"], "booking_id": booking_id}
    store.save_booking({"booking_id": booking_id, "request": req.model_dump(), **out})
    return out


@app.get("/users")
def users():
    return [{"id": uid, "name": u["name"],
             "label": f"{u['name']} ({u['completed_hugs']} hugs{', reported' if u['reports'] else ''}"
                      f"{', new' if u['account_age_days'] < 7 else ''})"}
            for uid, u in USERS.items()]


@app.get("/harness")
def harness():
    return _harness()


@app.get("/harness/versions")
def versions():
    return store.list_harnesses()


@app.get("/evals")
def evals():
    return [{k: v for k, v in e.items() if k not in ("failures", "holdout_failures")} for e in store.list_evals()]


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(Path(__file__).parent / "static" / "dashboard.html")


@app.get("/diff")
def get_diff(from_: int = Query(1, alias="from"), to: Optional[int] = None):
    # "from" is a Python keyword, so it is read through an alias.
    a = _harness(from_)
    b = _harness(to) if to else store.active_harness()
    return diff(a, b)
