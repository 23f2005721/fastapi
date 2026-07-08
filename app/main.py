import time
import uuid
import logging
from collections import defaultdict, deque

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

EMAIL = "23f2005721@ds.study.iitm.ac.in"
API_KEY = "ak_g9p1jlxvjoaqgpy9hcspmgtz"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

START = time.time()

logs = deque(maxlen=1000)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP Requests"
)

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = str(uuid.uuid4())

    http_requests_total.inc()

    entry = {
        "level": "INFO",
        "ts": time.time(),
        "path": request.url.path,
        "request_id": request_id,
    }

    logs.append(entry)

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.post("/analytics")
async def analytics(
    payload: dict,
    x_api_key: str | None = Header(default=None)
):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    events = payload.get("events", [])

    total_events = len(events)

    users = set()

    revenue = 0.0

    totals = defaultdict(float)

    for e in events:
        user = e["user"]
        amount = float(e["amount"])

        users.add(user)

        if amount > 0:
            revenue += amount
            totals[user] += amount

    top_user = ""

    if totals:
        top_user = max(totals, key=totals.get)

    return {
        "email": EMAIL,
        "total_events": total_events,
        "unique_users": len(users),
        "revenue": revenue,
        "top_user": top_user,
    }


@app.get("/work")
def work(n: int = 1):
    for _ in range(max(0, n)):
        pass

    return {
        "email": EMAIL,
        "done": n,
    }


@app.get("/healthz")
def health():
    return {
        "status": "ok",
        "uptime_s": time.time() - START,
    }


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/logs/tail")
def tail(limit: int = 10):
    limit = max(1, min(limit, 100))
    return list(logs)[-limit:]
