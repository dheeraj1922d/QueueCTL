#!/bin/bash

# QueueCTL Usage Examples
# Demonstrates various features of the job queue system

echo "======================================"
echo "QueueCTL Usage Examples"
echo "======================================"
echo ""

# Cleanup from previous runs
echo "Cleaning up from previous runs..."
queuectl worker stop --force 2>/dev/null || true
rm -f queuectl.db queuectl.db-journal .queuectl_workers.pid
sleep 1
echo ""

# Example 1: Basic Job
echo "Example 1: Basic Job Execution"
echo "--------------------------------"
queuectl enqueue '{"id":"hello-world","command":"echo Hello, QueueCTL!"}'
queuectl status
queuectl worker start --count 1
sleep 2
queuectl list --state completed
echo ""

# Example 2: Multiple Jobs
echo "Example 2: Multiple Jobs in Parallel"
echo "-------------------------------------"
queuectl enqueue '{"id":"job-1","command":"echo Job 1 && sleep 2"}'
queuectl enqueue '{"id":"job-2","command":"echo Job 2 && sleep 2"}'
queuectl enqueue '{"id":"job-3","command":"echo Job 3 && sleep 2"}'
queuectl worker start --count 2
sleep 5
queuectl status
echo ""

# Example 3: Job with Failure and Retry
echo "Example 3: Job Failure with Retry"
echo "----------------------------------"
queuectl enqueue '{"id":"fail-job","command":"exit 1","max_retries":2}'
echo "Waiting for job to fail and retry..."
sleep 10
queuectl list --state failed || true
queuectl dlq list
echo ""

# Example 4: Configuration
echo "Example 4: Configuration Management"
echo "-----------------------------------"
queuectl config show
queuectl config set max-retries 5
queuectl config show
echo ""

# Example 5: DLQ Operations
echo "Example 5: Dead Letter Queue Operations"
echo "---------------------------------------"
queuectl dlq list
# Try to retry a job from DLQ if exists
DLQ_JOB=$(queuectl dlq list 2>/dev/null | grep -oP '\| \K[a-zA-Z0-9\-]+(?= +\|)' | head -1 || echo "")
if [ ! -z "$DLQ_JOB" ]; then
    echo "Retrying job from DLQ: $DLQ_JOB"
    queuectl dlq retry "$DLQ_JOB" --reset-attempts
    sleep 5
    queuectl status
fi
echo ""

# Example 6: Worker Management
echo "Example 6: Worker Management"
echo "----------------------------"
queuectl worker status
queuectl worker stop
sleep 2
queuectl worker status || echo "No workers running"
echo ""

# Example 7: Complex Command
echo "Example 7: Complex Shell Commands"
echo "----------------------------------"
queuectl enqueue '{"id":"complex-1","command":"echo Start && sleep 1 && echo Middle && sleep 1 && echo End"}'
queuectl enqueue '{"id":"complex-2","command":"for i in 1 2 3; do echo Iteration $i; done"}'
queuectl worker start
sleep 5
queuectl list --state completed
echo ""

# Final cleanup
echo "Cleaning up..."
queuectl worker stop --force 2>/dev/null || true
echo ""

echo "======================================"
echo "Examples Complete!"
echo "======================================"
echo ""
echo "Try these commands yourself:"
echo "  queuectl status              # Check system status"
echo "  queuectl list                # List all jobs"
echo "  queuectl worker start -c 3   # Start 3 workers"
echo "  queuectl dlq list            # View failed jobs"
echo "  queuectl config show         # View configuration"
echo ""
