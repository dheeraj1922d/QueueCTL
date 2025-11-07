# QueueCTL Architecture Documentation

## System Overview

QueueCTL is a production-grade job queue system designed for background task execution with reliability, persistence, and fault tolerance.

## Design Principles

1. **Simplicity**: Easy to understand, deploy, and maintain
2. **Reliability**: ACID guarantees through SQLite
3. **Fault Tolerance**: Automatic retries with exponential backoff
4. **Isolation**: Job execution in separate processes
5. **Observability**: Comprehensive status and monitoring

## Component Architecture

### 1. Storage Layer (`storage.py`)

**Responsibility**: Persistent data management with thread-safe operations

**Key Features**:
- SQLite database with ACID guarantees
- Thread-local connections for concurrency
- Atomic job acquisition with database-level locking
- Automatic schema initialization

**Database Schema**:

```sql
-- Jobs table
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    state TEXT NOT NULL,
    attempts INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    next_retry_at TEXT,
    error_message TEXT,
    locked_by TEXT,
    locked_at TEXT
);

-- Configuration table
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

**Concurrency Strategy**:
- `EXCLUSIVE` transactions for job acquisition
- Thread-local connection pool
- Row-level locking for job state updates
- Stale lock detection (5-minute timeout)

### 2. Worker Process (`worker.py`)

**Responsibility**: Job execution and lifecycle management

**Execution Flow**:

```
1. Acquire job (atomic)
2. Update state to PROCESSING
3. Execute command via subprocess
4. Handle result:
   - Success → COMPLETED
   - Failure → FAILED (with retry) or DEAD (DLQ)
5. Release lock
6. Repeat
```

**Error Handling**:
- Subprocess timeout detection
- Exit code evaluation
- stderr capture
- Exception handling

**Retry Logic**:
```python
if attempts < max_retries:
    backoff = base ** attempts
    next_retry = now + timedelta(seconds=backoff)
    state = FAILED
else:
    state = DEAD  # Move to DLQ
```

**Graceful Shutdown**:
- Signal handlers (SIGTERM, SIGINT)
- Complete current job before exit
- Release locks on shutdown

### 3. Worker Manager (`manager.py`)

**Responsibility**: Worker process lifecycle management

**Features**:
- Process spawning and tracking
- PID file management
- Health monitoring via psutil
- Graceful and force shutdown

**Process Model**:
```
CLI Process
    └─> WorkerManager
         ├─> Worker Process 1 (detached)
         ├─> Worker Process 2 (detached)
         └─> Worker Process N (detached)
```

**PID Tracking**:
- File-based PID storage (`.queuectl_workers.pid`)
- Automatic cleanup of dead processes
- Cross-session persistence

### 4. CLI Interface (`cli.py`)

**Responsibility**: User interaction and command processing

**Design Pattern**: Command pattern with Click framework

**Command Categories**:
- Job Management: enqueue, list, get
- Worker Control: start, stop, status
- DLQ Operations: list, retry, clear
- Configuration: show, set
- Maintenance: clear, status

**Output Formatting**: Tabulated display with color coding

### 5. Data Models (`models.py`)

**Responsibility**: Type-safe data structures

**Job Model**:
```python
@dataclass
class Job:
    id: str
    command: str
    state: str
    attempts: int
    max_retries: int
    created_at: str
    updated_at: str
    next_retry_at: Optional[str]
    error_message: Optional[str]
```

**Config Model**:
```python
@dataclass
class Config:
    max_retries: int
    backoff_base: int
    worker_poll_interval: float
    job_timeout: int
```

## Data Flow Diagrams

### Job Submission Flow

```
User
  │
  ├─> queuectl enqueue
  │
  ├─> Parse JSON
  │
  ├─> Validate Job
  │
  ├─> Storage.save_job()
  │     │
  │     ├─> Insert into SQLite
  │     └─> Return success
  │
  └─> Display confirmation
```

### Job Execution Flow

```
Worker Loop
  │
  ├─> Storage.acquire_job()
  │     │
  │     ├─> BEGIN EXCLUSIVE
  │     ├─> SELECT ... FOR UPDATE
  │     ├─> UPDATE locked_by
  │     └─> COMMIT
  │
  ├─> Execute Command
  │     │
  │     ├─> subprocess.run()
  │     ├─> Capture output
  │     └─> Check exit code
  │
  ├─> Handle Result
  │     │
  │     ├─> Success: state = COMPLETED
  │     │
  │     └─> Failure:
  │           ├─> attempts < max_retries?
  │           │     ├─> Yes: state = FAILED, schedule retry
  │           │     └─> No: state = DEAD (DLQ)
  │           └─> Calculate backoff
  │
  ├─> Storage.save_job()
  │
  └─> Storage.release_job()
```

### Retry Scheduling

```
Job Fails (Exit Code != 0)
  │
  ├─> Increment attempts
  │
  ├─> Check: attempts >= max_retries?
  │     │
  │     ├─> Yes: Move to DLQ
  │     │     └─> state = DEAD
  │     │
  │     └─> No: Schedule Retry
  │           ├─> Calculate backoff
  │           │     backoff = base ^ attempts
  │           │
  │           ├─> Set next_retry_at
  │           │     next_retry_at = now + backoff
  │           │
  │           └─> state = FAILED
  │
  └─> Worker polls for next_retry_at <= now
```

## Concurrency & Synchronization

### Job Acquisition Race Condition

**Problem**: Multiple workers trying to acquire same job

**Solution**: Atomic database transaction

```python
# Atomic job acquisition
cursor.execute("BEGIN EXCLUSIVE")

# Find and lock job in single query
job = cursor.execute("""
    SELECT * FROM jobs
    WHERE state = 'pending' AND locked_by IS NULL
    LIMIT 1
""").fetchone()

if job:
    cursor.execute("""
        UPDATE jobs 
        SET locked_by = ?, locked_at = ?, state = 'processing'
        WHERE id = ?
    """, (worker_id, now, job.id))

cursor.execute("COMMIT")
```

### Stale Lock Detection

**Problem**: Worker crashes while holding lock

**Solution**: Timeout-based lock expiration

```python
# Acquire jobs with expired locks
WHERE (locked_by IS NULL OR locked_at < datetime('now', '-5 minutes'))
```

## Error Handling Strategy

### Levels of Error Handling

1. **Command Execution Errors**
   - Captured via subprocess exit codes
   - stderr logged as error_message
   - Triggers retry mechanism

2. **System Errors**
   - Database connection failures
   - File I/O errors
   - Handled with try-except blocks

3. **Worker Crashes**
   - Locks automatically released via timeout
   - Jobs re-acquired by other workers
   - PID file cleanup on restart

4. **Graceful Degradation**
   - Continue processing on non-critical errors
   - Log warnings but don't crash system

## Performance Considerations

### Optimization Strategies

1. **Database Indexing**
   ```sql
   CREATE INDEX idx_jobs_state ON jobs(state);
   CREATE INDEX idx_jobs_next_retry ON jobs(next_retry_at);
   ```

2. **Connection Pooling**
   - Thread-local connections
   - Reduced connection overhead

3. **Polling Optimization**
   - Configurable poll interval
   - Prevents excessive CPU usage

4. **Batch Operations**
   - Single transaction per job
   - Minimized database round-trips

### Scalability Limits

- **Single Machine**: Limited by CPU/memory
- **SQLite**: ~100K ops/sec theoretical limit
- **Workers**: Limited by system resources
- **Recommendation**: 1-10 workers for typical use cases

## Security Considerations

### Command Injection Protection

**Risk**: Arbitrary command execution

**Mitigation**:
- Commands executed via subprocess.run()
- No shell injection vulnerabilities in system code
- Users responsible for command safety

### Access Control

**Current State**: No authentication/authorization

**Production Recommendations**:
- Add user authentication
- Implement role-based access control
- Audit logging for compliance

## Testing Strategy

### Unit Tests (Future)

```python
# Test job state transitions
def test_job_lifecycle():
    job = Job(id="test", command="echo test")
    assert job.state == JobState.PENDING
    
    # Simulate execution
    job.state = JobState.PROCESSING
    job.attempts += 1
    
    # Simulate success
    job.state = JobState.COMPLETED
    assert job.state == JobState.COMPLETED
```

### Integration Tests

Current implementation: `test_queuectl.sh`

Tests:
- End-to-end job execution
- Worker management
- DLQ operations
- Configuration changes
- Data persistence

### Manual Testing Checklist

- [ ] Job enqueuing and retrieval
- [ ] Worker start/stop
- [ ] Job execution (success/failure)
- [ ] Retry mechanism
- [ ] DLQ operations
- [ ] Concurrent processing
- [ ] Configuration changes
- [ ] Data persistence
- [ ] Graceful shutdown

## Deployment Guide

### Local Development

```bash
pip install -e .
queuectl worker start --count 1
```

### Production Deployment

1. **Install as System Service** (systemd example):

```ini
[Unit]
Description=QueueCTL Worker
After=network.target

[Service]
Type=simple
User=queuectl
WorkingDirectory=/opt/queuectl
ExecStart=/usr/bin/queuectl worker start --count 3
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Monitoring**:
   - Health checks via `queuectl status`
   - Log aggregation (syslog/journald)
   - Metrics collection (custom integration)

3. **Backup**:
   - Regular SQLite database backups
   - Point-in-time recovery capability

## Future Enhancements

### Short-term (v1.1)

- [ ] Job output logging
- [ ] Job timeout enforcement
- [ ] Priority queue support
- [ ] Better error reporting

### Medium-term (v1.5)

- [ ] Web dashboard
- [ ] REST API
- [ ] Scheduled jobs (cron-like)
- [ ] Job dependencies (DAG)

### Long-term (v2.0)

- [ ] Distributed mode (Redis backend)
- [ ] Horizontal scaling
- [ ] Load balancing
- [ ] Multi-tenant support

## Troubleshooting

### Common Issues

**Workers not starting**:
- Check Python version (3.7+)
- Verify dependencies installed
- Check file permissions

**Jobs stuck in processing**:
- Workers may have crashed
- Run `queuectl worker stop --force`
- Stale locks will auto-expire in 5 minutes

**Database locked errors**:
- Reduce worker count
- Check disk I/O performance
- Consider Redis for high-throughput

**Jobs not retrying**:
- Check configuration: `queuectl config show`
- Verify next_retry_at is set
- Ensure workers are running

## References

- SQLite Documentation: https://www.sqlite.org/docs.html
- Python subprocess: https://docs.python.org/3/library/subprocess.html
- Click CLI Framework: https://click.palletsprojects.com/
- psutil Documentation: https://psutil.readthedocs.io/
