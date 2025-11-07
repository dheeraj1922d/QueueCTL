# QueueCTL Quick Start Guide

Get up and running with QueueCTL in 5 minutes!

## Installation

```bash
# Clone repository
git clone https://github.com/dheeraj1922d/QueueCTL.git
cd QueueCTL

# Install dependencies
pip install -r requirements.txt

# Install QueueCTL
pip install -e .

# Verify installation
queuectl --version
```

## Your First Job

```bash
# 1. Enqueue a job
queuectl enqueue '{"id":"my-first-job","command":"echo Hello World"}'

# 2. Start a worker
queuectl worker start

# 3. Check status (wait a moment)
sleep 2
queuectl status

# 4. View completed jobs
queuectl list --state completed

# 5. Stop worker
queuectl worker stop
```

Congratulations! 🎉 You just ran your first background job.

## Essential Commands

### Job Management
```bash
# Enqueue a job
queuectl enqueue '{"id":"job-id","command":"your-command"}'

# List all jobs
queuectl list

# List jobs by state
queuectl list --state pending
queuectl list --state completed
queuectl list --state failed

# Get specific job details
queuectl get job-id

# Check overall status
queuectl status
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

### Dead Letter Queue (DLQ)
```bash
# List failed jobs
queuectl dlq list

# Retry a failed job
queuectl dlq retry job-id

# Retry with reset attempt counter
queuectl dlq retry job-id --reset-attempts

# Clear all DLQ jobs
queuectl dlq clear
```

### Configuration
```bash
# View configuration
queuectl config show

# Change max retries
queuectl config set max-retries 5

# Change backoff base
queuectl config set backoff-base 3
```

## Job Definition Format

```json
{
  "id": "unique-job-id",           // Required: Unique identifier
  "command": "echo Hello",         // Required: Shell command to execute
  "max_retries": 3                 // Optional: Override default retries
}
```

### Examples

**Simple command:**
```bash
queuectl enqueue '{"id":"hello","command":"echo Hello"}'
```

**Command with arguments:**
```bash
queuectl enqueue '{"id":"backup","command":"tar -czf backup.tar.gz /data"}'
```

**Multi-step command:**
```bash
queuectl enqueue '{"id":"multi","command":"cd /tmp && ls -la && echo Done"}'
```

**Custom retry limit:**
```bash
queuectl enqueue '{"id":"custom","command":"curl https://api.example.com","max_retries":5}'
```

**From JSON file:**
```bash
echo '{"id":"from-file","command":"echo From File"}' > job.json
queuectl enqueue '@job.json'
```

## Common Workflows

### Workflow 1: Process Multiple Jobs
```bash
# Enqueue multiple jobs
for i in {1..5}; do
  queuectl enqueue "{\"id\":\"job-$i\",\"command\":\"echo Processing $i\"}"
done

# Process with multiple workers
queuectl worker start --count 3

# Monitor progress
watch -n 1 'queuectl status'

# Stop when done
queuectl worker stop
```

### Workflow 2: Handle Failures
```bash
# Enqueue a job that might fail
queuectl enqueue '{"id":"api-call","command":"curl -f https://api.example.com","max_retries":3}'

# Start worker
queuectl worker start

# If it fails, it will retry automatically (2s, 4s, 8s)
# After max retries, check DLQ
queuectl dlq list

# Retry if needed
queuectl dlq retry api-call --reset-attempts
```

### Workflow 3: Long-Running Tasks
```bash
# Enqueue long tasks
queuectl enqueue '{"id":"task-1","command":"sleep 30 && echo Task 1 done"}'
queuectl enqueue '{"id":"task-2","command":"sleep 30 && echo Task 2 done"}'

# Start workers and let them run
queuectl worker start --count 2

# Workers will process in background
# Check back later
queuectl status
```

### Workflow 4: Clean Up
```bash
# Clear completed jobs
queuectl clear --state completed

# Stop all workers
queuectl worker stop

# Remove database (fresh start)
rm queuectl.db
```

## Tips & Best Practices

### 1. Job IDs
- Use descriptive, unique IDs
- Include timestamp for uniqueness: `job-2025-11-07-001`
- Use prefixes for job types: `backup-`, `api-`, `process-`

### 2. Commands
- Test commands manually before enqueueing
- Use absolute paths for reliability
- Handle errors in scripts: `command || true`
- Redirect stderr if needed: `2>/dev/null`

### 3. Workers
- Start with 1 worker, scale up as needed
- More workers ≠ faster (depends on CPU/IO)
- Typical range: 1-5 workers for most use cases
- Stop workers when not needed

### 4. Retries
- Set appropriate max_retries based on job type
- Quick failures: max_retries=2
- Network calls: max_retries=5
- Critical jobs: max_retries=10

### 5. Monitoring
- Check status regularly: `queuectl status`
- Monitor DLQ: `queuectl dlq list`
- Review failed jobs for patterns
- Adjust configuration based on patterns

## Troubleshooting

### Jobs Not Processing
```bash
# Check if workers are running
queuectl worker status

# Start workers if needed
queuectl worker start
```

### Jobs Stuck in Processing
```bash
# Stop workers (releases locks)
queuectl worker stop --force

# Restart workers
queuectl worker start
```

### Jobs Keep Failing
```bash
# Check DLQ for error messages
queuectl dlq list

# Test command manually
the-failing-command

# Fix command and retry
queuectl dlq retry job-id --reset-attempts
```

### Workers Won't Stop
```bash
# Force stop workers
queuectl worker stop --force

# Clean up PID file if needed
rm -f .queuectl_workers.pid
```

### Fresh Start
```bash
# Stop everything
queuectl worker stop --force

# Remove database
rm -f queuectl.db .queuectl_workers.pid

# Start fresh
queuectl status
```

## What's Next?

- Read the full [README.md](README.md) for detailed documentation
- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
- Review [DEMO.md](DEMO.md) for demo scenarios
- Run automated tests: `./test_queuectl.sh`
- Try examples: `./examples.sh`

## Getting Help

```bash
# General help
queuectl --help

# Command-specific help
queuectl enqueue --help
queuectl worker --help
queuectl dlq --help
queuectl config --help
```

## Need More?

- **GitHub**: https://github.com/dheeraj1922d/QueueCTL
- **Issues**: https://github.com/dheeraj1922d/QueueCTL/issues
- **Documentation**: See README.md and ARCHITECTURE.md

---

**Happy Queueing! 🚀**
