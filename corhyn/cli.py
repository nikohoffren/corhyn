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

    # Create tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT,
            completed_at TEXT
        )
    ''')

    # Create tags table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            color TEXT,
            created_at TEXT
        )
    ''')

    # Create task-tag relationship table
    c.execute('''
        CREATE TABLE IF NOT EXISTS task_tags (
            task_id INTEGER,
            tag_id INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
            PRIMARY KEY (task_id, tag_id)
        )
    ''')

    # Create time entries table
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

    # Insert task
    c.execute('''
        INSERT INTO tasks (title, description, priority, deadline, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (title, description, priority, deadline, datetime.now().isoformat()))

    task_id = c.lastrowid

    # Handle tags
    if tags:
        tag_ids = _get_or_create_tags(c, tags)
        for tag_id in tag_ids:
            c.execute('''
                INSERT INTO task_tags (task_id, tag_id)
                VALUES (?, ?)
            ''', (task_id, tag_id))

    conn.commit()
    conn.close()

    console.print(Panel(f"[green]Task added successfully: {title}[/green]"))

@app.command()
def list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending/completed)"),
    priority: Optional[str] = typer.Option(None, "--priority", "-p", help="Filter by priority (low/medium/high)"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Filter by tags (comma-separated)"),
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

    query = """
        SELECT DISTINCT t.*, GROUP_CONCAT(tg.name) as tag_names
        FROM tasks t
        LEFT JOIN task_tags tt ON t.id = tt.task_id
        LEFT JOIN tags tg ON tt.tag_id = tg.id
    """
    params = []

    conditions = []
    if not show_completed:
        conditions.append("t.status = 'pending'")
    if status:
        conditions.append("t.status = ?")
        params.append(status)
    if priority:
        conditions.append("t.priority = ?")
        params.append(priority)
    if tags:
        tag_list = [tag.strip() for tag in tags.split(',')]
        placeholders = ','.join(['?'] * len(tag_list))
        conditions.append(f"""
            t.id IN (
                SELECT task_id
                FROM task_tags tt
                JOIN tags tg ON tt.tag_id = tg.id
                WHERE tg.name IN ({placeholders})
                GROUP BY task_id
                HAVING COUNT(DISTINCT tg.name) = ?
            )
        """)
        params.extend(tag_list)
        params.append(len(tag_list))

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " GROUP BY t.id ORDER BY t.created_at DESC"

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
    table.add_column("Tags")
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

        # Format tags
        tag_names = task[8] or ""
        tag_text = ", ".join(f"[blue]{tag}[/blue]" for tag in tag_names.split(',') if tag)

        table.add_row(
            str(task[0]),
            task[1],
            priority_text,
            task[4] or "N/A",
            status_text,
            tag_text,
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

@app.command()
def tags(
    list_tags: bool = typer.Option(False, "--list", "-l", help="List all tags"),
    create: Optional[str] = typer.Option(None, "--create", "-c", help="Create a new tag"),
    delete: Optional[int] = typer.Option(None, "--delete", "-d", help="Delete a tag by ID"),
    rename_id: Optional[int] = typer.Option(None, help="Tag ID to rename"),
    rename_name: Optional[str] = typer.Option(None, help="New name for the tag"),
    color_id: Optional[int] = typer.Option(None, help="Tag ID to set color for"),
    color_name: Optional[str] = typer.Option(None, help="New color for the tag"),
    stats: bool = typer.Option(False, "--stats", "-s", help="Show tag statistics")
):
    """Manage tags."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    if list_tags or not any([list_tags, create, delete, rename_id, color_id, stats]):
        # List all tags
        c.execute('''
            SELECT t.id, t.name, t.color, COUNT(tt.task_id) as task_count
            FROM tags t
            LEFT JOIN task_tags tt ON t.id = tt.tag_id
            GROUP BY t.id
            ORDER BY t.name
        ''')
        tags = c.fetchall()

        if not tags:
            console.print("[yellow]No tags found.[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name")
        table.add_column("Color")
        table.add_column("Tasks", justify="right")

        for tag in tags:
            color_style = tag[2] or "dim"
            table.add_row(
                str(tag[0]),
                f"[{color_style}]{tag[1]}[/{color_style}]",
                tag[2] or "N/A",
                str(tag[3])
            )

        console.print(table)

    elif create:
        # Create new tag
        try:
            c.execute('''
                INSERT INTO tags (name, created_at)
                VALUES (?, ?)
            ''', (create, datetime.now().isoformat()))
            conn.commit()
            console.print(f"[green]Tag '{create}' created successfully![/green]")
        except sqlite3.IntegrityError:
            console.print(f"[red]Tag '{create}' already exists![/red]")

    elif delete is not None:
        # Delete tag
        c.execute("SELECT name FROM tags WHERE id = ?", (delete,))
        tag = c.fetchone()
        if not tag:
            console.print(f"[red]Tag with ID {delete} not found![/red]")
            return

        if typer.confirm(f"Are you sure you want to delete tag '{tag[0]}'?"):
            c.execute("DELETE FROM tags WHERE id = ?", (delete,))
            conn.commit()
            console.print(f"[green]Tag '{tag[0]}' deleted successfully![/green]")

    elif rename_id is not None and rename_name is not None:
        # Rename tag
        c.execute("SELECT name FROM tags WHERE id = ?", (rename_id,))
        tag = c.fetchone()
        if not tag:
            console.print(f"[red]Tag with ID {rename_id} not found![/red]")
            return

        try:
            c.execute("UPDATE tags SET name = ? WHERE id = ?", (rename_name, rename_id))
            conn.commit()
            console.print(f"[green]Tag '{tag[0]}' renamed to '{rename_name}'![/green]")
        except sqlite3.IntegrityError:
            console.print(f"[red]Tag '{rename_name}' already exists![/red]")

    elif color_id is not None and color_name is not None:
        # Set tag color
        c.execute("SELECT name FROM tags WHERE id = ?", (color_id,))
        tag = c.fetchone()
        if not tag:
            console.print(f"[red]Tag with ID {color_id} not found![/red]")
            return

        c.execute("UPDATE tags SET color = ? WHERE id = ?", (color_name, color_id))
        conn.commit()
        console.print(f"[green]Tag '{tag[0]}' color updated to '{color_name}'![/green]")

    elif stats:
        # Show tag statistics
        c.execute('''
            SELECT
                t.name,
                COUNT(DISTINCT tt.task_id) as task_count,
                COUNT(DISTINCT CASE WHEN tk.status = 'completed' THEN tt.task_id END) as completed_tasks,
                SUM(CASE WHEN te.duration IS NOT NULL THEN te.duration ELSE 0 END) as total_time
            FROM tags t
            LEFT JOIN task_tags tt ON t.id = tt.tag_id
            LEFT JOIN tasks tk ON tt.task_id = tk.id
            LEFT JOIN time_entries te ON tk.id = te.task_id
            GROUP BY t.id
            ORDER BY task_count DESC
        ''')
        stats = c.fetchall()

        if not stats:
            console.print("[yellow]No tag statistics available.[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Tag")
        table.add_column("Tasks", justify="right")
        table.add_column("Completed", justify="right")
        table.add_column("Time Spent", justify="right")

        for stat in stats:
            time_spent = timedelta(seconds=stat[3]) if stat[3] else "0:00:00"
            table.add_row(
                stat[0],
                str(stat[1]),
                str(stat[2]),
                str(time_spent)
            )

        console.print(table)

    conn.close()

def _get_or_create_tags(cursor, tag_names: str) -> list:
    """Get or create tags from a comma-separated string of tag names."""
    if not tag_names:
        return []

    tag_ids = []
    for tag_name in tag_names.split(','):
        tag_name = tag_name.strip()
        if not tag_name:
            continue

        # Try to get existing tag
        cursor.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
        tag = cursor.fetchone()

        if tag:
            tag_ids.append(tag[0])
        else:
            # Create new tag
            cursor.execute('''
                INSERT INTO tags (name, created_at)
                VALUES (?, ?)
            ''', (tag_name, datetime.now().isoformat()))
            tag_ids.append(cursor.lastrowid)

    return tag_ids
