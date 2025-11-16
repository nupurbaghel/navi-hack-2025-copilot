#!/usr/bin/env python3
"""
Script to simulate frontend API calls for the checklist workflow.
Demonstrates how the frontend would interact with the backend API.
"""

import argparse
import json
import sys
import time
from typing import Dict, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class ChecklistSimulator:
    """Simulates frontend checklist workflow."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        debug: bool = False,
        demo: bool = False,
        continue_on_error: bool = False,
    ):
        """Initialize the simulator.

        Args:
            base_url: Base URL of the API
            debug: If True, show raw API responses
            demo: If True, show checklist items at each step with delays
            continue_on_error: If True, continue processing steps even if one fails
        """
        self.base_url = base_url.rstrip("/")
        self.debug = debug
        self.demo = demo
        self.continue_on_error = continue_on_error
        self.checklist_id: Optional[str] = None
        self.steps: list = []
        self.failed_steps: list = []

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
            time.sleep(1)  # Simulate processing time

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

    def run(self):
        """Run the complete checklist workflow."""
        # Start checklist
        if not self.start_checklist():
            console.print("[red]Failed to start checklist[/red]")
            sys.exit(1)

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

    args = parser.parse_args()

    simulator = ChecklistSimulator(
        base_url=args.url,
        debug=args.debug,
        demo=args.demo,
        continue_on_error=args.continue_on_error,
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
