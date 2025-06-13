# Corhyn CLI

A powerful command-line tool for task management, time tracking, and productivity metrics.

## Features

- Task management with priorities and deadlines
- Time tracking for tasks
- Productivity metrics and analytics
- Beautiful terminal UI with rich formatting
- Data persistence using SQLite
- Tag-based organization
- Pomodoro timer integration

## Installation

### Prerequisites

- Python 3.8 or higher
- `python3-full` package (for virtual environment support)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/</yourusername>/corhyn.git
cd corhyn
```

2. Create and activate a virtual environment:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

3. Install the package in development mode:

```bash
pip install -e .
```

Note: Always activate the virtual environment before working on the project. You'll know you're in the virtual environment when you see `(venv)` at the beginning of your command prompt.

## Usage

### Basic Commands

```bash
# Show help and available commands
corhyn --help

# Install shell completion
corhyn --install-completion
```

### Task Management

```bash
# Add a new task
corhyn add "Task title" --description "Task description" --priority high --deadline "2024-03-20" --tags "work,urgent"

# List all tasks
corhyn list

# List all tasks including completed ones
corhyn list --show-completed

# Filter tasks by status
corhyn list --status completed

# Filter tasks by priority
corhyn list --priority high

# Filter tasks by tags
corhyn list --tags "work,urgent"

# Complete a task
corhyn complete <task_id>

# Update task status
corhyn status TASK_ID STATUS

# Edit a task
corhyn edit <task_id> --title "New title" --description "New description" --priority medium --deadline "2024-03-21" --tags "work,important"

# Delete a task
corhyn delete <task_id>
```

### Time Tracking

```bash
# Start time tracking for a task
corhyn start TASK_ID

# Stop time tracking
corhyn stop
```

### Productivity

```bash
# View productivity statistics
corhyn stats [OPTIONS]
Options:
  -p, --period TEXT    Time period for stats (day/week/month/year) [default: week]
  -d, --detailed      Show detailed statistics

# Start a pomodoro timer session
corhyn pomodoro [OPTIONS]
Options:
  -m, --minutes INTEGER   Duration of the pomodoro session (default: 25)
```

The productivity statistics include:

- Overview of task completion and time tracking
- Priority-based task completion rates
- Most productive hours of the day
- Task completion trends over time
- Detailed analytics with the --detailed flag

### Tag Management

```bash
# List all tags
corhyn tags --list

# Create a new tag
corhyn tags --create "work"

# Rename a tag
corhyn tags --rename-id 1 --rename-name "new-tag-name"

# Set tag color
corhyn tags --color-id 1 --color-name "blue"

# Delete a tag
corhyn tags --delete 1

# View tag statistics
corhyn tags --stats
```

### Examples

```bash
# Add a high priority task with deadline and tags
corhyn add "Complete project documentation" \
  --priority high \
  --deadline "2024-03-20" \
  --tags "documentation,project"

# List all high priority tasks
corhyn list --priority high

# List all completed tasks
corhyn list --status completed

# Show all tasks including completed ones
corhyn list --show-completed

# Complete a task
corhyn complete 1

# Mark a task as pending
corhyn status 1 pending

# Mark a task as completed
corhyn status 1 completed

# Edit a task's title and priority
corhyn edit 1 \
  --title "Updated task title" \
  --priority medium

# Delete a task (with confirmation)
corhyn delete 1

# Force delete a task (without confirmation)
corhyn delete 1 --force
```

## Development

This project uses modern Python tooling:

- Poetry for dependency management
- Typer for CLI interface
- Rich for terminal formatting
- SQLAlchemy for data persistence
- Pydantic for data validation

## License

MIT License
