from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from .routers import (auth, team, user, lead, note, file, companies, pipelinestage, task,
                      notification, dashboard, search, tag, audit_log)
from sqlalchemy import text
from sqlalchemy.orm import Session
from .database import get_db
from fastapi import Depends, HTTPException, status
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from prometheus_fastapi_instrumentator import Instrumentator
from.logging_config import setup_logging
import logging
from contextlib import asynccontextmanager
from .routers.scheduler import scheduler


setup_logging()

logger = logging.getLogger("crm.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    FastAPICache.init(InMemoryBackend(), prefix="crm-cache")
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)
origins = ['*']
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(user.router)
app.include_router(companies.router)
app.include_router(auth.router)
app.include_router(lead.router)
app.include_router(note.router)
app.include_router(tag.router)
app.include_router(file.router)
app.include_router(pipelinestage.router)
app.include_router(notification.router)
app.include_router(team.router)
app.include_router(task.router)
app.include_router(dashboard.router)
app.include_router(search.router)
app.include_router(audit_log.router)


Instrumentator().instrument(app).expose(app, endpoint="/metrics")

@app.get("/")
def root():
    return {"Message": "Welcome to my API Practice Project"}

@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return{"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Database Unavaliable.")

# (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ;
# (& d:\pyythonn\pp\APIS\venv\Scripts\Activate.ps1)