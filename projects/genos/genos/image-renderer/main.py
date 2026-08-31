from fastapi import FastAPI

app = FastAPI(title="genos service")

@app.get("/")
def read_root():
    return {"service": "genos", "status": "ok"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
