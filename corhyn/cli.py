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
from .pomodoro import PomodoroTimer

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
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter by priority (low/medium/high)"),
    show_completed: bool = typer.Option(False, "--show-completed", help="Show completed tasks")
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

    conditions = []
    if not show_completed:
        conditions.append("status = 'pending'")
    if status:
        conditions.append("status = ?")
        params.append(status)
    if priority:
        conditions.append("priority = ?")
        params.append(priority)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY created_at DESC"

    c.execute(query, params)
    tasks = c.fetchall()

    if not tasks:
        console.print("[yellow]No tasks found matching the criteria.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Priority", justify="center")
    table.add_column("Deadline", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Created", justify="center")

    for task in tasks:
        # Format the status with color
        status_style = "green" if task[5] == "completed" else "yellow"
        status_text = f"[{status_style}]{task[5]}[/{status_style}]"

        # Format the priority with color
        priority_style = {
            "high": "red",
            "medium": "yellow",
            "low": "green"
        }.get(task[3], "dim")
        priority_text = f"[{priority_style}]{task[3] or 'N/A'}[/{priority_style}]"

        # Format the creation date
        created_at = datetime.fromisoformat(task[6])
        created_text = created_at.strftime("%Y-%m-%d %H:%M")

        table.add_row(
            str(task[0]),
            task[1],
            priority_text,
            task[4] or "N/A",
            status_text,
            created_text
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
    try:
        timer = PomodoroTimer()
        console.print(f"[yellow]Starting a {minutes}-minute pomodoro session...[/yellow]")
        console.print("[dim]Press Ctrl+C to stop the timer[/dim]")
        timer.start_session(minutes)
    except KeyboardInterrupt:
        timer.stop()
        console.print("\n[red]Pomodoro session stopped by user[/red]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@app.command()
def complete(task_id: int):
    """Mark a task as completed."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Check if task exists
    c.execute("SELECT id, title, status FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    if not task:
        console.print(f"[red]Task with ID {task_id} not found![/red]")
        return

    if task[2] == 'completed':
        console.print(f"[yellow]Task '{task[1]}' is already completed![/yellow]")
        return

    # Update task status
    c.execute('''
        UPDATE tasks
        SET status = 'completed', completed_at = ?
        WHERE id = ?
    ''', (datetime.now().isoformat(), task_id))

    conn.commit()
    conn.close()

    console.print(f"[green]Task '{task[1]}' marked as completed![/green]")

@app.command()
def status(
    task_id: int,
    status: str = typer.Argument(..., help="New status (pending/completed)")
):
    """Update task status."""
    if status not in ["pending", "completed"]:
        console.print("[red]Status must be one of: pending, completed[/red]")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Check if task exists
    c.execute("SELECT id, title FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    if not task:
        console.print(f"[red]Task with ID {task_id} not found![/red]")
        return

    # Update task status
    completed_at = datetime.now().isoformat() if status == 'completed' else None
    c.execute('''
        UPDATE tasks
        SET status = ?, completed_at = ?
        WHERE id = ?
    ''', (status, completed_at, task_id))

    conn.commit()
    conn.close()

    console.print(f"[green]Task '{task[1]}' status updated to {status}![/green]")

@app.command()
def edit(
    task_id: int,
    title: Optional[str] = typer.Option(None, "--title", "-t", help="New task title"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New task description"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="New task priority (low/medium/high)"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-dl", help="New task deadline"),
    tags: Optional[str] = typer.Option(None, "--tags", "-tg", help="New task tags")
):
    """Edit an existing task."""
    if priority and priority not in ["low", "medium", "high"]:
        console.print("[red]Priority must be one of: low, medium, high[/red]")
        return

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Check if task exists
    c.execute("SELECT id, title FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    if not task:
        console.print(f"[red]Task with ID {task_id} not found![/red]")
        return

    # Build update query dynamically based on provided fields
    update_fields = []
    params = []

    if title is not None:
        update_fields.append("title = ?")
        params.append(title)
    if description is not None:
        update_fields.append("description = ?")
        params.append(description)
    if priority is not None:
        update_fields.append("priority = ?")
        params.append(priority)
    if deadline is not None:
        update_fields.append("deadline = ?")
        params.append(deadline)
    if tags is not None:
        update_fields.append("tags = ?")
        params.append(tags)

    if not update_fields:
        console.print("[yellow]No changes provided. Use --help to see available options.[/yellow]")
        return

    # Add task_id to params
    params.append(task_id)

    # Execute update
    query = f'''
        UPDATE tasks
        SET {", ".join(update_fields)}
        WHERE id = ?
    '''
    c.execute(query, params)

    conn.commit()
    conn.close()

    console.print(f"[green]Task '{task[1]}' updated successfully![/green]")

@app.command()
def delete(
    task_id: int,
    force: bool = typer.Option(False, "--force", "-f", help="Force delete without confirmation")
):
    """Delete a task."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Check if task exists
    c.execute("SELECT id, title FROM tasks WHERE id = ?", (task_id,))
    task = c.fetchone()
    if not task:
        console.print(f"[red]Task with ID {task_id} not found![/red]")
        return

    if not force:
        # Ask for confirmation
        confirm = typer.confirm(f"Are you sure you want to delete task '{task[1]}'?")
        if not confirm:
            console.print("[yellow]Task deletion cancelled.[/yellow]")
            return

    # Delete the task
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    console.print(f"[green]Task '{task[1]}' deleted successfully![/green]")
