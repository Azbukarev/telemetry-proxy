import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

try:
    from telemetree import Telemetree  # офиц. SDK
    SDK_AVAILABLE = True
except Exception:
    SDK_AVAILABLE = False
    import httpx

TELEMETREE_PROJECT_ID = os.getenv("TELEMETREE_PROJECT_ID", "")
TELEMETREE_API_KEY    = os.getenv("TELEMETREE_API_KEY", "")
TELEMETREE_BASE_URL   = os.getenv("TELEMETREE_BASE_URL", "").strip()

if not TELEMETREE_PROJECT_ID or not TELEMETREE_API_KEY:
    raise RuntimeError("Missing TELEMETREE_PROJECT_ID or TELEMETREE_API_KEY")

app = FastAPI(title="telemetry-proxy")

sdk = None
if SDK_AVAILABLE:
    try:
        sdk = Telemetree(project_id=TELEMETREE_PROJECT_ID, api_key=TELEMETREE_API_KEY)
    except Exception:
        SDK_AVAILABLE = False

@app.get("/")
def root():
    return {"ok": True, "sdk": SDK_AVAILABLE}

@app.post("/track")
async def track(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Bad JSON")

    event = payload.get("event")
    telegram_id = payload.get("telegramId")
    props = payload.get("props", {})

    if not event or not telegram_id:
        raise HTTPException(400, "Need 'event' and 'telegramId'")

    if SDK_AVAILABLE and sdk is not None:
        try:
            sdk.track(event=event, telegram_id=str(telegram_id), **props)
            return {"ok": True}
        except Exception:
            pass

    base = TELEMETREE_BASE_URL or "https://ingest.telemetree.io"
    url = base.rstrip("/") + "/collect"
    body = {"event": event, "telegramId": telegram_id, "props": props}

    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-Project-ID": TELEMETREE_PROJECT_ID,
                    "X-Api-Key": TELEMETREE_API_KEY,
                },
                json=body,
            )
            return {"ok": res.status_code == 200, "status": res.status_code}
    except Exception as e:
        return {"ok": False, "error": str(e)}
