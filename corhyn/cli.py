import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from datetime import datetime, timedelta
from typing import Optional
import sqlite3
import json
from pathlib import Path
import os

app = typer.Typer(help="Corhyn - Your Personal Task Management CLI")
console = Console()

# Database setup
DB_PATH = Path.home() / ".corhyn" / "tasks.db"
DB_PATH.parent.mkdir(exist_ok=True)

def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT,
            tags TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')
    conn.commit()
    conn.close()

@app.callback()
def main_callback():
    """Initialize the database before any command."""
    init_db()

@app.command()
def add(
    title: str,
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Task priority (low/medium/high)"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-dl"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t")
):
    """Add a new task to your list."""
    if priority and priority not in ["low", "medium", "high"]:
        console.print("[red]Priority must be one of: low, medium, high[/red]")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    c.execute('''
        INSERT INTO tasks (title, description, priority, deadline, created_at, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (title, description, priority, deadline, datetime.now().isoformat(), tags))

    conn.commit()
    conn.close()

    console.print(Panel(f"[green]Task added successfully: {title}[/green]"))

@app.command()
def list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending/completed)"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter by priority (low/medium/high)")
):
    """List all tasks with optional filtering."""
    if status and status not in ["pending", "completed"]:
        console.print("[red]Status must be one of: pending, completed[/red]")
        return

    if priority and priority not in ["low", "medium", "high"]:
        console.print("[red]Priority must be one of: low, medium, high[/red]")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    query = "SELECT * FROM tasks"
    params = []

    if status or priority:
        conditions = []
        if status:
            conditions.append("status = ?")
            params.append(status)
        if priority:
            conditions.append("priority = ?")
            params.append(priority)
        query += " WHERE " + " AND ".join(conditions)

    c.execute(query, params)
    tasks = c.fetchall()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Deadline")
    table.add_column("Status")

    for task in tasks:
        table.add_row(
            str(task[0]),
            task[1],
            task[3] or "N/A",
            task[4] or "N/A",
            task[5]
        )

    console.print(table)
    conn.close()

@app.command()
def start(task_id: int):
    """Start time tracking for a task."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Check if task exists
    c.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if not c.fetchone():
        console.print(f"[red]Task with ID {task_id} not found![/red]")
        return

    # Start time tracking
    c.execute('''
        INSERT INTO time_entries (task_id, start_time)
        VALUES (?, ?)
    ''', (task_id, datetime.now().isoformat()))

    conn.commit()
    conn.close()

    console.print(f"[green]Started time tracking for task {task_id}[/green]")

@app.command()
def stop():
    """Stop time tracking for the current task."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Get the latest time entry
    c.execute('''
        SELECT id, task_id, start_time FROM time_entries
        WHERE end_time IS NULL
        ORDER BY start_time DESC
        LIMIT 1
    ''')

    entry = c.fetchone()
    if not entry:
        console.print("[red]No active time tracking session found![/red]")
        return

    end_time = datetime.now()
    start_time = datetime.fromisoformat(entry[2])
    duration = int((end_time - start_time).total_seconds())

    c.execute('''
        UPDATE time_entries
        SET end_time = ?, duration = ?
        WHERE id = ?
    ''', (end_time.isoformat(), duration, entry[0]))

    conn.commit()
    conn.close()

    console.print(f"[green]Stopped time tracking. Duration: {duration} seconds[/green]")

@app.command()
def stats():
    """Show productivity statistics."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Get total tasks
    c.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = c.fetchone()[0]

    # Get completed tasks
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
    completed_tasks = c.fetchone()[0]

    # Get total time tracked
    c.execute("SELECT SUM(duration) FROM time_entries")
    total_time = c.fetchone()[0] or 0

    # Create statistics panel
    stats_text = f"""
    Total Tasks: {total_tasks}
    Completed Tasks: {completed_tasks}
    Completion Rate: {(completed_tasks/total_tasks*100 if total_tasks > 0 else 0):.1f}%
    Total Time Tracked: {timedelta(seconds=total_time)}
    """

    console.print(Panel(stats_text, title="Productivity Statistics", border_style="blue"))
    conn.close()

@app.command()
def pomodoro(
    minutes: int = typer.Option(25, "--minutes", "-m", help="Duration of the pomodoro session")
):
    """Start a pomodoro timer session."""
    console.print(f"[yellow]Starting a {minutes}-minute pomodoro session...[/yellow]")
    # TODO: Implement actual timer functionality
    console.print("[green]Pomodoro session completed![/green]")
