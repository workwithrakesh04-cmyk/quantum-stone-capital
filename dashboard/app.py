"""
FastAPI dashboard backend.
"""
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from dashboard.state import get_state

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(title="Quantum Stone Capital", version="0.2.0")

STATIC_DIR = BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
async def startup():
    state = get_state()
    try:
        state.start()
    except Exception as e:
        print("state.start() failed:", e)


@app.on_event("shutdown")
async def shutdown():
    try:
        get_state().stop()
    except Exception:
        pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # New-style TemplateResponse (Starlette >= 0.29)
    return TEMPLATES.TemplateResponse(request=request, name="index.html", context={})


@app.get("/api/state")
async def api_state():
    return JSONResponse(get_state().snapshot())


@app.get("/api/prices")
async def api_prices():
    return JSONResponse(get_state().snapshot().get("prices", {}))


@app.get("/api/accounts")
async def api_accounts():
    return JSONResponse(get_state().snapshot().get("accounts", {}))


@app.get("/api/decisions")
async def api_decisions():
    return JSONResponse(get_state().snapshot().get("recent_decisions", []))


@app.get("/api/health")
async def api_health():
    state = get_state()
    return JSONResponse({
        "status": "ok",
        "started_at": state.started_at,
        "feeds": state.feeds.health(),
        "accounts": list(state.pool.broker.accounts.keys()),
    })


@app.post("/api/tick")
async def api_tick():
    prices = get_state().pool.tick()
    return JSONResponse({"ok": True, "prices": prices})


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            snapshot = get_state().snapshot()
            await websocket.send_text(json.dumps(snapshot))
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        return
    except Exception as e:
        print("WS error:", e)
        try:
            await websocket.close()
        except Exception:
            pass
