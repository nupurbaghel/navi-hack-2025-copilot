#!/usr/bin/env python3
"""
Script to simulate frontend API calls for the checklist workflow.
Demonstrates how the frontend would interact with the backend API.
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Optional

import requests
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Try to import TTS, but make it optional
try:
    from aviation_hackathon_sf.text_to_speech import ElevenLabsTTS

    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    ElevenLabsTTS = None

# Try to import Textual for TUI, but make it optional
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container
    from textual.widgets import DataTable, Footer, Header, Static
    from textual.binding import Binding

    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False

console = Console()


class ChecklistTUI(App):
    """Textual TUI for checklist demo mode."""

    CSS = """
#checklist-header {
    height: 3;
    border: solid $primary;
    background: $surface;
}

#checklist-progress {
    height: 1;
    border: solid $primary;
    background: $surface;
}

#checklist-steps {
    height: 60%;
    border: solid $primary;
    background: $surface;
}

#checklist-details {
    height: 35%;
    border: solid $primary;
    background: $surface;
}

.status-success {
    color: green;
}

.status-caution {
    color: yellow;
}

.status-warning {
    color: orange;
}

.status-failed {
    color: red;
}

.status-pending {
    color: dimgrey;
}
"""

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, simulator: "ChecklistSimulator"):
        """Initialize TUI with simulator reference.

        Args:
            simulator: ChecklistSimulator instance
        """
        super().__init__()
        self.simulator = simulator
        self.current_step_index = 0
        self.step_statuses = {}  # step_id -> status dict

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(
            Static("Pre-Flight Checklist", id="checklist-header"),
            Static("Progress: 0/0", id="checklist-progress"),
            DataTable(id="checklist-steps"),
            Static("Details will appear here...", id="checklist-details"),
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        table = self.query_one("#checklist-steps", DataTable)
        table.add_columns("Step", "Name", "Status", "Message")
        table.cursor_type = "row"

        # Initialize with all steps
        for step in self.simulator.steps:
            step_id = step["step_id"]
            step_name = step.get("name", step_id)
            table.add_row("○", step_name, "Pending", "", key=step_id)

        self.update_progress()

        # Start the workflow as an async task
        self.current_step_index = 0
        self.call_later(self._run_workflow)

    def update_progress(self):
        """Update progress indicator."""
        total = len(self.simulator.steps)
        completed = sum(
            1 for s in self.step_statuses.values() if s.get("status") in ("success", "caution", "warning", "failed")
        )
        progress_widget = self.query_one("#checklist-progress", Static)
        progress_widget.update(f"Progress: {completed}/{total} steps completed")

    def update_step_status(self, step_id: str, status_data: Dict):
        """Update status for a specific step.

        Args:
            step_id: Step ID
            status_data: Status data from API
        """
        table = self.query_one("#checklist-steps", DataTable)
        details_widget = self.query_one("#checklist-details", Static)

        status = status_data.get("status", "unknown")
        message = status_data.get("message", "")
        error = status_data.get("error", "")

        # Update step icon and status
        status_icons = {
            "success": "✓",
            "caution": "⚠",
            "warning": "✗",
            "failed": "✗",
            "no_data": "?",
            "pending": "○",
            "running": "⟳",
        }

        icon = status_icons.get(status, "?")
        step_info = next((s for s in self.simulator.steps if s["step_id"] == step_id), None)
        step_name = step_info.get("name", step_id) if step_info else step_id

        # Update row - find row by key and update
        row_key = step_id
        try:
            # In Textual 6.x, we can access rows directly
            # Try to get row index from the row key
            row_index = None
            # Access rows via the internal structure
            if hasattr(table, "rows") and row_key in table.rows:
                # Get the row index
                row_keys = list(table.rows.keys())
                if row_key in row_keys:
                    row_index = row_keys.index(row_key)

            if row_index is not None:
                # Update cells using column index
                table.update_cell_at((row_index, 0), icon)  # Step column
                table.update_cell_at((row_index, 2), status.upper())  # Status column
                table.update_cell_at(
                    (row_index, 3), message[:50] + "..." if len(message) > 50 else message
                )  # Message column
        except (AttributeError, IndexError, KeyError, TypeError):
            # If update fails, row might not exist yet or API changed - this is OK
            pass

        # Update details
        details_text = f"[bold]{step_name}[/bold]\n\n"
        details_text += f"Status: [{self._get_status_style(status)}]{status.upper()}[/]\n"
        if message:
            details_text += f"\n{message}\n"
        if error:
            details_text += f"\n[red]Error: {error}[/red]\n"

        details_widget.update(details_text)

        # Store status
        self.step_statuses[step_id] = status_data
        self.update_progress()

        # Highlight current row - find row index and set cursor
        try:
            row_index = None
            if hasattr(table, "rows") and row_key in table.rows:
                row_keys = list(table.rows.keys())
                if row_key in row_keys:
                    row_index = row_keys.index(row_key)
            if row_index is not None:
                table.cursor_row = row_index
        except (AttributeError, IndexError, KeyError, TypeError):
            pass

    def _get_status_style(self, status: str) -> str:
        """Get style class for status.

        Args:
            status: Status string

        Returns:
            Style class name
        """
        status_styles = {
            "success": "green",
            "caution": "yellow",
            "warning": "orange",
            "failed": "red",
            "no_data": "dim",
            "pending": "dim",
        }
        return status_styles.get(status, "white")

    def action_quit(self) -> None:
        """Quit the app."""
        self.exit()

    def action_refresh(self) -> None:
        """Refresh the display."""
        self.update_progress()

    async def _run_workflow(self):
        """Run the checklist workflow asynchronously."""
        import asyncio

        # Process each step
        for step in self.simulator.steps:
            step_id = step["step_id"]
            step_name = step.get("name", step_id)

            # Update TUI to show current step is running
            self.update_step_status(step_id, {"status": "running", "message": "Processing..."})

            # Process step in executor to avoid blocking
            loop = asyncio.get_event_loop()
            status_data = await loop.run_in_executor(None, self.simulator.process_step, step_id)

            if status_data:
                # Update TUI with status
                self.update_step_status(step_id, status_data)

                # Check if we should continue
                status = status_data.get("status")
                if status in ("warning", "failed"):
                    self.simulator.failed_steps.append({"step_id": step_id, "step_name": step_name, "status": status})

                    if not self.simulator.continue_on_error:
                        # Show error in TUI
                        details_widget = self.query_one("#checklist-details", Static)
                        details_widget.update(
                            f"[red]⚠ Checklist blocked at step {step_id}. Status: {status}[/red]\n"
                            "[yellow]Press 'q' to quit[/yellow]"
                        )
                        return

                # Small delay for visual feedback
                await asyncio.sleep(1.0)

                # If no next step, we're done
                next_step_id = status_data.get("next_step_id")
                if not next_step_id:
                    break
            else:
                self.simulator.failed_steps.append({"step_id": step_id, "step_name": step_name, "status": "error"})
                self.update_step_status(step_id, {"status": "error", "message": "Failed to process step"})
                if not self.simulator.continue_on_error:
                    return

        # Complete checklist
        await self._complete_checklist()

    async def _complete_checklist(self):
        """Complete the checklist."""
        if self.simulator.checklist_id:
            # Use the public method to make request
            import asyncio

            loop = asyncio.get_event_loop()
            complete_result = await loop.run_in_executor(
                None,
                lambda: self.simulator._make_request(  # noqa: SLF001
                    "POST",
                    "/checklist/complete",
                    json={"checklist_id": self.simulator.checklist_id},
                ),
            )

            if complete_result:
                details_widget = self.query_one("#checklist-details", Static)
                if self.simulator.failed_steps:
                    summary = (
                        f"[yellow]⚠ Checklist completed with {len(self.simulator.failed_steps)} failed step(s)[/yellow]"
                    )
                else:
                    summary = "[green]✓ Checklist completed successfully![/green]"
                summary += f"\n[dim]Completed {complete_result.get('completed_steps', 0)}/{complete_result.get('total_steps', 0)} steps[/dim]"
                if not self.simulator.failed_steps:
                    summary += f"\n[green]{complete_result.get('message', '')}[/green]"

                details_widget.update(summary)


class ChecklistSimulator:
    """Simulates frontend checklist workflow."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        debug: bool = False,
        demo: bool = False,
        continue_on_error: bool = False,
        enable_tts: bool = False,
        telemetry_file: Optional[str] = None,
    ):
        """Initialize the simulator.

        Args:
            base_url: Base URL of the API
            debug: If True, show raw API responses
            demo: If True, show checklist items at each step with delays
            continue_on_error: If True, continue processing steps even if one fails
            enable_tts: If True, enable text-to-speech announcements
            telemetry_file: Optional path to telemetry CSV file to load
        """
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self.demo = demo
        self.continue_on_error = continue_on_error
        self.enable_tts = enable_tts
        self.telemetry_file = telemetry_file
        self.checklist_id: Optional[str] = None
        self.steps: list = []
        self.failed_steps: list = []

        # Initialize TTS if enabled
        self.tts: Optional[ElevenLabsTTS] = None
        if self.enable_tts:
            if not TTS_AVAILABLE:
                console.print("[yellow]Warning: TTS not available. Install dependencies: poetry install[/yellow]")
            elif not os.getenv("ELEVENLABS_API_KEY"):
                console.print("[yellow]Warning: ELEVENLABS_API_KEY not set. TTS disabled.[/yellow]")
            else:
                try:
                    self.tts = ElevenLabsTTS()
                    console.print("[green]✓ Text-to-Speech enabled[/green]")
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not initialize TTS: {e}[/yellow]")
                    self.tts = None

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """Make an API request and return the JSON response.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments to pass to requests

        Returns:
            JSON response as dict, or None if error
        """
        url = f"{self.base_url}{endpoint}"

        if self.debug:
            console.print(f"[dim]→ {method} {url}[/dim]")
            if kwargs.get("json"):
                console.print(f"[dim]  Body: {json.dumps(kwargs['json'], indent=2)}[/dim]")
            if kwargs.get("params"):
                console.print(f"[dim]  Params: {kwargs['params']}[/dim]")

        try:
            response = requests.request(method, url, **kwargs, timeout=10)
            response.raise_for_status()

            result = response.json()

            if self.debug:
                console.print(f"[dim]← Response ({response.status_code}):[/dim]")
                console.print(Panel(json.dumps(result, indent=2), title="API Response", border_style="dim"))

            return result
        except requests.exceptions.RequestException as e:
            console.print(f"[red]Error: {e}[/red]")
            if self.debug and hasattr(e, "response") and e.response is not None:
                try:
                    error_body = e.response.json()
                    console.print(Panel(json.dumps(error_body, indent=2), title="Error Response", border_style="red"))
                except:
                    console.print(f"[red]Error body: {e.response.text}[/red]")
            return None

    def start_checklist(self) -> bool:
        """Start a new checklist session.

        Returns:
            True if successful, False otherwise
        """
        console.print("\n[bold blue]Starting Checklist Session[/bold blue]")

        result = self._make_request("POST", "/checklist/start")

        if not result:
            return False

        self.checklist_id = result.get("checklist_id")
        self.steps = result.get("steps", [])

        console.print(f"[green]✓ Checklist started[/green]")
        console.print(f"[dim]Checklist ID: {self.checklist_id}[/dim]")
        console.print(f"[dim]Total steps: {len(self.steps)}[/dim]\n")

        return True

    def process_step(self, step_id: str) -> Optional[Dict]:
        """Process a single checklist step.

        Args:
            step_id: ID of the step to process

        Returns:
            Status response dict, or None if error
        """
        step_info = next((s for s in self.steps if s["step_id"] == step_id), None)
        if not step_info:
            console.print(f"[red]Step {step_id} not found[/red]")
            return None

        step_name = step_info.get("name", step_id)
        step_desc = step_info.get("description", "")

        if self.demo:
            console.print(f"\n[bold cyan]📋 Step: {step_name}[/bold cyan]")
            if step_desc:
                console.print(f"[dim]{step_desc}[/dim]")
            console.print("[yellow]Processing...[/yellow]")

            # Announce the item being checked if TTS is enabled
            if self.enable_tts and self.tts:
                try:
                    announcement = f"{step_name}, checking."
                    audio_data = self.tts.text_to_speech(announcement)
                    # Play in background (non-blocking)
                    self.tts.play_audio(audio_data)
                except Exception as e:
                    logger.warning(f"TTS failed for announcement: {e}")

            time.sleep(0.1)  # Simulate processing time

        # Call /checklist/next to start processing
        next_result = self._make_request(
            "GET",
            f"/checklist/next/{step_id}",
            params={"checklist_id": self.checklist_id} if self.checklist_id else None,
        )

        if not next_result:
            return None

        # Wait a bit for processing (if demo mode)
        if self.demo:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Validating telemetry data...", total=None)
                time.sleep(1.5)

        # Check status
        status_result = self._make_request(
            "GET",
            f"/checklist/status/{step_id}",
            params={"checklist_id": self.checklist_id} if self.checklist_id else None,
        )

        return status_result

    def _speak_checklist_item(self, step_name: str, status: str):
        """Speak checklist item using TTS if enabled.

        Args:
            step_name: Name of the checklist item
            status: Status of the item
        """
        if not self.tts:
            return

        try:
            # Map status to TTS announcement format
            if status == "success":
                text = f"{step_name}, check."
            elif status == "caution":
                text = f"Caution: {step_name} requires attention."
            elif status == "warning":
                text = f"Warning: {step_name} check failed."
            elif status == "failed":
                text = f"Alert: {step_name} check failed."
            else:
                text = f"{step_name}, checking."

            # Generate and play audio
            audio_data = self.tts.text_to_speech(text)
            self.tts.play_audio(audio_data)

        except Exception as e:
            # Don't fail the script if TTS fails
            logger.warning(f"TTS failed for {step_name}: {e}")

    def display_status(self, step_id: str, status_data: Dict):
        """Display the status of a checklist step.

        Args:
            step_id: ID of the step
            status_data: Status response from API
        """
        step_info = next((s for s in self.steps if s["step_id"] == step_id), None)
        step_name = step_info.get("name", step_id) if step_info else step_id

        status = status_data.get("status", "unknown")
        message = status_data.get("message", "")
        error = status_data.get("error")
        next_step_id = status_data.get("next_step_id")

        # Speak the checklist item if TTS is enabled
        if self.enable_tts:
            self._speak_checklist_item(step_name, status)

        # Determine status color and icon
        status_config = {
            "success": ("green", "✓", "PASSED"),
            "caution": ("yellow", "⚠", "CAUTION"),
            "warning": ("red", "✗", "WARNING"),
            "failed": ("red", "✗", "FAILED"),
            "no_data": ("dim", "?", "NO DATA"),
            "pending": ("dim", "○", "PENDING"),
            "running": ("blue", "⟳", "RUNNING"),
        }

        color, icon, label = status_config.get(status, ("white", "?", status.upper()))

        # Create status table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style=color, width=12)
        table.add_column()

        table.add_row(f"{icon} {label}", f"[bold]{step_name}[/bold]")
        if message:
            table.add_row("", f"[{color}]{message}[/{color}]")
        if error:
            table.add_row("", f"[red]Error: {error}[/red]")
        if next_step_id:
            table.add_row("", f"[dim]Next: {next_step_id}[/dim]")

        console.print(table)
        console.print()  # Empty line

    def load_telemetry(self, csv_path: str) -> bool:
        """Load a telemetry CSV file into the API.

        Args:
            csv_path: Path to the CSV file

        Returns:
            True if successful, False otherwise
        """
        console.print(f"[dim]Loading telemetry from: {csv_path}[/dim]")

        result = self._make_request(
            "POST",
            "/telemetry/load",
            json={"csv_path": csv_path},
        )

        if not result:
            console.print(f"[red]Failed to load telemetry from {csv_path}[/red]")
            return False

        if result.get("success"):
            rows = result.get("rows_loaded", 0)
            console.print(f"[green]✓ Telemetry loaded: {rows} rows from {result.get('csv_path', csv_path)}[/green]\n")
            return True
        else:
            console.print(f"[red]Failed to load telemetry: {result.get('message', 'Unknown error')}[/red]")
            return False

    def run(self):
        """Run the complete checklist workflow."""
        # Load telemetry file if specified
        if self.telemetry_file:
            if not self.load_telemetry(self.telemetry_file):
                console.print("[yellow]Warning: Failed to load telemetry file, continuing with default[/yellow]\n")

        # Start checklist
        if not self.start_checklist():
            console.print("[red]Failed to start checklist[/red]")
            sys.exit(1)

        # Use TUI if available and in demo mode
        if self.demo and TEXTUAL_AVAILABLE:
            self._run_with_tui()
        else:
            self._run_normal()

    def _run_with_tui(self):
        """Run checklist workflow with Textual TUI."""
        app = ChecklistTUI(self)
        app.simulator = self  # Store reference for async access

        # Run the TUI app (this will start the async event loop)
        app.run()

    def _run_normal(self):
        """Run checklist workflow in normal (non-TUI) mode."""
        if self.demo:
            console.print("[bold]Running in demo mode - showing each step with delays[/bold]\n")

        # Process each step
        for i, step in enumerate(self.steps, 1):
            step_id = step["step_id"]
            step_name = step.get("name", step_id)

            if not self.demo:
                console.print(f"[dim]Step {i}/{len(self.steps)}: {step_name}[/dim]")

            status_data = self.process_step(step_id)

            if status_data:
                self.display_status(step_id, status_data)

                # Check if we should continue
                status = status_data.get("status")
                if status in ("warning", "failed"):
                    self.failed_steps.append({"step_id": step_id, "step_name": step_name, "status": status})

                    if not self.continue_on_error:
                        console.print(f"[red]⚠ Checklist blocked at step {step_id}. " f"Status: {status}[/red]")
                        console.print("[yellow]Please address the issue before continuing.[/yellow]")
                        console.print("[dim]Use --continue-on-error to proceed despite errors.[/dim]\n")
                        break
                    else:
                        console.print(
                            f"[yellow]⚠ Step {step_id} failed, but continuing due to --continue-on-error flag[/yellow]\n"
                        )

                # If no next step, we're done
                next_step_id = status_data.get("next_step_id")
                if not next_step_id:
                    # If continuing on error and we're not at the last step, try to get next step manually
                    if self.continue_on_error and i < len(self.steps):
                        # Continue to next step in list
                        continue
                    break
            else:
                self.failed_steps.append({"step_id": step_id, "step_name": step_name, "status": "error"})
                console.print(f"[red]Failed to process step {step_id}[/red]\n")
                if not self.continue_on_error:
                    break

        # Show summary of failed steps if any
        if self.failed_steps:
            console.print("\n[bold yellow]Summary of Failed Steps:[/bold yellow]")
            for failed in self.failed_steps:
                console.print(
                    f"  [red]✗[/red] {failed.get('step_name', failed.get('step_id'))} "
                    f"({failed.get('step_id')}) - Status: {failed.get('status', 'error')}"
                )
            console.print()

        # Complete checklist
        if self.checklist_id:
            console.print("[bold blue]Completing Checklist[/bold blue]")
            complete_result = self._make_request(
                "POST",
                "/checklist/complete",
                json={"checklist_id": self.checklist_id},
            )

            if complete_result:
                if self.failed_steps:
                    console.print(
                        f"[yellow]⚠ Checklist completed with {len(self.failed_steps)} failed step(s)[/yellow]"
                    )
                else:
                    console.print("[green]✓ Checklist completed successfully![/green]")
                console.print(
                    f"[dim]Completed {complete_result.get('completed_steps', 0)}/"
                    f"{complete_result.get('total_steps', 0)} steps[/dim]"
                )
                if not self.failed_steps:
                    console.print(f"[green]{complete_result.get('message', '')}[/green]")
                console.print()
            else:
                console.print("[red]Failed to complete checklist[/red]\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Simulate frontend API calls for checklist workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run in normal mode
  python scripts/run_checklist.py

  # Run with debug output (shows API requests/responses)
  python scripts/run_checklist.py --debug

  # Run in demo mode (shows each step with delays)
  python scripts/run_checklist.py --demo

  # Run with both debug and demo
  python scripts/run_checklist.py --debug --demo

  # Continue even if steps fail (useful for testing)
  python scripts/run_checklist.py --continue-on-error

  # Combine all options
  python scripts/run_checklist.py --debug --demo --continue-on-error

  # Enable text-to-speech (co-pilot announcements)
  python scripts/run_checklist.py --demo --tts

  # Load different telemetry file
  python scripts/run_checklist.py --demo --telemetry flight-data/log_240505_132633_KHAF.csv

  # Combine options
  python scripts/run_checklist.py --demo --tts --telemetry flight-data/log_240505_132633_KHAF.csv

  # Use different API URL
  python scripts/run_checklist.py --url http://localhost:8080
        """,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show raw API requests and responses",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with step-by-step display and delays",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing steps even if one fails (useful for testing/demos)",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="Enable text-to-speech announcements (requires ELEVENLABS_API_KEY)",
    )
    parser.add_argument(
        "--telemetry",
        type=str,
        help="Path to telemetry CSV file to load (e.g., flight-data/log_240505_132633_KHAF.csv)",
    )

    args = parser.parse_args()

    simulator = ChecklistSimulator(
        base_url=args.url,
        debug=args.debug,
        demo=args.demo,
        continue_on_error=args.continue_on_error,
        enable_tts=args.tts,
        telemetry_file=args.telemetry,
    )

    try:
        simulator.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if args.debug:
            import traceback

            console.print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
