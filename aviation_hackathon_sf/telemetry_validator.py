"""
Telemetry data validator for checklist items.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger


class TelemetryValidator:
    """Validates flight telemetry data against checklist states."""

    def __init__(self, csv_path: str):
        """Initialize validator with CSV file path.

        Args:
            csv_path: Path to flight_data.csv file
        """
        self.csv_path = Path(csv_path)
        self._data: Optional[List[Dict]] = None
        self._load_data()

    def _load_data(self):
        """Load CSV data into memory."""
        if not self.csv_path.exists():
            logger.warning(f"CSV file not found at {self.csv_path}")
            self._data = []
            return

        try:
            with open(self.csv_path, "r", encoding="utf-8") as f:
                # Skip header comments (lines starting with #)
                lines = []
                for line in f:
                    stripped = line.strip()
                    if not stripped.startswith("#") and stripped:
                        lines.append(line)

                # Read CSV from remaining lines
                # The first non-comment line should be the header
                if len(lines) < 2:
                    logger.warning("CSV file has insufficient data")
                    self._data = []
                    return

                reader = csv.DictReader(lines)
                # Strip whitespace from column names and values
                all_rows = []
                for row in reader:
                    if any(row.values()):  # Filter empty rows
                        # Normalize column names by stripping whitespace
                        # Handle None values properly - convert to empty string before stripping
                        normalized_row = {
                            k.strip(): (v.strip() if isinstance(v, str) else ("" if v is None else str(v)))
                            for k, v in row.items()
                        }
                        all_rows.append(normalized_row)

                # Filter to pre-flight data: engine running but still on ground
                # Pre-flight checklist happens when engine is running but aircraft hasn't taken off
                # This matches the concept from FlightDataFilter but inverted - we want pre-flight WITH engine running
                self._data = []
                for row in all_rows:
                    # Get values and handle None/empty strings safely
                    alt_ind_val = row.get("AltInd", "")
                    rpm_val = row.get("E1 RPM", "")
                    fflow_val = row.get("E1 FFlow", "")
                    gndspd_val = row.get("GndSpd", "")

                    # Convert to string and strip, handling None values
                    alt_ind_str = (str(alt_ind_val) if alt_ind_val is not None else "").strip()
                    rpm_str = (str(rpm_val) if rpm_val is not None else "").strip()
                    fflow_str = (str(fflow_val) if fflow_val is not None else "").strip()
                    gndspd_str = (str(gndspd_val) if gndspd_val is not None else "").strip()

                    try:
                        # Parse altitude - on ground means low altitude (< 50 feet) or empty/0
                        if not alt_ind_str:
                            alt_ind = 0  # Empty means on ground
                        else:
                            alt_ind = float(alt_ind_str)

                        # Parse engine parameters
                        rpm = float(rpm_str) if rpm_str else 0
                        fflow = float(fflow_str) if fflow_str else 0
                        gndspd = float(gndspd_str) if gndspd_str else 0

                        # Pre-flight condition: on ground (low altitude) AND engine running
                        # Engine running means: RPM >= 100 (idle or above) AND (fuel flowing OR moving)
                        is_on_ground = alt_ind < 50  # Less than 50 feet = on ground
                        is_engine_running = rpm >= 100 and (fflow > 0 or gndspd >= 0.5)

                        if is_on_ground and is_engine_running:
                            # This is pre-flight with engine running - perfect for checklist validation
                            self._data.append(row)
                        elif is_on_ground and rpm == 0:
                            # Engine off but on ground - might be early pre-flight, include it
                            # (some checklist items can be checked before engine start)
                            self._data.append(row)
                    except (ValueError, TypeError):
                        # If we can't parse, check if AltInd is empty (conservative - include it)
                        if not alt_ind_str:
                            self._data.append(row)

                rows_filtered = len(all_rows) - len(self._data)
                logger.info(
                    f"Loaded {len(all_rows)} total rows, filtered to {len(self._data)} pre-flight rows "
                    f"(engine running on ground or engine off on ground, removed {rows_filtered} in-flight rows)"
                )
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            self._data = []

    def get_row_count(self) -> int:
        """Get the number of rows loaded.

        Returns:
            Number of rows in the dataset
        """
        return len(self._data) if self._data else 0

    def get_latest_row(self) -> Optional[Dict]:
        """Get the best row for pre-flight checklist validation.

        For pre-flight checklists, we want a row where:
        - Engine is running (RPM > 0)
        - Aircraft is on ground (low altitude)
        - Engine is at idle or low power (not at takeoff power)

        If no such row exists, falls back to the last row.

        Returns:
            Dictionary of column values, or None if no data
        """
        if not self._data or len(self._data) == 0:
            return None

        # Try to find a row with engine running at idle/low power (RPM 500-2000)
        # This is more appropriate for pre-flight checklist validation
        for row in reversed(self._data):  # Start from most recent and work backwards
            rpm_str = row.get("E1 RPM", "").strip()
            if rpm_str:
                try:
                    rpm = float(rpm_str)
                    # Engine running at idle or low power (not at takeoff)
                    if 500 <= rpm <= 2000:
                        return row
                except (ValueError, TypeError):
                    pass

        # Fall back to last row if no suitable row found
        return self._data[-1]

    def get_value(self, column_name: str, row: Optional[Dict] = None) -> Optional[float]:
        """Get a numeric value from a specific column.

        Args:
            column_name: Name of the CSV column (will be stripped of whitespace)
            row: Specific row to read from. If None, uses latest row.

        Returns:
            Numeric value, or None if not found/invalid
        """
        if row is None:
            row = self.get_latest_row()

        if not row:
            return None

        # Strip whitespace from column name for lookup (rows are already normalized)
        column_name = column_name.strip()
        value_str = row.get(column_name)

        if value_str is None:
            return None

        # Strip whitespace from value if it's a string
        if isinstance(value_str, str):
            value_str = value_str.strip()
            if not value_str:
                return None
        else:
            value_str = str(value_str).strip()
            if not value_str:
                return None

        try:
            return float(value_str)
        except (ValueError, TypeError):
            return None

    def validate_step(self, step: Dict, row: Optional[Dict] = None) -> Tuple[str, str, Optional[Dict]]:
        """Validate a checklist step against telemetry data.

        Args:
            step: Checklist step dictionary with states and telemetry_columns
            row: Specific row to validate against. If None, uses latest row.

        Returns:
            Tuple of (status, message, details)
            - status: "success", "caution", "warning", "failed", or "no_data"
            - message: Human-readable message
            - details: Dictionary with validation details (values, ranges, etc.)
        """
        if row is None:
            row = self.get_latest_row()

        if not row:
            return ("no_data", "No telemetry data available", None)

        telemetry_columns = step.get("telemetry_columns", [])
        states = step.get("states")

        if not telemetry_columns:
            # No telemetry columns to check (e.g., visual inspection)
            return ("success", "Visual check required - no telemetry validation", None)

        if not states:
            # No states defined - can't validate
            return ("failed", "No validation criteria defined for this step", None)

        # Get values from telemetry
        values = {}
        for col in telemetry_columns:
            val = self.get_value(col, row)
            values[col] = val

        # Check if we have any valid values
        valid_values = [v for v in values.values() if v is not None]
        if not valid_values:
            return ("no_data", f"No telemetry data available for columns: {', '.join(telemetry_columns)}", None)

        # Determine the value to check based on validation logic
        # For fuel quantity, sum left and right tanks
        if "Fuel Quantity" in step.get("name", "") or "FQtyL" in telemetry_columns:
            total_fuel = sum(v for v in values.values() if v is not None)
            check_value = total_fuel
            value_description = f"Total fuel: {total_fuel:.1f} {states.get('unit', '')}"
        else:
            # For single-column checks, use the first available value
            check_value = valid_values[0]
            value_description = f"{telemetry_columns[0]}: {check_value:.1f} {states.get('unit', '')}"

        # Check against states (red -> yellow -> green priority)
        details = {
            "value": check_value,
            "value_description": value_description,
            "columns_checked": telemetry_columns,
            "raw_values": values,
        }

        # Check red range first (most critical)
        red_range = states.get("red")
        if red_range:
            red_min = red_range.get("min")
            red_max = red_range.get("max")
            # Check if value is in red range
            in_red = False
            if red_min is not None and red_max is not None:
                in_red = red_min <= check_value <= red_max
            elif red_min is not None:
                # If only red_min is set, values >= red_min are in red range
                in_red = check_value >= red_min
            elif red_max is not None:
                # If only red_max is set, values <= red_max are in red range
                in_red = check_value <= red_max

            if in_red:
                details["range"] = "red"
                if red_min is not None and red_max is not None:
                    details["range_description"] = f"In red range ({red_min}-{red_max} {states.get('unit', '')})"
                elif red_min is not None:
                    details["range_description"] = f"At or above red minimum ({red_min} {states.get('unit', '')})"
                else:
                    details["range_description"] = f"At or below red maximum ({red_max} {states.get('unit', '')})"
                return ("warning", f"WARNING: {value_description} - In warning range", details)

        # Check yellow range
        yellow_range = states.get("yellow")
        if yellow_range:
            yellow_min = yellow_range.get("min")
            yellow_max = yellow_range.get("max")
            if yellow_min is not None and yellow_max is not None:
                if yellow_min <= check_value <= yellow_max:
                    details["range"] = "yellow"
                    details["range_description"] = (
                        f"In yellow range ({yellow_min}-{yellow_max} {states.get('unit', '')})"
                    )
                    return ("caution", f"CAUTION: {value_description} - Requires attention", details)
            elif yellow_min is not None:
                # If only yellow_min is set, values < yellow_min are in yellow range
                if check_value < yellow_min:
                    details["range"] = "yellow"
                    details["range_description"] = f"Below yellow minimum ({yellow_min} {states.get('unit', '')})"
                    return ("caution", f"CAUTION: {value_description} - Below normal minimum", details)
            elif yellow_max is not None:
                # If only yellow_max is set, values > yellow_max are in yellow range
                if check_value > yellow_max:
                    details["range"] = "yellow"
                    details["range_description"] = f"Above yellow maximum ({yellow_max} {states.get('unit', '')})"
                    return ("caution", f"CAUTION: {value_description} - Above normal maximum", details)

        # Check green range (normal operation)
        green_range = states.get("green")
        if green_range:
            green_min = green_range.get("min")
            green_max = green_range.get("max")
            if green_min is not None and green_max is not None:
                if green_min <= check_value <= green_max:
                    details["range"] = "green"
                    details["range_description"] = f"In green range ({green_min}-{green_max} {states.get('unit', '')})"
                    return ("success", f"OK: {value_description} - Within normal range", details)
            elif green_min is not None and check_value >= green_min:
                details["range"] = "green"
                details["range_description"] = f"Above green minimum ({green_min} {states.get('unit', '')})"
                return ("success", f"OK: {value_description} - Within normal range", details)
            elif green_max is not None and check_value <= green_max:
                details["range"] = "green"
                details["range_description"] = f"Below green maximum ({green_max} {states.get('unit', '')})"
                return ("success", f"OK: {value_description} - Within normal range", details)

        # If we get here, value doesn't match any defined range
        # Build a helpful error message explaining what went wrong
        unit = states.get("unit", "")
        range_descriptions = []

        if green_range:
            green_min = green_range.get("min")
            green_max = green_range.get("max")
            if green_min is not None and green_max is not None:
                range_descriptions.append(f"Green (normal): {green_min}-{green_max} {unit}")
            elif green_min is not None:
                range_descriptions.append(f"Green (normal): ≥{green_min} {unit}")
            elif green_max is not None:
                range_descriptions.append(f"Green (normal): ≤{green_max} {unit}")

        if yellow_range:
            yellow_min = yellow_range.get("min")
            yellow_max = yellow_range.get("max")
            if yellow_min is not None and yellow_max is not None:
                range_descriptions.append(f"Yellow (caution): {yellow_min}-{yellow_max} {unit}")
            elif yellow_min is not None:
                range_descriptions.append(f"Yellow (caution): <{yellow_min} {unit}")
            elif yellow_max is not None:
                range_descriptions.append(f"Yellow (caution): >{yellow_max} {unit}")

        if red_range:
            red_min = red_range.get("min")
            red_max = red_range.get("max")
            if red_min is not None and red_max is not None:
                range_descriptions.append(f"Red (warning): {red_min}-{red_max} {unit}")
            elif red_min is not None:
                range_descriptions.append(f"Red (warning): <{red_min} {unit}")
            elif red_max is not None:
                range_descriptions.append(f"Red (warning): >{red_max} {unit}")

        ranges_text = " | ".join(range_descriptions) if range_descriptions else "No ranges defined"

        # Determine what went wrong
        problem_description = f"Value {check_value:.2f} {unit} is outside all defined ranges."
        if green_range and green_range.get("max") is not None:
            green_max = green_range.get("max")
            if check_value > green_max:
                diff = check_value - green_max
                problem_description = (
                    f"Value {check_value:.2f} {unit} exceeds the maximum normal range of {green_max} {unit} "
                    f"by {diff:.2f} {unit}. "
                )
                if diff < 1.0:  # Small difference, might be acceptable
                    problem_description += "This is slightly above the normal range - verify fuel quantity manually."
                else:
                    problem_description += "This exceeds the safe operating range."
        elif green_range and green_range.get("min") is not None:
            green_min = green_range.get("min")
            if check_value < green_min:
                diff = green_min - check_value
                problem_description = (
                    f"Value {check_value:.2f} {unit} is below the minimum normal range of {green_min} {unit} "
                    f"by {diff:.2f} {unit}. "
                )
                if diff < 1.0:
                    problem_description += "This is slightly below the normal range - verify fuel quantity manually."
                else:
                    problem_description += "This is below the safe operating range."

        error_message = f"{problem_description} " f"Expected ranges: {ranges_text}"

        details["range"] = "unknown"
        details["expected_ranges"] = ranges_text
        details["problem"] = problem_description
        return ("failed", error_message, details)
