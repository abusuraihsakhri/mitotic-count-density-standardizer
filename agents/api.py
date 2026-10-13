"""FastAPI service for calibrated density conversion and legacy demonstration APIs."""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mitotic_density import calculate_metrics
from .base import AuditLogger
from .models import SystemTaskPayload
from .supervisor import SystemSupervisor

supervisor = SystemSupervisor(model_provider="mock")
app = FastAPI(
    title="Mitotic Count Density Standardizer API",
    description="Area-normalized mitotic measurements; separate demo-only agent endpoints.",
    version="3.1.0",
)


class DensityRequest(BaseModel):
    mitotic_count: int = Field(ge=0)
    field_diameter_mm: float | None = None
    measured_area_mm2: float | None = None
    fields_counted: int = Field(default=10, ge=1)


class ChatRequest(BaseModel):
    query: str


@app.get("/", include_in_schema=False)
def index():
    path = Path(__file__).resolve().parent.parent / "web" / "index.html"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Browser interface not installed")
    return FileResponse(path)


@app.get("/health")
def health():
    return {"status": "running", "service": "mitotic-count-density-standardizer",
            "version": "3.1.0", "agent_workflow": "demonstration_only"}


@app.get("/metrics")
def metrics():
    return {"dossiers_processed_total": len(supervisor.dossier_registry),
            "audit_blocks_total": len(AuditLogger.get_trail()),
            "audit_integrity_verified": AuditLogger.verify_integrity()}


@app.post("/api/density")
def api_density(payload: DensityRequest):
    try:
        return calculate_metrics(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/audit")
def api_audit(payload: SystemTaskPayload):
    dossier = supervisor.process_task(payload)
    return {"experimental_demo": True, **dossier.to_dict()}


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return {"response": supervisor.query_supervisory_chat(req.query),
                "experimental_demo": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/audit/logs")
def api_audit_logs():
    return {"audit_trail": AuditLogger.get_trail(),
            "verified": AuditLogger.verify_integrity(),
            "persistence": "process_memory_only"}
