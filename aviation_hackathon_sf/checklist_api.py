"""
FastAPI endpoints for checklist workflow.
"""

import json
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from loguru import logger
from aviation_hackathon_sf.telemetry_validator import TelemetryValidator

# In-memory storage for checklist state (in production, use Redis or database)
checklist_state: Dict[str, Dict] = {}
checklist_data: Optional[List[Dict]] = None
telemetry_validator: Optional[TelemetryValidator] = None


class ChecklistStartResponse(BaseModel):
    """Response for /checklist/start endpoint."""

    checklist_id: str
    steps: List[Dict]
    message: str


class ChecklistNextResponse(BaseModel):
    """Response for /checklist/next endpoint."""

    step_id: str
    step_name: str
    message: str


class ChecklistStatusResponse(BaseModel):
    """Response for /checklist/status endpoint."""

    step_id: str
    status: str  # "pending", "running", "success", "failed"
    next_step_id: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ChecklistCompleteRequest(BaseModel):
    """Request for /checklist/complete endpoint."""

    checklist_id: str


class ChecklistCompleteResponse(BaseModel):
    """Response for /checklist/complete endpoint."""

    checklist_id: str
    message: str
    completed_steps: int
    total_steps: int


class TelemetryLoadRequest(BaseModel):
    """Request for /telemetry/load endpoint."""

    csv_path: str


class TelemetryLoadResponse(BaseModel):
    """Response for /telemetry/load endpoint."""

    success: bool
    message: str
    csv_path: str
    rows_loaded: Optional[int] = None


def get_telemetry_validator(csv_path: Optional[str] = None) -> Optional[TelemetryValidator]:
    """Get or create telemetry validator instance.

    Args:
        csv_path: Optional path to CSV file. If None, uses default or environment variable.

    Returns:
        TelemetryValidator instance, or None if CSV file not found
    """
    global telemetry_validator  # noqa: PLW0603

    # If csv_path is provided, reload the validator
    if csv_path:
        csv_file = Path(csv_path)
        if not csv_file.exists():
            logger.warning(f"Flight data CSV not found at {csv_file}")
            return None
        logger.info(f"Loading telemetry data from: {csv_file}")
        telemetry_validator = TelemetryValidator(str(csv_file))
        return telemetry_validator

    # Use existing validator if available
    if telemetry_validator is not None:
        return telemetry_validator

    # Try to find CSV file
    csv_path = os.getenv("FLIGHT_DATA_CSV")
    if not csv_path:
        # Try default location
        csv_path = Path(__file__).parent.parent / "flight_data.csv"

    if not Path(csv_path).exists():
        logger.warning(f"Flight data CSV not found at {csv_path}")
        return None

    telemetry_validator = TelemetryValidator(str(csv_path))
    return telemetry_validator


def load_checklist_data(checklist_file: Optional[str] = None) -> List[Dict]:
    """Load checklist data from JSON file.

    Args:
        checklist_file: Path to checklist JSON file. If None, uses default.

    Returns:
        List of checklist items
    """
    global checklist_data

    if checklist_data is not None:
        return checklist_data

    if checklist_file is None:
        checklist_file = Path(__file__).parent.parent / "checklist_before_takeoff.json"

    checklist_path = Path(checklist_file)
    if not checklist_path.exists():
        logger.warning(f"Checklist file not found at {checklist_path}, using dummy data")
        # Return dummy checklist for now
        return [
            {
                "step_id": "step_1",
                "name": "Doors",
                "description": "Verify doors are latched",
                "expected_value": "LATCHED",
                "telemetry_columns": [],
                "validation_logic": "Visual check required",
            },
            {
                "step_id": "step_2",
                "name": "Fuel Quantity",
                "description": "Confirm fuel quantity is adequate",
                "expected_value": "> minimum required",
                "telemetry_columns": ["FQtyL", "FQtyR"],
                "validation_logic": "Sum of FQtyL and FQtyR should be above minimum",
            },
            {
                "step_id": "step_3",
                "name": "Engine Parameters",
                "description": "Check engine parameters are within normal ranges",
                "expected_value": "Within green arcs",
                "telemetry_columns": ["E1 RPM", "E1 OilT", "E1 OilP", "E1 CHT1"],
                "validation_logic": "All engine parameters should be within normal operating ranges",
            },
        ]

    checklist_data = json.loads(checklist_path.read_text(encoding="utf-8"))
    logger.info(f"Loaded {len(checklist_data)} checklist items from {checklist_path}")
    return checklist_data


def create_checklist_endpoints(app: FastAPI):
    """Create checklist endpoints and add them to the FastAPI app.

    Args:
        app: FastAPI application instance
    """

    @app.post("/checklist/start", response_model=ChecklistStartResponse)
    def start_checklist():
        """Start a new checklist session.

        Returns:
            Checklist ID and list of steps
        """
        checklist_id = str(uuid.uuid4())
        steps = load_checklist_data()

        # Initialize checklist state
        checklist_state[checklist_id] = {
            "checklist_id": checklist_id,
            "current_step_index": 0,
            "steps": steps,
            "status": "in_progress",
        }

        logger.info(f"Started checklist {checklist_id} with {len(steps)} steps")

        return ChecklistStartResponse(
            checklist_id=checklist_id,
            steps=[
                {
                    "step_id": step["step_id"],
                    "name": step["name"],
                    "description": step.get("description", ""),
                }
                for step in steps
            ],
            message="Checklist started. Use /checklist/next/<step_id> to proceed with each step.",
        )

    @app.get("/checklist/next/{step_id}", response_model=ChecklistNextResponse)
    def get_next_step(step_id: str, checklist_id: Optional[str] = None):
        """Get the next step in the checklist and start validation.

        Args:
            step_id: ID of the step to process
            checklist_id: Optional checklist ID from query parameter

        Returns:
            Step information and status
        """
        # Validate checklist_id if provided
        if checklist_id and checklist_id not in checklist_state:
            raise HTTPException(status_code=404, detail=f"Checklist {checklist_id} not found")

        steps = load_checklist_data()
        step = next((s for s in steps if s["step_id"] == step_id), None)

        if not step:
            raise HTTPException(status_code=404, detail=f"Step {step_id} not found")

        # In a real implementation, this would trigger background validation
        # For now, we just return the step info
        logger.info(f"Processing step {step_id}: {step['name']} for checklist {checklist_id}")

        return ChecklistNextResponse(
            step_id=step_id,
            step_name=step["name"],
            message=f"Processing {step['name']}. Use /checklist/status/{step_id}?checklist_id={checklist_id} to check status.",
        )

    @app.get("/checklist/status/{step_id}", response_model=ChecklistStatusResponse)
    def get_step_status(step_id: str, checklist_id: Optional[str] = None):
        """Get the status of a checklist step.

        Args:
            step_id: ID of the step to check
            checklist_id: Optional checklist ID from query parameter

        Returns:
            Step status and next step ID if successful
        """
        # Validate checklist_id if provided
        if checklist_id and checklist_id not in checklist_state:
            raise HTTPException(status_code=404, detail=f"Checklist {checklist_id} not found")

        steps = load_checklist_data()
        step = next((s for s in steps if s["step_id"] == step_id), None)

        if not step:
            raise HTTPException(status_code=404, detail=f"Step {step_id} not found")

        # Find current step index
        current_index = next((i for i, s in enumerate(steps) if s["step_id"] == step_id), None)

        if current_index is None:
            raise HTTPException(status_code=404, detail=f"Step {step_id} not found in checklist")

        # Validate against telemetry data
        validator = get_telemetry_validator()
        if validator:
            status, message, _details = validator.validate_step(step)
            logger.info(f"Status check for step {step_id} (checklist {checklist_id}): {status} - {message}")

            # Determine if we can proceed to next step
            # Only proceed if status is "success" or "caution" (warnings block progression)
            next_step_id = None
            if status in ("success", "caution"):
                if current_index < len(steps) - 1:
                    next_step_id = steps[current_index + 1]["step_id"]
            elif status == "warning":
                # Warning blocks progression - pilot must address
                return ChecklistStatusResponse(
                    step_id=step_id,
                    status="warning",
                    next_step_id=None,
                    error=message,
                    message=f"WARNING: {step['name']} - {message}",
                )
            elif status == "no_data":
                # No data available - might be OK for some steps
                if current_index < len(steps) - 1:
                    next_step_id = steps[current_index + 1]["step_id"]
                return ChecklistStatusResponse(
                    step_id=step_id,
                    status="no_data",
                    next_step_id=next_step_id,
                    message=message,
                )
            else:
                # Failed validation - use the detailed message from validator
                return ChecklistStatusResponse(
                    step_id=step_id,
                    status="failed",
                    next_step_id=None,
                    error=message,
                    message=f"FAILED: {step['name']} - {message}",
                )

            return ChecklistStatusResponse(
                step_id=step_id,
                status=status,
                next_step_id=next_step_id,
                message=message,
            )
        else:
            # No validator available - return dummy success
            logger.warning("No telemetry validator available, returning dummy status")
            next_step_id = None
            if current_index < len(steps) - 1:
                next_step_id = steps[current_index + 1]["step_id"]

            return ChecklistStatusResponse(
                step_id=step_id,
                status="success",
                next_step_id=next_step_id,
                message=f"Step {step['name']} - No telemetry data available (using dummy validation)",
            )

    @app.post("/checklist/complete", response_model=ChecklistCompleteResponse)
    def complete_checklist(request: ChecklistCompleteRequest):
        """Complete the checklist session.

        Args:
            request: Request containing checklist_id

        Returns:
            Completion message and summary
        """
        checklist_id = request.checklist_id

        if checklist_id not in checklist_state:
            raise HTTPException(status_code=404, detail=f"Checklist {checklist_id} not found")

        state = checklist_state[checklist_id]
        steps = state["steps"]

        # Mark as complete
        state["status"] = "completed"

        logger.info(f"Completed checklist {checklist_id}")

        return ChecklistCompleteResponse(
            checklist_id=checklist_id,
            message="Checklist completed successfully. Aircraft is ready for takeoff.",
            completed_steps=len(steps),
            total_steps=len(steps),
        )

    @app.post("/telemetry/load", response_model=TelemetryLoadResponse)
    def load_telemetry(request: TelemetryLoadRequest):
        """Load a new telemetry CSV file.

        Args:
            request: Request containing path to CSV file

        Returns:
            Response with load status
        """
        global telemetry_validator  # noqa: PLW0603

        csv_path = request.csv_path
        csv_file = Path(csv_path)

        # Check if file exists (try relative to project root if not absolute)
        if not csv_file.is_absolute():
            # Try relative to project root
            project_root = Path(__file__).parent.parent
            csv_file = project_root / csv_path

        if not csv_file.exists():
            raise HTTPException(status_code=404, detail=f"CSV file not found at {csv_path}")

        try:
            # Load new validator
            validator = get_telemetry_validator(str(csv_file))
            if validator:
                rows_loaded = validator.get_row_count()
                logger.info(f"Loaded telemetry from {csv_file}: {rows_loaded} rows")
                return TelemetryLoadResponse(
                    success=True,
                    message=f"Telemetry data loaded successfully from {csv_file.name}",
                    csv_path=str(csv_file),
                    rows_loaded=rows_loaded,
                )
            else:
                return TelemetryLoadResponse(
                    success=False,
                    message=f"Failed to load telemetry from {csv_file}",
                    csv_path=str(csv_file),
                )
        except Exception as e:
            logger.error(f"Error loading telemetry: {e}")
            raise HTTPException(status_code=500, detail=f"Error loading telemetry file: {str(e)}")
