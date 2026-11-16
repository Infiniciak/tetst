import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from py_eureka_client.eureka_client import EurekaClient

@asynccontextmanager
async def lifespan(app: FastAPI):
    eureka_client = EurekaClient(
        eureka_server=os.getenv("EUREKA_SERVER_URL", "http://127.0.0.1:8761"),
        eureka_context="/eureka",
        app_name=os.getenv("SERVICE_NAME", "DEPARTMENT-SERVICE"),
        instance_ip=os.getenv("INSTANCE_IP", "127.0.0.1"),
        instance_host=os.getenv("INSTANCE_HOST", "localhost"),
        instance_port=int(os.getenv("SERVICE_PORT", "8102")),
        strict_service_error_policy=False,
    )
    await eureka_client.start()
    try:
        yield
    finally:
        await eureka_client.stop()

app = FastAPI(title="Department Service", lifespan=lifespan)

DEPARTMENTS = {
    1: {"id": 1, "name": "Wsparcie IT", "building": "A"},
    2: {"id": 2, "name": "Infrastruktura", "building": "B"},
}

@app.get("/departments/{department_id}")
def get_department(department_id: int):
    dept = DEPARTMENTS.get(department_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Departament nie został znaleziony")
    return dept

@app.get("/health")
def health():
    return {"status": "UP"}