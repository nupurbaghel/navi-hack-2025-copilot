# Quick Start Guide

## Prerequisites

1. Install dependencies (if not already done):
```bash
poetry install
```

2. Set your OpenAI API key:
```bash
export OPENAI_API_KEY=your_openai_api_key_here
```

Or create a `.env` file:
```bash
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
```

## Step 1: Generate Checklist JSON

Run the LangChain agent to extract the checklist from the SR-20 manual:

```bash
poetry run python -m aviation_hackathon_sf.checklist_agent
```

This will:
- Read `sr20.md` from the project root
- Extract the "Before Takeoff" checklist using OpenAI
- Save the result to `checklist_before_takeoff.json`

**Expected output:**
```
Extracted X checklist items:
  - step_1: Doors
    Columns: ...
  - step_2: Fuel Quantity
    Columns: FQtyL, FQtyR
  ...
```

## Step 2: Start the API Server

### Option A: Using Docker Compose (Recommended)

```bash
# Make sure OPENAI_API_KEY is set in your environment or .env file
docker-compose up --build
```

The API will be available at: `http://localhost:8000`

### Option B: Using Poetry/Uvicorn directly

```bash
poetry run uvicorn aviation_hackathon_sf.main:app --reload --port 8000
```

Or use the Makefile:
```bash
make run
```

## Step 3: Test the API

Once the server is running, you can test the endpoints:

```bash
# Start a checklist
curl -X POST http://localhost:8000/checklist/start

# Get next step (replace <step_id> and <checklist_id> from previous response)
curl http://localhost:8000/checklist/next/step_1?checklist_id=<checklist_id>

# Check step status
curl http://localhost:8000/checklist/status/step_1?checklist_id=<checklist_id>

# Complete checklist
curl -X POST http://localhost:8000/checklist/complete \
  -H "Content-Type: application/json" \
  -d '{"checklist_id": "<checklist_id>"}'
```

## View API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

- **"Manual not found"**: Make sure `sr20.md` exists in the project root
- **"OPENAI_API_KEY not set"**: Export the environment variable or create a `.env` file
- **Port already in use**: Change the port in `docker-compose.yml` or use `--port` flag with uvicorn
