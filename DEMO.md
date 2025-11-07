# QueueCTL Demo Guide

This guide provides step-by-step instructions for demonstrating QueueCTL's capabilities.

## Demo Video Script

### Setup (30 seconds)

```bash
# Clone and setup
git clone https://github.com/dheeraj1922d/QueueCTL.git
cd QueueCTL
pip install -r requirements.txt
pip install -e .
```

### Demo 1: Basic Job Execution (1 minute)

```bash
# Check initial status
queuectl status

# Enqueue a simple job
queuectl enqueue '{"id":"hello","command":"echo Hello, QueueCTL!"}'

# List pending jobs
queuectl list --state pending

# Start a worker
queuectl worker start

# Wait a moment and check status
sleep 2
queuectl status

# View completed job
queuectl list --state completed

# Stop worker
queuectl worker stop
```

**What to highlight**: 
- Simple JSON-based job definition
- Clear status output
- Job state transitions (pending → processing → completed)

### Demo 2: Multiple Workers & Parallel Processing (1.5 minutes)

```bash
# Enqueue multiple jobs
for i in {1..6}; do
  queuectl enqueue "{\"id\":\"job-$i\",\"command\":\"echo Processing job $i && sleep 3\"}"
done

# Show pending jobs
queuectl list --state pending

# Start 3 workers for parallel processing
queuectl worker start --count 3

# Check worker status
queuectl worker status

# Monitor as jobs complete
watch -n 1 'queuectl status'

# Stop workers
queuectl worker stop
```

**What to highlight**:
- Concurrent job processing
- Multiple workers working in parallel
- No job duplication (proper locking)

### Demo 3: Retry Mechanism & DLQ (2 minutes)

```bash
# Enqueue jobs that will fail
queuectl enqueue '{"id":"fail-1","command":"exit 1","max_retries":2}'
queuectl enqueue '{"id":"fail-2","command":"nonexistent_command","max_retries":2}'

# Start worker
queuectl worker start

# Watch the retry mechanism
# You'll see exponential backoff: retry after 2s, then 4s
watch -n 1 'queuectl list'

# After retries exhausted (~10 seconds), check DLQ
sleep 12
queuectl dlq list

# Get details of failed job
queuectl dlq list

# Retry a job from DLQ
queuectl dlq retry fail-1 --reset-attempts

# Check status
queuectl status

# Stop worker
queuectl worker stop
```

**What to highlight**:
- Automatic retry with exponential backoff (2^1=2s, 2^2=4s)
- Failed jobs move to Dead Letter Queue after max retries
- Ability to retry jobs from DLQ
- Error messages captured

### Demo 4: Configuration Management (1 minute)

```bash
# View current configuration
queuectl config show

# Change max retries
queuectl config set max-retries 5

# Change backoff base for faster/slower retries
queuectl config set backoff-base 3

# View updated configuration
queuectl config show

# Configuration persists across restarts
```

**What to highlight**:
- Configurable retry behavior
- Persistence of settings
- Easy configuration management

### Demo 5: Data Persistence (1 minute)

```bash
# Enqueue jobs
queuectl enqueue '{"id":"persist-1","command":"echo Job 1"}'
queuectl enqueue '{"id":"persist-2","command":"echo Job 2"}'

# Check status
queuectl list

# Simulate "restart" by just checking data is still there
queuectl list

# Start worker to process
queuectl worker start
sleep 3

# Jobs completed and data persisted
queuectl list --state completed

queuectl worker stop
```

**What to highlight**:
- SQLite-based persistence
- Data survives restarts
- ACID guarantees

### Demo 6: Complex Commands (1 minute)

```bash
# Multi-step commands
queuectl enqueue '{"id":"complex-1","command":"echo Start && sleep 1 && echo Middle && sleep 1 && echo Done"}'

# Shell loops
queuectl enqueue '{"id":"loop-1","command":"for i in 1 2 3; do echo Iteration $i; sleep 1; done"}'

# Conditional execution
queuectl enqueue '{"id":"cond-1","command":"[ -f /etc/hosts ] && echo File exists || echo File missing"}'

# Process and verify
queuectl worker start
sleep 8
queuectl list --state completed

queuectl worker stop
```

**What to highlight**:
- Any shell command supported
- Complex multi-step operations
- Shell scripting capabilities

## Key Features to Emphasize

### 1. Production-Ready
- ACID guarantees with SQLite
- Atomic job acquisition
- No race conditions
- Graceful shutdown

### 2. Robust Error Handling
- Automatic retries
- Exponential backoff
- Dead Letter Queue
- Error message capture

### 3. Easy to Use
- Simple CLI interface
- JSON-based job definitions
- Clear status output
- Comprehensive help

### 4. Scalable
- Multiple workers
- Concurrent processing
- No job duplication
- Configurable behavior

### 5. Persistent
- Survives restarts
- SQLite storage
- Transaction safety
- Data integrity

## Demo Tips

1. **Use `watch` command** for live monitoring:
   ```bash
   watch -n 1 'queuectl status'
   ```

2. **Keep terminal output clean**:
   - Clear screen between demos: `clear`
   - Use `--limit` flag for list commands
   - Show most relevant commands

3. **Explain as you go**:
   - What each command does
   - Expected behavior
   - What's happening behind the scenes

4. **Handle errors gracefully**:
   - If something fails, explain why
   - Show how to recover
   - Demonstrate DLQ functionality

5. **Time management**:
   - Prepare database beforehand if needed
   - Use shorter sleep times for demos
   - Have backup commands ready

## Common Demo Scenarios

### Scenario A: Job Failure Recovery
```bash
# Simulate network service call that fails initially
queuectl enqueue '{"id":"api-call","command":"curl -f https://httpstat.us/503 || exit 1","max_retries":3}'
queuectl worker start
# Watch it retry with backoff
# Eventually moves to DLQ
# Show DLQ management
```

### Scenario B: Background Processing
```bash
# Long-running background tasks
queuectl enqueue '{"id":"backup","command":"tar -czf backup.tar.gz /tmp 2>/dev/null || true"}'
queuectl enqueue '{"id":"cleanup","command":"find /tmp -type f -name \"*.tmp\" -mtime +7 -delete 2>/dev/null || true"}'
queuectl worker start
# Show workers processing in background
```

### Scenario C: Batch Processing
```bash
# Process multiple files
for file in file1.txt file2.txt file3.txt; do
  queuectl enqueue "{\"id\":\"process-$file\",\"command\":\"echo Processing $file && sleep 2\"}"
done
queuectl worker start --count 2
# Show parallel batch processing
```

## Recording the Demo

### Recommended Tools
- **Terminal recording**: asciinema, terminalizer
- **Screen recording**: OBS Studio, SimpleScreenRecorder
- **GIF creation**: peek, gifski

### Recording Tips
1. Use a clean terminal with good contrast
2. Set terminal size to 100x30 for readability
3. Use larger font size (14-16pt)
4. Speak clearly and explain actions
5. Keep demo under 5-10 minutes
6. Edit out long waits

### Example asciinema Recording
```bash
# Install asciinema
pip install asciinema

# Record demo
asciinema rec queuectl-demo.cast

# Upload to asciinema.org
asciinema upload queuectl-demo.cast

# Or convert to GIF
docker run --rm -v $PWD:/data asciinema/asciicast2gif queuectl-demo.cast demo.gif
```

## Questions to Anticipate

**Q: How does it handle concurrent access?**
A: Atomic database transactions with job locking prevent race conditions.

**Q: What happens if a worker crashes?**
A: Stale locks are automatically released after 5 minutes, and jobs are reprocessed.

**Q: Can I schedule jobs for future execution?**
A: Not in v1.0, but it's planned for v1.5. Currently, you can use system cron to enqueue jobs.

**Q: How many workers can I run?**
A: Limited by system resources. Typically 1-10 workers work well for most use cases.

**Q: Can this run distributed across multiple machines?**
A: Not currently. It's designed for single-machine use. Distributed mode planned for v2.0.

**Q: How do I monitor job outputs?**
A: Currently, outputs go to worker logs. Job output storage is planned for v1.1.

## Clean Up After Demo

```bash
# Stop all workers
queuectl worker stop --force

# Clear all jobs
echo 'y' | queuectl clear

# Or delete database
rm queuectl.db

# Remove PID file
rm -f .queuectl_workers.pid
```

---

**Good luck with your demo! 🚀**
