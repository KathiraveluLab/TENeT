from fastapi import FastAPI

app = FastAPI(title="TENeT API")

@app.get("/")
async def root():
    return {"message": "Welcome to TENeT API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
