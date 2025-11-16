"""
LangChain-based agent to extract checklist items from SR-20 manual
and map them to CSV telemetry columns.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from loguru import logger


class ChecklistAgent:
    """Agent that extracts checklists from SR-20 manual and maps to telemetry columns."""

    # Available CSV columns from flight telemetry data
    CSV_COLUMNS = [
        # Timestamp & Identification
        "Lcl Date",
        "Lcl Time",
        "UTCOfst",
        "AtvWpt",
        # Position & Navigation
        "Latitude",
        "Longitude",
        "AltInd",
        "BaroA",
        "AltMSL",
        "AltGPS",
        "WptDst",
        "WptBrg",
        "MagVar",
        "CRS",
        "NAV1",
        "NAV2",
        "COM1",
        "COM2",
        "HCDI",
        "VCDI",
        "GPSfix",
        "HAL",
        "VAL",
        "HPLwas",
        "HPLfd",
        "VPLwas",
        # Flight Dynamics
        "IAS",
        "GndSpd",
        "TAS",
        "VSpd",
        "VSpdG",
        "Pitch",
        "Roll",
        "HDG",
        "TRK",
        "LatAc",
        "NormAc",
        # Environmental
        "OAT",
        "WndSpd",
        "WndDr",
        # Engine Parameters
        "E1 RPM",
        "E1 %Pwr",
        "E1 MAP",
        "E1 FFlow",
        "E1 OilT",
        "E1 OilP",
        "E1 CHT1",
        "E1 CHT2",
        "E1 CHT3",
        "E1 CHT4",
        "E1 CHT5",
        "E1 CHT6",
        "E1 EGT1",
        "E1 EGT2",
        "E1 EGT3",
        "E1 EGT4",
        "E1 EGT5",
        "E1 EGT6",
        "E1 TIT1",
        "E1 TIT2",
        "E1 Torq",
        "E1 NG",
        "E1 ITT",
        # Fuel System
        "FQtyL",
        "FQtyR",
        # Electrical System
        "volt1",
        "volt2",
        "amp1",
        # Autopilot/Flight Control System
        "AfcsOn",
        "RollM",
        "PitchM",
        "RollC",
        "PichC",
        # Navigation Source
        "HSIS",
    ]

    def __init__(self, openai_api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """Initialize the checklist agent.

        Args:
            openai_api_key: OpenAI API key. If None, will try to get from environment.
            model: OpenAI model to use.
        """
        self.llm = ChatOpenAI(
            model=model,
            temperature=0,
            api_key=openai_api_key,
        )
        self.output_parser = StrOutputParser()

    def extract_checklist(self, manual_path: str, checklist_type: str = "Before Takeoff") -> List[Dict]:
        """Extract checklist items from the SR-20 manual.

        Args:
            manual_path: Path to the sr20.md file
            checklist_type: Type of checklist to extract (e.g., "Before Takeoff", "Preflight Inspection")

        Returns:
            List of checklist items with their mappings to CSV columns
        """
        logger.info(f"Reading manual from {manual_path}")
        manual_content = Path(manual_path).read_text(encoding="utf-8")

        # Create prompt to extract checklist
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert aviation systems analyst. Your task is to extract checklist items
from the SR-20 Airplane Flight Manual and map each item to the relevant telemetry data columns
that can be used to verify/validate that checklist item.

CRITICAL: The manual contains detailed instrument range tables with color-coded states:
- RED Arc/Bar: Warning ranges (dangerous/unsafe conditions)
- YELLOW Arc/Bar: Caution ranges (requires attention)
- GREEN Arc/Bar: Normal/acceptable ranges

For each checklist item, you MUST:
1. Find the checklist item name/description from the "{checklist_type}" section
2. Search the manual for related instrument range tables (look for sections like "SECTION 2: LIMITATIONS"
   which contains tables with Red/Yellow/Green arcs for various instruments)
3. Extract the exact numerical ranges for each state (Red, Yellow, Green) if available
4. Map to CSV telemetry columns that can validate this item

Focus on the "{checklist_type}" checklist section. Extract all items in that section.

Available CSV columns:
{columns}

Return the result as a JSON array where each item has:
- "step_id": unique identifier (e.g., "step_1", "step_2")
- "name": checklist item name
- "description": detailed description of what needs to be checked
- "expected_value": expected value or range (if applicable, null otherwise)
- "telemetry_columns": array of CSV column names that can validate this item
- "validation_logic": brief description of how to validate using telemetry data
- "states": object with color-coded ranges (if available):
  - "green": object with "min" and "max" values for normal range
  - "yellow": object with "min" and "max" values for caution range (can be null if not applicable)
  - "red": object with "min" and "max" values for warning range (can be null if not applicable)
  - "unit": unit of measurement (e.g., "gallons", "psi", "°F", "RPM", "volts")

Example format:
[
  {{
    "step_id": "step_1",
    "name": "Fuel Quantity",
    "description": "Confirm fuel quantity is adequate for flight",
    "expected_value": "10-28 gallons (green range)",
    "telemetry_columns": ["FQtyL", "FQtyR"],
    "validation_logic": "Sum of FQtyL and FQtyR should be in green range (10-28 gallons)",
    "states": {{
      "green": {{"min": 10, "max": 28}},
      "yellow": {{"min": 0, "max": 10}},
      "red": null,
      "unit": "gallons"
    }}
  }},
  {{
    "step_id": "step_2",
    "name": "Oil Pressure",
    "description": "Check engine oil pressure is within normal range",
    "expected_value": "55-95 psi (green range)",
    "telemetry_columns": ["E1 OilP"],
    "validation_logic": "E1 OilP should be between 55-95 psi for normal operation",
    "states": {{
      "green": {{"min": 55, "max": 95}},
      "yellow": {{"min": 25, "max": 55}},
      "red": {{"min": 0, "max": 25}},
      "unit": "psi"
    }}
  }}
]

IMPORTANT: Search the manual thoroughly for instrument range tables. Look for sections that list
Red Arc, Yellow Arc, and Green Arc ranges. Extract the exact numerical values from these tables.""",
                ),
                (
                    "user",
                    "Extract the {checklist_type} checklist from this manual. Pay special attention to instrument range tables with Red/Yellow/Green arcs:\n\n{manual}",
                ),
            ]
        )

        chain = prompt | self.llm | self.output_parser

        logger.info(f"Extracting {checklist_type} checklist...")
        # Include more content to capture LIMITATIONS section with instrument ranges
        # Try to include both the checklist section and the LIMITATIONS section
        manual_snippet = manual_content[:100000]  # Increased limit to include range tables

        # If we can find the LIMITATIONS section, include it (contains instrument range tables)
        limitations_start = manual_content.find("SECTION 2: LIMITATIONS")
        if limitations_start != -1:
            # Include LIMITATIONS section with instrument range tables (approximately 30000 chars)
            # This should capture the Powerplant Limitations tables with Red/Yellow/Green arcs
            limitations_section = manual_content[limitations_start : limitations_start + 30000]
            # Also include the checklist section from the beginning
            checklist_section = manual_content[:50000]
            manual_snippet = f"{checklist_section}\n\n=== INSTRUMENT RANGE TABLES FROM SECTION 2: LIMITATIONS ===\n{limitations_section}"

        response = chain.invoke(
            {
                "checklist_type": checklist_type,
                "manual": manual_snippet,
                "columns": ", ".join(self.CSV_COLUMNS),
            }
        )

        # Parse JSON response
        try:
            # Extract JSON from markdown code blocks if present
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()
            elif "```" in response:
                json_start = response.find("```") + 3
                json_end = response.find("```", json_start)
                response = response[json_start:json_end].strip()

            checklist = json.loads(response)
            logger.info(f"Extracted {len(checklist)} checklist items")
            return checklist
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response was: {response[:500]}")
            raise ValueError(f"Failed to parse checklist from LLM response: {e}") from e

    def save_checklist(self, checklist: List[Dict], output_path: str):
        """Save checklist to JSON file.

        Args:
            checklist: List of checklist items
            output_path: Path to save the JSON file
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(json.dumps(checklist, indent=2), encoding="utf-8")
        logger.info(f"Saved checklist to {output_path}")


def main():
    """Main function to run the checklist extraction."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Get OpenAI API key from environment
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize agent
    agent = ChecklistAgent(openai_api_key=api_key)

    # Path to manual
    manual_path = Path(__file__).parent.parent / "sr20.md"
    if not manual_path.exists():
        raise FileNotFoundError(f"Manual not found at {manual_path}")

    # Extract Before Takeoff checklist
    checklist = agent.extract_checklist(str(manual_path), checklist_type="Before Takeoff")

    # Save to output
    output_path = Path(__file__).parent.parent / "checklist_before_takeoff.json"
    agent.save_checklist(checklist, str(output_path))

    print(f"\nExtracted {len(checklist)} checklist items:")
    for item in checklist:
        print(f"  - {item['step_id']}: {item['name']}")
        print(f"    Columns: {', '.join(item.get('telemetry_columns', []))}")
        if "states" in item and item["states"]:
            states = item["states"]
            if states.get("green"):
                print(f"    Green: {states['green'].get('min')}-{states['green'].get('max')} {states.get('unit', '')}")
            if states.get("yellow"):
                print(
                    f"    Yellow: {states['yellow'].get('min')}-{states['yellow'].get('max')} {states.get('unit', '')}"
                )
            if states.get("red"):
                print(f"    Red: {states['red'].get('min')}-{states['red'].get('max')} {states.get('unit', '')}")


if __name__ == "__main__":
    main()
