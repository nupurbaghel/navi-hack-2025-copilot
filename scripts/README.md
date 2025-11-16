# Checklist Simulator Script

This script simulates how a frontend would interact with the checklist API, demonstrating the complete workflow from starting a checklist to completing it.

## Usage

### Basic Usage

```bash
# Run the checklist simulator
poetry run python scripts/run_checklist.py

# Or using Make
make run-checklist
```

### Debug Mode

Shows all API requests and responses:

```bash
poetry run python scripts/run_checklist.py --debug

# Or using Make
make run-checklist-debug
```

### Demo Mode

Shows each checklist item with descriptions and delays for better visualization:

```bash
poetry run python scripts/run_checklist.py --demo

# Or using Make
make run-checklist-demo
```

### Combined Modes

```bash
# Both debug and demo
poetry run python scripts/run_checklist.py --debug --demo

# Custom API URL
poetry run python scripts/run_checklist.py --url http://localhost:8080
```

## Features

- **Simulates Frontend Workflow**: Makes the same API calls a frontend would make
- **Step-by-Step Progress**: Shows status of each checklist item
- **Color-Coded Status**:
  - ✓ Green: Success (PASSED)
  - ⚠ Yellow: Caution (CAUTION)
  - ✗ Red: Warning/Error (WARNING/FAILED)
  - ? Gray: No Data (NO DATA)
- **Debug Mode**: Shows raw API requests and responses
- **Demo Mode**: Displays checklist items with descriptions and processing delays

## Example Output

### Normal Mode
```
Starting Checklist Session
✓ Checklist started
Checklist ID: a251c633-1bcb-498d-80c3-bc50d3d09f78
Total steps: 5

Step 1/5: Fuel Quantity
✓ PASSED    Fuel Quantity
            OK: Total fuel: 27.9 gallons - Within normal range
            Next: step_2
```

### Demo Mode
```
Starting Checklist Session
✓ Checklist started

📋 Step: Fuel Quantity
Confirm fuel quantity is adequate for flight.
Processing...
Validating telemetry data...

✓ PASSED    Fuel Quantity
            OK: Total fuel: 27.9 gallons - Within normal range
            Next: step_2
```

## Requirements

- API server running on `http://localhost:8000` (or specify with `--url`)
- `flight_data.csv` available for telemetry validation
- `checklist_before_takeoff.json` with checklist definitions
