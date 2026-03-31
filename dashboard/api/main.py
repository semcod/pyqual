from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pathlib import Path
import sqlite3
import json
import ast
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()
INGEST_TOKEN = os.getenv("PYQUAL_DASHBOARD_TOKEN", "default-token-change-me")

app = FastAPI(
    title="Pyqual Dashboard API",
    description="API for serving Pyqual quality metrics",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files (for production)
if Path("../dist").exists():
    app.mount("/", StaticFiles(directory="../dist", html=True), name="static")

# Database helper functions
def get_db_path(project_id: str) -> Path:
    """Get the path to a project's pipeline database."""
    return Path(f"projects/{project_id}/.pyqual/pipeline.db")

def read_summary_json(project_id: str) -> Optional[Dict[str, Any]]:
    """Read the summary.json file for a project."""
    summary_path = Path(f"projects/{project_id}/.pyqual/summary.json")
    if summary_path.exists():
        try:
            with open(summary_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Failed to read summary for {project_id}: {e}")
    return None

def query_pipeline_db(db_path: Path, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Execute a query on the pipeline database."""
    if not db_path.exists():
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    except (sqlite3.Error, OSError) as e:
        logger.error(f"Database query failed: {e}")
        return []

# API Endpoints
@app.get("/api/projects")
async def get_projects():
    """List all configured projects."""
    projects = []
    projects_dir = Path("projects")
    
    if not projects_dir.exists():
        return projects
    
    for project_dir in projects_dir.iterdir():
        if project_dir.is_dir():
            summary = read_summary_json(project_dir.name)
            if summary:
                projects.append({
                    "id": project_dir.name,
                    "name": summary.get("project_name", project_dir.name),
                    "url": summary.get("project_url", ""),
                    "branch": summary.get("branch", "main"),
                    "last_run": summary
                })
    
    return projects

@app.get("/api/projects/{project_id}/latest")
async def get_latest_run(project_id: str):
    """Get the latest run for a project."""
    summary = read_summary_json(project_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Project not found or no runs available")
    return summary

@app.get("/api/projects/{project_id}/runs")
async def get_project_runs(project_id: str, limit: int = 50):
    """Get recent runs for a project."""
    db_path = get_db_path(project_id)
    
    # Get pipeline end events
    query = """
        SELECT timestamp, kwargs
        FROM pipeline_logs
        WHERE function_name = 'pipeline_end'
        ORDER BY id DESC
        LIMIT ?
    """
    
    runs = []
    for row in query_pipeline_db(db_path, query, (limit,)):
        kwargs = ast.literal_eval(row["kwargs"])
        run = {
            "timestamp": row["timestamp"],
            "status": "passed" if kwargs.get("final_ok") else "failed",
            "duration_s": kwargs.get("total_duration_s", 0),
            "iterations": kwargs.get("iterations", 0)
        }
        runs.append(run)
    
    return runs

@app.get("/api/projects/{project_id}/metrics/{metric}")
async def get_metric_history(project_id: str, metric: str, days: int = 30):
    """Get historical values for a specific metric."""
    db_path = get_db_path(project_id)
    
    # Calculate date threshold
    threshold = (datetime.now() - timedelta(days=days)).isoformat()
    
    query = """
        SELECT timestamp, kwargs
        FROM pipeline_logs
        WHERE function_name = 'gate_check'
        AND kwargs LIKE ?
        AND timestamp > ?
        ORDER BY timestamp
    """
    
    history = []
    pattern = f"%'metric': '{metric}'%"
    
    for row in query_pipeline_db(db_path, query, (pattern, threshold)):
        kwargs = ast.literal_eval(row["kwargs"])
        if kwargs.get("metric") == metric:
            history.append({
                "timestamp": row["timestamp"],
                "value": kwargs.get("value", 0)
            })
    
    return history

@app.get("/api/projects/{project_id}/stages")
async def get_stage_performance(project_id: str, days: int = 30):
    """Get stage performance over time."""
    db_path = get_db_path(project_id)
    
    threshold = (datetime.now() - timedelta(days=days)).isoformat()
    
    query = """
        SELECT timestamp, kwargs, duration_ms
        FROM pipeline_logs
        WHERE function_name = 'stage_done'
        AND timestamp > ?
        ORDER BY timestamp
    """
    
    stages = {}
    for row in query_pipeline_db(db_path, query, (threshold,)):
        kwargs = ast.literal_eval(row["kwargs"])
        stage_name = kwargs.get("stage", "unknown")
        
        if stage_name not in stages:
            stages[stage_name] = []
        
        stages[stage_name].append({
            "timestamp": row["timestamp"],
            "duration_s": kwargs.get("duration_s", 0),
            "passed": kwargs.get("ok", False),
            "skipped": kwargs.get("skipped", False)
        })
    
    return stages

@app.get("/api/projects/{project_id}/gates")
async def get_gate_status(project_id: str, days: int = 7):
    """Get recent gate check results."""
    db_path = get_db_path(project_id)
    
    threshold = (datetime.now() - timedelta(days=days)).isoformat()
    
    query = """
        SELECT timestamp, kwargs
        FROM pipeline_logs
        WHERE function_name = 'gate_check'
        AND timestamp > ?
        ORDER BY timestamp DESC
    """
    
    gates = []
    for row in query_pipeline_db(db_path, query, (threshold,)):
        kwargs = ast.literal_eval(row["kwargs"])
        gates.append({
            "timestamp": row["timestamp"],
            "metric": kwargs.get("metric"),
            "value": kwargs.get("value"),
            "threshold": kwargs.get("threshold"),
            "passed": kwargs.get("ok", False)
        })
    
    return gates

@app.get("/api/projects/{project_id}/summary")
async def get_project_summary(project_id: str):
    """Get a comprehensive summary of project metrics."""
    db_path = get_db_path(project_id)
    
    # Get latest pipeline end
    end_rows = query_pipeline_db(
        db_path,
        "SELECT timestamp, kwargs FROM pipeline_logs WHERE function_name = 'pipeline_end' ORDER BY id DESC LIMIT 1"
    )
    
    if not end_rows:
        raise HTTPException(status_code=404, detail="No pipeline runs found")
    
    latest = ast.literal_eval(end_rows[0]["kwargs"])
    
    # Get all gate checks from latest run
    # This is a simplified approach - in production, you'd track run IDs
    gate_query = """
        SELECT kwargs FROM pipeline_logs
        WHERE function_name = 'gate_check'
        AND timestamp <= ?
        ORDER BY timestamp DESC
    """
    
    gates = []
    for row in query_pipeline_db(db_path, gate_query, (end_rows[0]["timestamp"],)):
        kwargs = ast.literal_eval(row["kwargs"])
        gates.append(kwargs)
    
    # Calculate metrics
    metrics = {}
    for gate in gates:
        if gate.get("metric"):
            metrics[gate["metric"]] = gate["value"]
    
    return {
        "timestamp": end_rows[0]["timestamp"],
        "status": "passed" if latest.get("final_ok") else "failed",
        "duration_s": latest.get("total_duration_s", 0),
        "iterations": latest.get("iterations", 0),
        "metrics": metrics,
        "gates": gates
    }

@app.post("/api/projects/{project_id}/ingest")
async def ingest_results(
    project_id: str, 
    data: Dict[str, Any],
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Ingest results from CI/CD pipeline."""
    # Verify token
    if credentials.credentials != INGEST_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    # Validate data structure
    required_fields = ["timestamp", "status", "metrics"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Create project directory if needed
    project_dir = Path(f"projects/{project_id}")
    project_dir.mkdir(parents=True, exist_ok=True)
    
    # Create .pyqual directory
    pyqual_dir = project_dir / ".pyqual"
    pyqual_dir.mkdir(exist_ok=True)
    
    # Save summary
    summary_path = pyqual_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(data, f, indent=2)
    
    # If pipeline.db is included, save it
    if "pipeline_db_base64" in data:
        import base64
        db_data = base64.b64decode(data["pipeline_db_base64"])
        with open(pyqual_dir / "pipeline.db", "wb") as f:
            f.write(db_data)
    
    logger.info(f"Successfully ingested results for project {project_id}")
    return {"status": "success", "project_id": project_id}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
