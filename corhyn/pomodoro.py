import time
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Callable
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
import os

console = Console()

class PomodoroTimer:
    def __init__(self):
        self.is_running = False
        self.current_session = 0
        self.total_sessions = 4
        self.work_duration = 25  # minutes
        self.short_break_duration = 5  # minutes
        self.long_break_duration = 15  # minutes

    def _play_notification(self):
        """Play a notification sound using system commands."""
        try:
            # Try different system commands for notification sound
            commands = [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["paplay", "/usr/share/sounds/freedesktop/stereo/notification.oga"],
                ["paplay", "/usr/share/sounds/ubuntu/notifications/Mallet.ogg"],
                ["spd-say", "Time's up!"],  # Fallback to speech synthesis
            ]

            for cmd in commands:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    break
                except (subprocess.SubprocessError, FileNotFoundError):
                    continue
        except Exception:
            pass  # Silently fail if sound can't be played

    def _format_time(self, seconds: int) -> str:
        """Format seconds into MM:SS format."""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _show_progress(self, duration: int, message: str):
        """Show a progress bar for the timer."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task(message, total=duration)
            while not progress.finished:
                progress.update(task, advance=1)
                time.sleep(1)

    def start_session(self, minutes: Optional[int] = None):
        """Start a Pomodoro session."""
        if minutes:
            self.work_duration = minutes

        self.is_running = True
        self.current_session = 0

        while self.is_running and self.current_session < self.total_sessions:
            # Work session
            self.current_session += 1
            console.print(f"\n[bold blue]Starting Pomodoro {self.current_session}/{self.total_sessions}[/bold blue]")
            console.print(f"[yellow]Focus time: {self.work_duration} minutes[/yellow]")

            self._show_progress(self.work_duration * 60, "Working...")
            self._play_notification()

            if self.current_session < self.total_sessions:
                # Short break
                console.print("\n[bold green]Time for a short break![/bold green]")
                self._show_progress(self.short_break_duration * 60, "Short break...")
                self._play_notification()
            else:
                # Long break after 4 sessions
                console.print("\n[bold green]Time for a long break![/bold green]")
                self._show_progress(self.long_break_duration * 60, "Long break...")
                self._play_notification()
                self.current_session = 0  # Reset for next round

    def stop(self):
        """Stop the Pomodoro timer."""
        self.is_running = False
