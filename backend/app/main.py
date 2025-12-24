from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()
from .routers.metrics import router as metrics_router
from .routers.transport import router as transport_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="TENeT Healthcare Desert Metrics API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(metrics_router, prefix="/metrics")
app.include_router(transport_router, prefix="/transport")

@app.get("/")
def root():
    return {"message": "Healthcare Desert API running"}
