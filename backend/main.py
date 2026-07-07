from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
import httpx
import os

app = FastAPI(title="DevOps Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    config.load_kube_config()
except:
    config.load_incluster_config()

v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://18.199.150.120:9090")

@app.get("/")
def root():
    return {"status": "ok", "message": "DevOps Dashboard API"}

@app.get("/api/pods")
def get_pods():
    pods = v1.list_pod_for_all_namespaces()
    return [
        {
            "name": p.metadata.name,
            "namespace": p.metadata.namespace,
            "status": p.status.phase,
            "node": p.spec.node_name,
        }
        for p in pods.items
    ]

@app.get("/api/deployments")
def get_deployments():
    deps = apps_v1.list_deployment_for_all_namespaces()
    return [
        {
            "name": d.metadata.name,
            "namespace": d.metadata.namespace,
            "replicas": d.spec.replicas,
            "ready": d.status.ready_replicas,
        }
        for d in deps.items
    ]

@app.post("/api/deployments/{namespace}/{name}/restart")
def restart_deployment(namespace: str, name: str):
    import datetime
    body = {
        "spec": {
            "template": {
                "metadata": {
                    "annotations": {
                        "kubectl.kubernetes.io/restartedAt": datetime.datetime.utcnow().isoformat()
                    }
                }
            }
        }
    }
    apps_v1.patch_namespaced_deployment(name, namespace, body)
    return {"message": f"Deployment {name} restarted"}

@app.get("/api/metrics")
async def get_metrics():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{PROMETHEUS_URL}/api/v1/query?query=100-(avg(irate(node_cpu_seconds_total{{mode='idle'}}[5m]))*100)")
            cpu = r.json()["data"]["result"][0]["value"][1]
            r2 = await client.get(f"{PROMETHEUS_URL}/api/v1/query?query=(1-(node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes))*100")
            mem = r2.json()["data"]["result"][0]["value"][1]
            return {"cpu": round(float(cpu), 2), "memory": round(float(mem), 2)}
        except:
            return {"cpu": 0, "memory": 0}
