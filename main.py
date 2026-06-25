from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx
import os

app = FastAPI(title="DevOps Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090")

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.get("/api/metrics")
async def get_metrics():
    async with httpx.AsyncClient() as c:
        try:
            r = await c.get(PROMETHEUS_URL + "/api/v1/query", params={"query": "100-(avg(irate(node_cpu_seconds_total{mode='idle'}[5m]))*100)"})
            cpu = r.json()["data"]["result"][0]["value"][1]
            r2 = await c.get(PROMETHEUS_URL + "/api/v1/query", params={"query": "(1-(node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes))*100"})
            mem = r2.json()["data"]["result"][0]["value"][1]
            r3 = await c.get(PROMETHEUS_URL + "/api/v1/query", params={"query": "(1-(node_filesystem_avail_bytes{mountpoint='/etc/hostname'}/node_filesystem_size_bytes{mountpoint='/etc/hostname'}))*100"})
            disk = r3.json()["data"]["result"][0]["value"][1]
            return {
                "cpu": round(float(cpu), 2),
                "memory": round(float(mem), 2),
                "disk": round(float(disk), 2)
            }
        except Exception as e:
            return {"cpu": 0, "memory": 0, "disk": 0, "error": str(e)}

@app.get("/api/services")
async def get_services():
    services = [
        {"name": "Prometheus", "url": "http://127.0.0.1:9090/-/healthy"},
        {"name": "Grafana", "url": "http://127.0.0.1:3000/api/health"},
        {"name": "Alertmanager", "url": "http://127.0.0.1:9093/-/healthy"},
    ]
    results = []
    async with httpx.AsyncClient(timeout=3) as c:
        for svc in services:
            try:
                r = await c.get(svc["url"])
                results.append({"name": svc["name"], "status": "up" if r.status_code == 200 else "down"})
            except:
                results.append({"name": svc["name"], "status": "down"})
    return results

app.mount("/", StaticFiles(directory="static", html=True), name="static")
