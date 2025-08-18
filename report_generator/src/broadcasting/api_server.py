from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import asyncio
import json
import logging
from datetime import datetime
import uuid
from enum import Enum
import traceback
from contextlib import asynccontextmanager
import os
# custom
from src.custom_code.expert import Expert
from src.custom_code.lobe import LobeVectorMemory   
from src.custom_code.coordinator import Coordinator
from src.custom_code.summarizer import SummaryAgent
from src.custom_code.ra_team import ExpertTeam
from src.custom_code.expert_generator import ExpertGenerator
from langchain_openai import ChatOpenAI
from fastapi.middleware.cors import CORSMiddleware  # ADD THIS

from src.broadcasting.event_broadcaster import event_broadcaster, EventType
from src.broadcasting.logging_interceptor import StructuredLogInterceptor, PrintInterceptor
import builtins
from contextlib import contextmanager
# Job management
class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class AssessmentJob:
    def __init__(self, job_id: str, request_data: dict):
        self.job_id = job_id
        self.status = JobStatus.PENDING
        self.request_data = request_data
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.progress_logs = []

# Global storage (use Redis or database in production)
jobs: Dict[str, AssessmentJob] = {}
active_websockets: List[WebSocket] = []

# Custom logging handler that broadcasts to websockets
class StructuredWebSocketLogHandler(logging.Handler):
    def __init__(self, job_id: str):
        super().__init__()
        self.job_id = job_id
        self.interceptor = StructuredLogInterceptor(job_id)
        
    def emit(self, record):
        try:
            # Process the formatted message
            asyncio.create_task(
                self.interceptor.process_message(
                    self.format(record),
                    record.levelname
                )
            )
        except Exception as e:
            print(f"Error in StructuredWebSocketLogHandler: {e}")

@contextmanager
def intercept_print(job_id: str):
    """Context manager to intercept print statements"""
    original_print = builtins.print
    builtins.print = PrintInterceptor(job_id, original_print)
    try:
        yield
    finally:
        builtins.print = original_print

async def broadcast_update(message: dict):
    """Broadcast update to all connected WebSocket clients"""
    disconnected = []
    for websocket in active_websockets:
        try:
            await websocket.send_json(message)
        except:
            disconnected.append(websocket)
    
    # Clean up disconnected websockets
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Risk Assessment API Server...")
    app.state.vector_memory = await initialize_database()
    print("✅ Vector database initialized")
    yield
    # Shutdown
    print("🛑 Shutting down server...")

# Create FastAPI app
app = FastAPI(
    title="SWIFT Risk Assessment API",
    version="0.0.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Request models
class AssessmentRequest(BaseModel):
    query: str
    generate_experts: bool = False
    max_messages: int = 30
    expert_config: Optional[Dict[str, Any]] = None

class JobResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    message: str

# API Endpoints
@app.post("/api/assessments", response_model=JobResponse)
async def create_assessment(
    request: AssessmentRequest,
    background_tasks: BackgroundTasks
):
    """Submit a new risk assessment job"""
    job_id = str(uuid.uuid4())
    job = AssessmentJob(job_id, request.dict())
    jobs[job_id] = job
    
    # Start assessment in background
    background_tasks.add_task(
        run_assessment,
        job_id,
        request
    )
    
    return JobResponse(
        job_id=job_id,
        status=job.status.value,
        created_at=job.created_at.isoformat(),
        message="Assessment job created successfully"
    )

@app.get("/api/assessments/{job_id}")
async def get_assessment_status(job_id: str):
    """Get status and result of an assessment job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    response = {
        "job_id": job_id,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "progress_logs_count": len(job.progress_logs)
    }
    
    if job.status == JobStatus.COMPLETED:
        response["result"] = job.result
    elif job.status == JobStatus.FAILED:
        response["error"] = job.error
        
    return response

@app.get("/api/assessments/{job_id}/logs")
async def get_assessment_logs(job_id: str, since_index: int = 0):
    """Get progress logs for an assessment job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    logs = job.progress_logs[since_index:]
    
    return {
        "job_id": job_id,
        "logs": logs,
        "total_logs": len(job.progress_logs),
        "returned_logs": len(logs)
    }

@app.get("/api/experts")
async def get_experts():
    """Get list of approved experts"""
    try:
        with open("data/text_files/approved_experts.json", "r") as f:
            experts = json.load(f)
            return {
                "experts": experts,
                "count": len(experts),
                "summary": {
                    "names": [e["name"] for e in experts],
                    "domains": list(set(e.get("domain", "general") for e in experts))
                }
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/progress/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: Optional[str] = None):
    """Enhanced WebSocket endpoint with structured events"""
    await websocket.accept()
    
    # Create a queue for this connection
    queue = asyncio.Queue()
    event_broadcaster.add_listener(queue)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connection",
            "message": "Connected to structured progress updates",
            "job_id": job_id
        })
        
        # If job_id specified, send current experts immediately
        if job_id and job_id in jobs:
            # Send approved experts
            try:
                with open("data/text_files/approved_experts.json", "r") as f:
                    experts = json.load(f)
                    await event_broadcaster.broadcast(
                        EventType.APPROVED_EXPERTS,
                        {
                            "experts": experts,
                            "count": len(experts)
                        },
                        job_id
                    )
            except:
                pass
        
        # Listen for events
        while True:
            try:
                # Wait for events with timeout for ping/pong
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                # Filter by job_id if specified
                if job_id and event.get("job_id") != job_id:
                    continue
                    
                await websocket.send_json(event)
                
            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_json({"type": "ping"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        event_broadcaster.remove_listener(queue)

@app.get("/api/jobs")
async def list_jobs(status: Optional[str] = None):
    """List all assessment jobs"""
    job_list = []
    for job_id, job in jobs.items():
        if status and job.status.value != status:
            continue
            
        job_list.append({
            "job_id": job_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "query_preview": job.request_data.get("query", "")[:100] + "..."
        })
    
    return {"jobs": job_list, "total": len(job_list)}

# Initialize database function
async def initialize_database():
    from src.custom_code.lobe import LobeVectorMemory
    
    vector_memory = LobeVectorMemory(persist_directory="./data/vectordb")
    
    # Add files from a folder
    stats = await vector_memory.add_folder(
        folder_path="data/database",
        file_extensions=['.txt', '.md', '.pdf']
    )
    
    print(f"Database initialized: {stats['added']} files added, {stats['skipped']} skipped")
    return vector_memory

# Background task to run assessment
async def run_assessment(job_id: str, request: AssessmentRequest):
    """Run the risk assessment in background"""
    job = jobs[job_id]
    
    job_logger = logging.getLogger(f"assessment_{job_id}")
    job_logger.setLevel(logging.INFO)
    
    ws_handler = StructuredWebSocketLogHandler(job_id)
    ws_handler.setFormatter(logging.Formatter('%(message)s'))
    job_logger.addHandler(ws_handler)
    
    with intercept_print(job_id):
        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()
            
            await event_broadcaster.broadcast(
                EventType.STATUS_CHANGE,
                {
                    "status": "running",
                    "message": "Assessment started"
                },
                job_id
            )
            
            job_logger.info("🚀 Starting risk assessment...")
            
            # Load required files
            with open("data/text_files/swift_info.md", "r", encoding="utf-8") as file:
                swift_info = file.read()
            
            with open("data/text_files/database_info.txt", "r", encoding="utf-8") as file:
                database_info = file.read()
            
            # Get vector memory from app state
            vector_memory = app.state.vector_memory
            
            # Create model clients
            model_client = ChatOpenAI(model="gpt-4.1")
            
            # Generate or load experts
            if request.generate_experts:
                job_logger.info("📝 Generating expert team...")
                
                expert_generator = ExpertGenerator(
                    model="gpt-4.1",
                    provider="openai",
                    min_experts=5,
                    max_experts=12
                )
                
                approved_experts = expert_generator.run_expert_generator(
                    user_request=request.query,
                    swift_details=swift_info,
                    database_info=database_info
                )
            else:
                with open("data/text_files/approved_experts.json", "r") as f:
                    approved_experts = json.load(f)
            await event_broadcaster.broadcast(
                EventType.APPROVED_EXPERTS,
                {
                    "experts": approved_experts,
                    "count": len(approved_experts),
                    "names": [e["name"] for e in approved_experts]
                },
                job_id
            )

            job_logger.info(f"👥 Creating {len(approved_experts)} experts...")
            
            # Create experts
            experts = {}
            for expert in approved_experts:
                expert_name = expert["name"]
                expert_agent = Expert(
                    name=expert_name.lower().replace(" ", "_").replace("-", "_"),
                    model_client=model_client,
                    vector_memory=vector_memory,
                    system_message=expert["system_prompt"],
                    lobe1_config={"keywords": expert["keywords"]},
                    lobe2_config={"keywords": expert["keywords"]},
                    debug=False
                )
                experts[expert_name] = expert_agent
                job_logger.info(f"✅ Created expert: {expert_name}")
            
            # Create team components
            coordinator = Coordinator(model_client, experts, debug=True)
            summary_agent = SummaryAgent(model_client, debug=True)
            
            # Create team with custom logger
            team = ExpertTeam(
                coordinator=coordinator,
                experts=experts,
                summary_agent=summary_agent,
                max_messages=request.max_messages,
                debug=True
            )
            
            job_logger.info("🎯 Starting team consultation...")
            
            # Run assessment
            result = await team.consult(request.query)
            
            # Save result
            job.result = result
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            
            job_logger.info("✅ Assessment completed successfully!")
            
            await broadcast_update({
                "job_id": job_id,
                "type": "status_change", 
                "status": "completed",
                "message": "Assessment completed successfully"
            })
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()
            
            job_logger.error(f"❌ Assessment failed: {str(e)}")
            job_logger.error(traceback.format_exc())
            
            await broadcast_update({
                "job_id": job_id,
                "type": "status_change",
                "status": "failed",
                "message": f"Assessment failed: {str(e)}"
            })
        
        finally:
            # Clean up logger
            job_logger.removeHandler(ws_handler)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_jobs": sum(1 for j in jobs.values() if j.status == JobStatus.RUNNING),
        "total_jobs": len(jobs)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.broadcasting.api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
