from fastapi import FastAPI

from aviation_hackathon_sf.checklist_api import create_checklist_endpoints

app = FastAPI(
    title="Aviation Hackathon SF - Co-Pilot Assistant API",
    description="AI-powered co-pilot assistant for pre-flight checklist validation using flight telemetry data",
    version="0.1.0",
)

# Register checklist endpoints
create_checklist_endpoints(app)


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "name": "Aviation Hackathon SF - Co-Pilot Assistant",
        "description": "AI-powered co-pilot assistant for pre-flight checklist validation",
        "version": "0.1.0",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "checklist_start": "POST /checklist/start",
            "checklist_next": "GET /checklist/next/{step_id}",
            "checklist_status": "GET /checklist/status/{step_id}",
            "checklist_complete": "POST /checklist/complete",
        },
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
