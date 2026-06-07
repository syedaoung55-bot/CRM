from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from .routers import auth, user, lead, note, file
from app import models
from app.database import engine, Base
from slowapi import Limiter


origins = ['*']

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(lead.router)
app.include_router(note.router)
app.include_router(file.router)

@app.get("/")
def root():
    return {"Message": "Welcome to my API Practice Project"}

# (Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ;
# (& d:\pyythonn\pp\APIS\venv\Scripts\Activate.ps1)