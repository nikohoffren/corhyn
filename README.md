# Corhyn CLI

A command-line tool for task management, time tracking, and productivity metrics.

## Features

- Task management with priorities and deadlines
- Time tracking for tasks
- Productivity metrics and analytics
- Terminal UI with rich formatting
- Data persistence using SQLite
- Tag-based organization
- Pomodoro timer integration

## Installation

### Prerequisites

- Python 3.8 or higher

#### Ubuntu/Debian

```bash
sudo apt update
sudo apt install python3-full
```

#### Fedora

```bash
sudo dnf install python3 python3-pip python3-venv
```

#### Arch Linux

```bash
sudo pacman -S python python-pip python-venv
```

#### macOS

```bash
brew install python
```

#### Windows

- Download and install Python from [python.org](https://www.python.org/downloads/)
- Ensure "Add Python to PATH" is checked during installation

### Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/corhyn.git
   cd corhyn
   ```

2. Create and activate a virtual environment:

   - **Linux/macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```

3. Install the package in development mode:
   ```bash
   pip install -e .
   ```

Note: Always activate the virtual environment before working on the project. You'll know you're in the virtual environment when you see `(venv)` at the beginning of your command prompt.

### Alternative Installation Using `install.sh`

For convenience, a shell script (`install.sh`) is provided in the root of the project. This script automates the setup process for Unix-like systems (Linux, macOS) by:

1. Creating a virtual environment
2. Activating the virtual environment
3. Installing the package in development mode

To use the script, run:

```bash
chmod +x install.sh
./install.sh
```

**Note:** This script is intended for Unix-like systems. Windows users should follow the manual installation instructions above.

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

# Search for tasks by keyword
corhyn search
```

### Time Tracking

```bash
# Start time tracking for a task
corhyn start TASK_ID

# Stop time tracking
corhyn stop

# List time tracking entries
corhyn time --list

# Add manual time entry
corhyn time --add-task-id TASK_ID --add-duration MINUTES

# Export time entries to CSV
corhyn time --export "time_entries.csv"

# Show time tracking report
corhyn time --report [OPTIONS]
Options:
  -p, --period TEXT    Time period for report (day/week/month/year) [default: week]
```

The time tracking report includes:

- Overview of tracked time and sessions
- Time spent per task
- Daily time tracking breakdown
- Export functionality for data analysis

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

## FAQ & Troubleshooting

### Where is my data stored?

All your tasks, tags, and time entries are stored in a local SQLite database at `~/.corhyn/tasks.db`.

### I updated the app and now I get a database error (e.g., missing column)

If you see errors about missing columns or tables after an update, your database schema may be out of date. You can reset the database by deleting the file at `~/.corhyn/tasks.db`. **Warning:** This will delete all your data.

### How do I reset all my data?

Delete the file at `~/.corhyn/tasks.db` and restart the CLI. A new, empty database will be created.

### I get an error about a missing command or option

Make sure you have the latest version of the code and have reinstalled the package with `pip install -e .` inside your virtual environment.

### How do I see all available commands?

Run `corhyn --help` to see all commands and options. You can also run `corhyn <command> --help` for details on a specific command.

### Can I use Corhyn on multiple devices?

Currently, Corhyn stores data locally and does not sync between devices. You can manually copy the `~/.corhyn/tasks.db` file if needed.

### How do I export my data?

Use `corhyn time --export <filename.csv>` to export your time tracking data. For tasks and tags, export is not yet implemented.
