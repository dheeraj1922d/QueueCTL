# QueueCTL - Production-Grade CLI Job Queue System

[![Python](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A robust, production-ready CLI-based background job queue system with worker processes, automatic retries using exponential backoff, and Dead Letter Queue (DLQ) support.

## 🎯 Features

- ✅ **CLI-Based Interface** - Complete command-line control
- ✅ **Background Job Processing** - Execute shell commands as background jobs
- ✅ **Multi-Worker Support** - Run multiple workers in parallel
- ✅ **Persistent Storage** - SQLite-based storage survives restarts
- ✅ **Automatic Retries** - Exponential backoff retry mechanism
- ✅ **Dead Letter Queue** - Manage permanently failed jobs
- ✅ **Job Locking** - Prevent duplicate job execution
- ✅ **Graceful Shutdown** - Workers finish current jobs before stopping
- ✅ **Configuration Management** - Configurable retry and backoff settings
- ✅ **Comprehensive Status** - Real-time monitoring of jobs and workers

## 📋 Table of Contents

- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Usage Examples](#-usage-examples)
- [CLI Commands](#-cli-commands)
- [Job Lifecycle](#-job-lifecycle)
- [Configuration](#-configuration)
- [Testing](#-testing)
- [Assumptions & Trade-offs](#-assumptions--trade-offs)

## 🚀 Installation

### Prerequisites

- Python 3.7 or higher
- pip (Python package installer)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/dheeraj1922d/QueueCTL.git
cd QueueCTL
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install QueueCTL:
```bash
pip install -e .
```

4. Verify installation:
```bash
queuectl --help
```

## ⚡ Quick Start

```bash
# 1. Check system status
queuectl status

# 2. Enqueue a job
queuectl enqueue '{"id":"job1","command":"echo Hello World"}'

# 3. Start workers
queuectl worker start --count 2

# 4. Monitor progress
queuectl status

# 5. View completed jobs
queuectl list --state completed

# 6. Stop workers when done
queuectl worker stop
```

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────┐
│                      QueueCTL CLI                        │
│  (User Interface - Command Processing & Display)        │
└─────────────┬───────────────────────────────────────────┘
              │
              ├──────┐
              │      │
        ┌─────▼──┐ ┌─▼────────┐
        │ Worker │ │ Worker   │  ... (Multiple Workers)
        │   #1   │ │   #2     │
        └─────┬──┘ └─┬────────┘
              │      │
              └──────┴───────────────┐
                                     │
                        ┌────────────▼────────────┐
                        │   Storage Layer         │
                        │   (SQLite Database)     │
                        │                         │
                        │  • Jobs Table           │
                        │  • Config Table         │
                        │  • Job Locking          │
                        └─────────────────────────┘
```

### Data Flow

1. **Job Submission**: User enqueues jobs via CLI → Stored in SQLite
2. **Job Acquisition**: Worker acquires job with atomic locking
3. **Job Execution**: Worker executes command in subprocess
4. **Result Handling**:
   - **Success**: Job marked as completed
   - **Failure**: Job scheduled for retry with exponential backoff
   - **Max Retries Exceeded**: Job moved to Dead Letter Queue

### Job States

| State | Description |
|-------|-------------|
| `pending` | Waiting to be picked up by a worker |
| `processing` | Currently being executed by a worker |
| `completed` | Successfully executed |
| `failed` | Failed but retryable (scheduled for retry) |
| `dead` | Permanently failed (in DLQ) |

### Persistence Strategy

- **Database**: SQLite for ACID compliance and simplicity
- **Thread Safety**: Connection pooling with thread-local storage
- **Atomic Operations**: Database-level locking for job acquisition
- **Crash Recovery**: Jobs in `processing` state released on startup

## 📚 Usage Examples

### Basic Job Enqueuing

```bash
# Simple command
queuectl enqueue '{"id":"hello","command":"echo Hello"}'

# Command with custom retry limit
queuectl enqueue '{"id":"custom","command":"./script.sh","max_retries":5}'

# From JSON file
queuectl enqueue '@job_definition.json'
```

### Worker Management

```bash
# Start single worker
queuectl worker start

# Start multiple workers
queuectl worker start --count 3

# Check worker status
queuectl worker status

# Stop workers gracefully
queuectl worker stop

# Force stop workers
queuectl worker stop --force
```

### Job Monitoring

```bash
# Overall system status
queuectl status

# List all jobs
queuectl list

# List jobs by state
queuectl list --state pending
queuectl list --state completed
queuectl list --state failed

# Get specific job details
queuectl get job1

# Limit results
queuectl list --limit 10
```

### Dead Letter Queue (DLQ) Operations

```bash
# List failed jobs in DLQ
queuectl dlq list

# Retry a specific job
queuectl dlq retry job1

# Retry with reset attempts
queuectl dlq retry job1 --reset-attempts

# Clear all DLQ jobs
queuectl dlq clear
```

### Configuration Management

```bash
# Show current configuration
queuectl config show

# Set maximum retries
queuectl config set max-retries 5

# Set backoff base (exponential)
queuectl config set backoff-base 3

# Set job timeout (seconds)
queuectl config set job-timeout 600
```

### Data Management

```bash
# Clear completed jobs
queuectl clear --state completed

# Clear all jobs (with confirmation)
queuectl clear
```

## 📖 CLI Commands

### Core Commands

| Command | Description |
|---------|-------------|
| `queuectl enqueue <json>` | Add a new job to the queue |
| `queuectl status` | Show system status and job counts |
| `queuectl list [--state STATE]` | List jobs, optionally filtered |
| `queuectl get <job_id>` | Get detailed job information |
| `queuectl clear [--state STATE]` | Delete jobs from queue |

### Worker Commands

| Command | Description |
|---------|-------------|
| `queuectl worker start [--count N]` | Start N worker processes |
| `queuectl worker stop [--force]` | Stop all workers |
| `queuectl worker status` | Show running worker details |

### DLQ Commands

| Command | Description |
|---------|-------------|
| `queuectl dlq list` | List all jobs in DLQ |
| `queuectl dlq retry <job_id>` | Retry a failed job |
| `queuectl dlq clear` | Clear all DLQ jobs |

### Config Commands

| Command | Description |
|---------|-------------|
| `queuectl config show` | Display current configuration |
| `queuectl config set <key> <value>` | Update configuration value |

## 🔄 Job Lifecycle

```
┌──────────┐
│ Enqueued │
└────┬─────┘
     │
     ▼
┌─────────┐
│ PENDING │◄──────────┐
└────┬────┘           │
     │                │ Retry scheduled
     │ Worker picks   │ (exponential backoff)
     ▼                │
┌────────────┐    ┌───┴────┐
│ PROCESSING │───►│ FAILED │
└────┬───────┘    └───┬────┘
     │                │
     │ Success        │ Max retries
     ▼                ▼
┌───────────┐    ┌──────┐
│ COMPLETED │    │ DEAD │ (DLQ)
└───────────┘    └──────┘
```

### Retry Mechanism

**Exponential Backoff Formula**: `delay = base ^ attempts`

Example with `backoff_base = 2`:
- Attempt 1 fails → retry in 2^1 = 2 seconds
- Attempt 2 fails → retry in 2^2 = 4 seconds
- Attempt 3 fails → retry in 2^3 = 8 seconds
- Max retries (3) exceeded → move to DLQ

### Concurrency & Locking

- **Job Acquisition**: Atomic database transaction
- **Lock Mechanism**: Jobs marked with `locked_by` worker ID
- **Stale Lock Recovery**: Locks older than 5 minutes auto-released
- **Duplicate Prevention**: One job processed by one worker only

## ⚙️ Configuration

### Default Settings

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max-retries` | 3 | Maximum retry attempts |
| `backoff-base` | 2 | Exponential backoff base |
| `worker-poll-interval` | 1.0 | Seconds between job polls |
| `job-timeout` | 300 | Job execution timeout (seconds) |

### Modifying Configuration

```bash
# Increase max retries
queuectl config set max-retries 5

# Change backoff base for faster/slower retries
queuectl config set backoff-base 3

# Adjust worker polling
queuectl config set worker-poll-interval 2.0

# Set job timeout
queuectl config set job-timeout 600
```

**Note**: Configuration changes require worker restart to take effect.

## 🧪 Testing

### Automated Test Suite

Run the comprehensive test script:

```bash
chmod +x test_queuectl.sh
./test_queuectl.sh
```

The test suite validates:
- ✅ Job enqueuing and retrieval
- ✅ Worker start/stop functionality
- ✅ Job execution (success/failure)
- ✅ Retry mechanism with backoff
- ✅ DLQ operations
- ✅ Data persistence across restarts
- ✅ Configuration management
- ✅ Concurrent job processing

### Manual Testing Scenarios

#### Test 1: Basic Job Execution
```bash
queuectl enqueue '{"id":"test1","command":"echo Test"}'
queuectl worker start
sleep 2
queuectl list --state completed
queuectl worker stop
```

#### Test 2: Retry Mechanism
```bash
queuectl enqueue '{"id":"fail-test","command":"exit 1","max_retries":2}'
queuectl worker start
# Watch retry attempts with exponential backoff
queuectl status
# After ~6 seconds (2^1 + 2^2), check DLQ
sleep 8
queuectl dlq list
queuectl worker stop
```

#### Test 3: Multiple Workers
```bash
# Enqueue multiple jobs
for i in {1..10}; do
  queuectl enqueue "{\"id\":\"job$i\",\"command\":\"sleep 2 && echo Job $i\"}"
done

# Start multiple workers and observe parallel processing
queuectl worker start --count 3
queuectl worker status
queuectl status
```

#### Test 4: Data Persistence
```bash
queuectl enqueue '{"id":"persist","command":"echo Persist"}'
queuectl status
# Data persists in queuectl.db
# Verify by checking again
queuectl get persist
```

## 🤔 Assumptions & Trade-offs

### Assumptions

1. **Execution Environment**: Workers run on same machine as CLI
2. **Shell Commands**: All job commands are shell-executable
3. **Storage**: Single SQLite database file sufficient for use case
4. **Concurrency**: Worker count limited by system resources
5. **Command Output**: stdout/stderr handled via subprocess, not stored

### Trade-offs

| Decision | Rationale | Alternative |
|----------|-----------|-------------|
| **SQLite vs Distributed Queue** | Simplicity, ACID guarantees, single-machine deployment | Redis/RabbitMQ for distributed systems |
| **Subprocess vs Thread Pool** | Isolation, security, handles any command | Thread pool for Python-only tasks |
| **File-based PID tracking** | Simple, no additional dependencies | Process manager like systemd |
| **Polling vs Events** | Simple implementation, predictable behavior | Event-driven for lower latency |
| **No job output storage** | Reduced storage overhead | Store outputs for audit trail |

### Limitations

- **Single Machine**: Not designed for distributed deployment
- **No Job Priority**: All jobs FIFO within state
- **No Scheduled Jobs**: No built-in cron-like scheduling
- **Basic Monitoring**: No built-in metrics/alerting
- **Command-only**: Cannot execute Python functions directly

### Potential Enhancements

- [ ] Job priority queues
- [ ] Scheduled/delayed job execution (`run_at` field)
- [ ] Job output/log storage
- [ ] Web dashboard for monitoring
- [ ] Metrics and statistics (success rate, avg execution time)
- [ ] Job dependencies (DAG execution)
- [ ] Distributed mode with Redis backend
- [ ] Webhook notifications on job completion

## 📁 Project Structure

```
QueueCTL/
├── queuectl/
│   ├── __init__.py        # Package initialization
│   ├── models.py          # Data models (Job, Config)
│   ├── storage.py         # SQLite persistence layer
│   ├── worker.py          # Worker process implementation
│   ├── manager.py         # Worker process manager
│   └── cli.py             # CLI interface (Click-based)
├── test_queuectl.sh       # Automated test suite
├── requirements.txt       # Python dependencies
├── setup.py               # Package installation script
├── README.md              # This file
└── .gitignore             # Git ignore patterns
```

## 🔧 Development

### Running from Source

```bash
# Install in development mode
pip install -e .

# Run CLI directly
python -m queuectl.cli --help

# Or use installed command
queuectl --help
```

### Code Structure

- **models.py**: Data classes for Job and Config
- **storage.py**: Thread-safe SQLite operations with ACID guarantees
- **worker.py**: Job execution logic with retry handling
- **manager.py**: Process lifecycle management
- **cli.py**: Click-based CLI with all commands

## 📝 License

This project is licensed under the MIT License.

## 👤 Author

**Dheeraj**
- GitHub: [@dheeraj1922d](https://github.com/dheeraj1922d)

## 🙏 Acknowledgments

Built as part of the **QueueCTL Backend Developer Internship Assignment**.

---

**Note**: This is a demonstration project showcasing job queue system design and implementation. For production use, consider additional features like authentication, API endpoints, and distributed architecture.
