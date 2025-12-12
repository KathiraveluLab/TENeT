from fastapi import FastAPI
from dotenv import load_dotenv
load_dotenv()
from .routers.healthsites import router as healthsites_router
from .routers.metrics import router as metrics_router
from .routers.transport import router as transport_router
from .routers.specialists import router as specialist_router

app = FastAPI(title="TENeT Healthcare Desert Metrics API")

app.include_router(healthsites_router, prefix="/healthsites")
app.include_router(metrics_router, prefix="/metrics")
app.include_router(transport_router, prefix="/transport")
app.include_router(specialist_router, prefix="/specialists")

@app.get("/")
def root():
    return {"message": "Healthcare Desert API running"}
