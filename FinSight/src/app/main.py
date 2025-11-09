from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.app.api.v1.routes import router as api_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to FinSight API"}

# Additional endpoints can be defined here as needed.