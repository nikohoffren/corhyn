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
import csv

app = typer.Typer(help="Corhyn - Your Personal Task Management CLI")
console = Console(force_terminal=True, color_system="auto")

# Database setup
DB_PATH = Path.home() / ".corhyn" / "tasks.db"
DB_PATH.parent.mkdir(exist_ok=True)

def init_db():
    """Initialize the SQLite database."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Create tasks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            priority TEXT,
            deadline TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        )
    ''')

    # Create time_entries table
    c.execute('''
        CREATE TABLE IF NOT EXISTS time_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            duration INTEGER,
            notes TEXT,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')

    # Create tags table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # Create task_tags relationship table
    c.execute('''
        CREATE TABLE IF NOT EXISTS task_tags (
            task_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (task_id, tag_id),
            FOREIGN KEY (task_id) REFERENCES tasks (id),
            FOREIGN KEY (tag_id) REFERENCES tags (id)
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

        # Safely access tag_names
        tag_names = task[8] if len(task) > 8 and task[8] else ""
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
def stats(
    period: str = typer.Option("week", "--period", "-p", help="Time period for stats (day/week/month/year)"),
    detailed: bool = typer.Option(False, "--detailed", "-d", help="Show detailed statistics")
):
    """View productivity statistics and analytics."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    # Calculate time period
    now = datetime.now()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "month":
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == "year":
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        console.print("[red]Invalid period. Use: day, week, month, or year[/red]")
        return

    # Basic statistics
    c.execute('''
        SELECT
            COUNT(*) as total_tasks,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
            AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100 as completion_rate
        FROM tasks
        WHERE created_at >= ?
    ''', (start_date.isoformat(),))
    basic_stats = c.fetchone()

    # Time tracking statistics
    c.execute('''
        SELECT
            COUNT(DISTINCT task_id) as tracked_tasks,
            SUM(duration) as total_time,
            AVG(duration) as avg_time
        FROM time_entries
        WHERE start_time >= ?
    ''', (start_date.isoformat(),))
    time_stats = c.fetchone()

    # Priority-based statistics
    c.execute('''
        SELECT
            priority,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            AVG(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) * 100 as completion_rate
        FROM tasks
        WHERE created_at >= ?
        GROUP BY priority
    ''', (start_date.isoformat(),))
    priority_stats = c.fetchall()

    # Most productive hours
    c.execute('''
        SELECT
            strftime('%H', start_time) as hour,
            COUNT(*) as sessions,
            SUM(duration) as total_time
        FROM time_entries
        WHERE start_time >= ?
        GROUP BY hour
        ORDER BY total_time DESC
        LIMIT 5
    ''', (start_date.isoformat(),))
    productive_hours = c.fetchall()

    # Task completion trends
    c.execute('''
        SELECT
            date(created_at) as date,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
        FROM tasks
        WHERE created_at >= ?
        GROUP BY date
        ORDER BY date
    ''', (start_date.isoformat(),))
    trends = c.fetchall()

    # Display basic statistics
    console.print(Panel.fit(
        f"[bold]Productivity Statistics for {period.capitalize()}[/bold]\n"
        f"Total Tasks: {basic_stats[0]}\n"
        f"Completed Tasks: {basic_stats[1]}\n"
        f"Completion Rate: {basic_stats[2]:.1f}%\n"
        f"Tracked Tasks: {time_stats[0]}\n"
        f"Total Time Spent: {timedelta(seconds=time_stats[1] or 0)}\n"
        f"Average Time per Task: {timedelta(seconds=time_stats[2] or 0)}",
        title="Overview"
    ))

    if detailed:
        # Priority-based statistics
        priority_table = Table(show_header=True, header_style="bold magenta")
        priority_table.add_column("Priority")
        priority_table.add_column("Total Tasks", justify="right")
        priority_table.add_column("Completed", justify="right")
        priority_table.add_column("Completion Rate", justify="right")

        for stat in priority_stats:
            priority_table.add_row(
                stat[0] or "N/A",
                str(stat[1]),
                str(stat[2]),
                f"{stat[3]:.1f}%"
            )

        console.print("\n[bold]Priority-based Statistics[/bold]")
        console.print(priority_table)

        # Most productive hours
        hours_table = Table(show_header=True, header_style="bold magenta")
        hours_table.add_column("Hour")
        hours_table.add_column("Sessions", justify="right")
        hours_table.add_column("Total Time", justify="right")

        for hour in productive_hours:
            hours_table.add_row(
                f"{hour[0]}:00",
                str(hour[1]),
                str(timedelta(seconds=hour[2]))
            )

        console.print("\n[bold]Most Productive Hours[/bold]")
        console.print(hours_table)

        # Task completion trends
        trends_table = Table(show_header=True, header_style="bold magenta")
        trends_table.add_column("Date")
        trends_table.add_column("Total Tasks", justify="right")
        trends_table.add_column("Completed", justify="right")
        trends_table.add_column("Completion Rate", justify="right")

        for trend in trends:
            completion_rate = (trend[2] / trend[1] * 100) if trend[1] > 0 else 0
            trends_table.add_row(
                trend[0],
                str(trend[1]),
                str(trend[2]),
                f"{completion_rate:.1f}%"
            )

        console.print("\n[bold]Task Completion Trends[/bold]")
        console.print(trends_table)

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

@app.command()
def time(
    list_entries: bool = typer.Option(False, "--list", "-l", help="List time tracking entries"),
    add_task_id: Optional[int] = typer.Option(None, help="Task ID for manual time entry"),
    add_duration: Optional[int] = typer.Option(None, help="Duration in minutes for manual time entry"),
    export: Optional[str] = typer.Option(None, "--export", "-e", help="Export time entries to CSV file"),
    report: bool = typer.Option(False, "--report", "-r", help="Show time tracking report"),
    period: str = typer.Option("week", "--period", "-p", help="Time period for report (day/week/month/year)")
):
    """Manage time tracking entries and reports."""
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    if list_entries or not any([list_entries, add_task_id, export, report]):
        # List time entries
        c.execute('''
            SELECT
                te.id,
                t.title,
                te.start_time,
                te.duration,
                te.notes
            FROM time_entries te
            JOIN tasks t ON te.task_id = t.id
            ORDER BY te.start_time DESC
        ''')
        entries = c.fetchall()

        if not entries:
            console.print("[yellow]No time entries found.[/yellow]")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Task")
        table.add_column("Start Time")
        table.add_column("Duration")
        table.add_column("Notes")

        for entry in entries:
            start_time = datetime.fromisoformat(entry[2])
            duration = timedelta(seconds=entry[3]) if entry[3] else "In Progress"
            table.add_row(
                str(entry[0]),
                entry[1],
                start_time.strftime("%Y-%m-%d %H:%M"),
                str(duration),
                entry[4] or ""
            )

        console.print(table)

    elif add_task_id is not None and add_duration is not None:
        # Add manual time entry
        duration_seconds = add_duration * 60

        # Verify task exists
        c.execute("SELECT title FROM tasks WHERE id = ?", (add_task_id,))
        task = c.fetchone()
        if not task:
            console.print(f"[red]Task with ID {add_task_id} not found![/red]")
            return

        # Add time entry
        c.execute('''
            INSERT INTO time_entries (task_id, start_time, duration, notes)
            VALUES (?, ?, ?, ?)
        ''', (add_task_id, datetime.now().isoformat(), duration_seconds, "Manual entry"))
        conn.commit()

        console.print(f"[green]Added {add_duration} minutes to task '{task[0]}'[/green]")

    elif export:
        # Export time entries to CSV
        c.execute('''
            SELECT
                t.title,
                te.start_time,
                te.duration,
                te.notes
            FROM time_entries te
            JOIN tasks t ON te.task_id = t.id
            ORDER BY te.start_time
        ''')
        entries = c.fetchall()

        if not entries:
            console.print("[yellow]No time entries to export.[/yellow]")
            return

        try:
            with open(export, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Task', 'Start Time', 'Duration (minutes)', 'Notes'])
                for entry in entries:
                    duration_minutes = entry[2] / 60 if entry[2] else 0
                    writer.writerow([
                        entry[0],
                        entry[1],
                        f"{duration_minutes:.1f}",
                        entry[3] or ""
                    ])
            console.print(f"[green]Time entries exported to {export}[/green]")
        except Exception as e:
            console.print(f"[red]Error exporting time entries: {str(e)}[/red]")

    elif report:
        # Calculate time period
        now = datetime.now()
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            console.print("[red]Invalid period. Use: day, week, month, or year[/red]")
            return

        # Get time tracking statistics
        c.execute('''
            SELECT
                COUNT(DISTINCT task_id) as tracked_tasks,
                SUM(duration) as total_time,
                AVG(duration) as avg_time,
                COUNT(*) as total_sessions
            FROM time_entries
            WHERE start_time >= ?
        ''', (start_date.isoformat(),))
        stats = c.fetchone()

        # Get time by task
        c.execute('''
            SELECT
                t.title,
                COUNT(*) as sessions,
                SUM(te.duration) as total_time
            FROM time_entries te
            JOIN tasks t ON te.task_id = t.id
            WHERE te.start_time >= ?
            GROUP BY t.id
            ORDER BY total_time DESC
        ''', (start_date.isoformat(),))
        task_stats = c.fetchall()

        # Get time by day
        c.execute('''
            SELECT
                date(start_time) as date,
                COUNT(*) as sessions,
                SUM(duration) as total_time
            FROM time_entries
            WHERE start_time >= ?
            GROUP BY date
            ORDER BY date
        ''', (start_date.isoformat(),))
        daily_stats = c.fetchall()

        # Display report
        console.print(Panel.fit(
            f"[bold]Time Tracking Report for {period.capitalize()}[/bold]\n"
            f"Tracked Tasks: {stats[0]}\n"
            f"Total Time: {timedelta(seconds=stats[1] or 0)}\n"
            f"Average Session: {timedelta(seconds=stats[2] or 0)}\n"
            f"Total Sessions: {stats[3]}",
            title="Overview"
        ))

        # Time by task
        task_table = Table(show_header=True, header_style="bold magenta")
        task_table.add_column("Task")
        task_table.add_column("Sessions", justify="right")
        task_table.add_column("Total Time", justify="right")

        for stat in task_stats:
            task_table.add_row(
                stat[0],
                str(stat[1]),
                str(timedelta(seconds=stat[2]))
            )

        console.print("\n[bold]Time by Task[/bold]")
        console.print(task_table)

        # Time by day
        daily_table = Table(show_header=True, header_style="bold magenta")
        daily_table.add_column("Date")
        daily_table.add_column("Sessions", justify="right")
        daily_table.add_column("Total Time", justify="right")

        for stat in daily_stats:
            daily_table.add_row(
                stat[0],
                str(stat[1]),
                str(timedelta(seconds=stat[2]))
            )

        console.print("\n[bold]Time by Day[/bold]")
        console.print(daily_table)

    conn.close()

@app.command()
#find task by keyword
def search():
    """Search for a task by entering the keyword"""

    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()

    keyword = input('Keyword of the task:- ').strip()
    query = "select * from tasks where title like '%s'"%('%'+keyword.lower()+'%')
    c.execute(query)

    data = c.fetchall()
    if not data:
        console.print(f"[yellow]No task found with keyword:- {keyword}[/yellow]")
        return 
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    table.add_column("Priority", justify="center")
    table.add_column("Deadline", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Tags")
    table.add_column("Created", justify="center")

    for task in data:
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

        # Safely access tag_names
        tag_names = task[8] if len(task) > 8 and task[8] else ""
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