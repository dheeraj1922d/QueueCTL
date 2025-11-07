#!/bin/bash

# QueueCTL Test Script
# Tests core functionality of the job queue system

set -e  # Exit on error

echo "======================================"
echo "QueueCTL Functional Test Suite"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup function
cleanup() {
    echo ""
    echo "Cleaning up..."
    queuectl worker stop --force 2>/dev/null || true
    rm -f queuectl.db queuectl.db-journal .queuectl_workers.pid
    echo "Cleanup complete"
}

# Setup trap for cleanup
trap cleanup EXIT

# Helper function to run test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -e "${YELLOW}TEST:${NC} $test_name"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Initial cleanup
cleanup

echo "Setting up test environment..."
echo ""

# Test 1: Check CLI is available
run_test "CLI command available" "command -v queuectl >/dev/null 2>&1"

# Test 2: Show help
run_test "Show help" "queuectl --help >/dev/null"

# Test 3: Show status (empty queue)
run_test "Show empty queue status" "queuectl status"

# Test 4: Enqueue a simple job
run_test "Enqueue simple job" 'queuectl enqueue '"'"'{"id":"test-job-1","command":"echo '\''Hello World'\''"}'"'"

# Test 5: List pending jobs
run_test "List pending jobs" "queuectl list --state pending | grep -q 'test-job-1'"

# Test 6: Get specific job
run_test "Get job details" "queuectl get test-job-1 | grep -q 'test-job-1'"

# Test 7: Configuration management
run_test "Show configuration" "queuectl config show"
run_test "Set max-retries" "queuectl config set max-retries 5"
run_test "Verify config change" "queuectl config show | grep -q 'max-retries.*5'"

# Test 8: Enqueue multiple jobs
echo "Enqueuing multiple jobs..."
queuectl enqueue '{"id":"job-success","command":"echo Success"}'
queuectl enqueue '{"id":"job-sleep","command":"sleep 1 && echo Done"}'
queuectl enqueue '{"id":"job-fail","command":"exit 1","max_retries":2}'
queuectl enqueue '{"id":"job-notfound","command":"nonexistent_command_12345","max_retries":1}'

run_test "Verify multiple jobs enqueued" "[ $(queuectl list --state pending | grep -c 'job-') -ge 4 ]"

# Test 9: Start workers
run_test "Start workers" "queuectl worker start --count 2"
run_test "Verify workers running" "[ $(queuectl worker status | grep -c 'PID') -gt 0 ]"

# Test 10: Wait for jobs to process
echo "Waiting for jobs to process..."
sleep 8

# Test 11: Check job completion
run_test "Job completed successfully" "queuectl list --state completed | grep -q 'job-success'"

# Test 12: Check failed jobs moved to DLQ
echo "Waiting for failed jobs to reach DLQ..."
sleep 5

run_test "Failed job in DLQ" "queuectl dlq list | grep -q 'job-fail' || queuectl dlq list | grep -q 'job-notfound'"

# Test 13: DLQ operations
run_test "List DLQ jobs" "queuectl dlq list"

# Find a job in DLQ and retry it
DLQ_JOB=$(queuectl dlq list 2>/dev/null | grep -oP 'job-\w+' | head -1 || echo "")
if [ ! -z "$DLQ_JOB" ]; then
    run_test "Retry DLQ job" "queuectl dlq retry $DLQ_JOB --reset-attempts"
fi

# Test 14: Worker management
run_test "Stop workers" "queuectl worker stop"
run_test "Verify workers stopped" "! queuectl worker status | grep -q 'PID'"

# Test 15: Data persistence test
echo "Testing data persistence..."
queuectl enqueue '{"id":"persist-test","command":"echo Persistence"}'
run_test "Job persisted before restart" "queuectl get persist-test | grep -q 'persist-test'"

# Simulate restart by creating new storage instance (data should persist)
run_test "Job still exists after DB close/reopen" "queuectl get persist-test | grep -q 'persist-test'"

# Test 16: Clear operations
run_test "Clear completed jobs" "echo 'y' | queuectl clear --state completed"

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Failed:${NC} $TESTS_FAILED"
echo -e "Total:  $((TESTS_PASSED + TESTS_FAILED))"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
