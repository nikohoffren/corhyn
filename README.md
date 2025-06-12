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

```bash
# Clone the repository
git clone https://github.com/</yourusername>/corhyn.git
cd corhyn

# Install the package
pip install -e .
```

## Usage

```bash
# Add a new task
corhyn add "Complete project documentation" --priority high --deadline "2024-03-20"

# List all tasks
corhyn list

# Start time tracking for a task
corhyn start "Complete project documentation"

# Stop time tracking
corhyn stop

# View productivity metrics
corhyn stats

# Start a pomodoro session
corhyn pomodoro start
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
