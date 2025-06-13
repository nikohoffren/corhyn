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
corhyn add "Task title" [OPTIONS]
Options:
  -d, --description TEXT    Task description
  -p, --priority TEXT      Task priority (low/medium/high)
  -dl, --deadline TEXT     Task deadline
  -t, --tags TEXT         Task tags

# List all tasks
corhyn list [OPTIONS]
Options:
  -s, --status TEXT       Filter by status (pending/completed)
  -p, --priority TEXT     Filter by priority (low/medium/high)
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
corhyn stats

# Start a pomodoro timer session
corhyn pomodoro [OPTIONS]
Options:
  -m, --minutes INTEGER   Duration of the pomodoro session (default: 25)
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

# Start time tracking for task ID 1
corhyn start 1

# Start a 30-minute pomodoro session
corhyn pomodoro --minutes 30
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
