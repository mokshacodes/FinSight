# FinSight/src/app/__init__.py

from fastapi import FastAPI

app = FastAPI()

from .api.v1 import routes

app.include_router(routes.router)