from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="TENeT API")

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to TENeT API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

# Mount the data directory to serve GeoJSON files
data_path = os.getenv("DATA_DIR", "/data")
if os.path.exists(data_path):
    app.mount("/data", StaticFiles(directory=data_path), name="data")
