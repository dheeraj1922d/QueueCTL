"""
Command-line interface for QueueCTL.
"""

import click
import json
import sys
from datetime import datetime
from tabulate import tabulate

from .models import Job, JobState, Config
from .storage import Storage
from .manager import WorkerManager


# Create storage instance
storage = Storage()
manager = WorkerManager()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    QueueCTL - A production-grade CLI-based background job queue system.
    
    Manage background jobs with worker processes, automatic retries, and DLQ support.
    """
    pass


@cli.command()
@click.argument('job_json', type=str)
def enqueue(job_json):
    """
    Add a new job to the queue.
    
    JOB_JSON: JSON string or file path containing job definition
    
    Example:
        queuectl enqueue '{"id":"job1","command":"echo Hello"}'
    """
    try:
        # Check if it's a file path
        if job_json.startswith('@'):
            file_path = job_json[1:]
            with open(file_path, 'r') as f:
                job_data = json.load(f)
        else:
            job_data = json.loads(job_json)
        
        # Get current config for max_retries default
        config = storage.get_config()
        
        # Set defaults from config if not provided
        if 'max_retries' not in job_data:
            job_data['max_retries'] = config.max_retries
        
        # Create job
        job = Job.from_dict(job_data)
        
        # Check if job already exists
        existing_job = storage.get_job(job.id)
        if existing_job:
            click.echo(f"Error: Job with ID '{job.id}' already exists", err=True)
            sys.exit(1)
        
        # Save job
        if storage.save_job(job):
            click.echo(f"✓ Job '{job.id}' enqueued successfully")
            click.echo(f"  Command: {job.command}")
            click.echo(f"  Max retries: {job.max_retries}")
        else:
            click.echo("Error: Failed to enqueue job", err=True)
            sys.exit(1)
    
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.group()
def worker():
    """Manage worker processes."""
    pass


@worker.command('start')
@click.option('--count', '-c', default=1, type=int, help='Number of workers to start')
def worker_start(count):
    """
    Start one or more worker processes.
    
    Example:
        queuectl worker start --count 3
    """
    if count < 1:
        click.echo("Error: Worker count must be at least 1", err=True)
        sys.exit(1)
    
    pids = manager.start_workers(count)
    
    if not pids:
        sys.exit(1)


@worker.command('stop')
@click.option('--force', '-f', is_flag=True, help='Force kill workers immediately')
def worker_stop(force):
    """
    Stop all running workers.
    
    Example:
        queuectl worker stop
        queuectl worker stop --force
    """
    count = manager.stop_workers(graceful=not force)
    
    if count == 0:
        sys.exit(1)


@worker.command('status')
def worker_status():
    """
    Show status of running workers.
    
    Example:
        queuectl worker status
    """
    workers = manager.get_worker_status()
    
    if not workers:
        click.echo("No workers running")
        return
    
    # Format worker data
    table_data = []
    for w in workers:
        table_data.append([
            w['pid'],
            w['status'],
            f"{w['cpu_percent']:.1f}%",
            f"{w['memory_mb']:.1f} MB",
            w['created']
        ])
    
    click.echo("\n" + tabulate(
        table_data,
        headers=['PID', 'Status', 'CPU', 'Memory', 'Started'],
        tablefmt='grid'
    ))
    click.echo(f"\nTotal workers: {len(workers)}")


@cli.command()
def status():
    """
    Show summary of all job states and active workers.
    
    Example:
        queuectl status
    """
    # Get job counts
    counts = storage.get_job_counts()
    
    # Get worker status
    workers = manager.get_worker_status()
    
    click.echo("\n=== QueueCTL Status ===\n")
    
    # Job statistics
    click.echo("Jobs by State:")
    table_data = []
    for state in [JobState.PENDING, JobState.PROCESSING, JobState.COMPLETED, 
                  JobState.FAILED, JobState.DEAD]:
        count = counts.get(state, 0)
        icon = "●" if count > 0 else "○"
        table_data.append([icon, state.upper(), count])
    
    click.echo(tabulate(table_data, headers=['', 'State', 'Count'], tablefmt='simple'))
    
    total_jobs = sum(counts.values())
    click.echo(f"\nTotal jobs: {total_jobs}")
    
    # Worker statistics
    click.echo(f"\nActive workers: {len(workers)}")
    
    # Configuration
    config = storage.get_config()
    click.echo("\nConfiguration:")
    click.echo(f"  Max retries: {config.max_retries}")
    click.echo(f"  Backoff base: {config.backoff_base}")
    click.echo(f"  Job timeout: {config.job_timeout}s")
    click.echo()


@cli.command('list')
@click.option('--state', '-s', type=str, help='Filter by job state')
@click.option('--limit', '-l', type=int, default=50, help='Maximum number of jobs to show')
def list_jobs(state, limit):
    """
    List jobs, optionally filtered by state.
    
    Example:
        queuectl list
        queuectl list --state pending
        queuectl list --state completed --limit 10
    """
    if state:
        state = state.lower()
        if state not in [JobState.PENDING, JobState.PROCESSING, JobState.COMPLETED,
                        JobState.FAILED, JobState.DEAD]:
            click.echo(f"Error: Invalid state '{state}'", err=True)
            click.echo(f"Valid states: pending, processing, completed, failed, dead", err=True)
            sys.exit(1)
        
        jobs = storage.get_jobs_by_state(state)
    else:
        jobs = storage.get_all_jobs()
    
    if not jobs:
        click.echo("No jobs found")
        return
    
    # Limit results
    jobs = jobs[:limit]
    
    # Format job data
    table_data = []
    for job in jobs:
        # Truncate command if too long
        command = job.command
        if len(command) > 40:
            command = command[:37] + "..."
        
        # Format error message
        error = ""
        if job.error_message:
            error = job.error_message
            if len(error) > 30:
                error = error[:27] + "..."
        
        table_data.append([
            job.id,
            command,
            job.state,
            f"{job.attempts}/{job.max_retries}",
            error,
            job.created_at[:19]
        ])
    
    click.echo("\n" + tabulate(
        table_data,
        headers=['ID', 'Command', 'State', 'Attempts', 'Error', 'Created'],
        tablefmt='grid'
    ))
    
    click.echo(f"\nShowing {len(jobs)} job(s)")
    if len(jobs) == limit:
        click.echo(f"(Limited to {limit} results. Use --limit to show more)")


@cli.command('get')
@click.argument('job_id', type=str)
def get_job(job_id):
    """
    Get detailed information about a specific job.
    
    Example:
        queuectl get job1
    """
    job = storage.get_job(job_id)
    
    if not job:
        click.echo(f"Error: Job '{job_id}' not found", err=True)
        sys.exit(1)
    
    click.echo("\n" + job.to_json())


@cli.group()
def dlq():
    """Manage Dead Letter Queue (DLQ)."""
    pass


@dlq.command('list')
def dlq_list():
    """
    List all jobs in the Dead Letter Queue.
    
    Example:
        queuectl dlq list
    """
    jobs = storage.get_jobs_by_state(JobState.DEAD)
    
    if not jobs:
        click.echo("No jobs in DLQ")
        return
    
    # Format job data
    table_data = []
    for job in jobs:
        # Truncate command if too long
        command = job.command
        if len(command) > 40:
            command = command[:37] + "..."
        
        # Truncate error
        error = job.error_message or ""
        if len(error) > 40:
            error = error[:37] + "..."
        
        table_data.append([
            job.id,
            command,
            job.attempts,
            error,
            job.updated_at[:19]
        ])
    
    click.echo("\n" + tabulate(
        table_data,
        headers=['ID', 'Command', 'Attempts', 'Last Error', 'Failed At'],
        tablefmt='grid'
    ))
    
    click.echo(f"\nTotal jobs in DLQ: {len(jobs)}")


@dlq.command('retry')
@click.argument('job_id', type=str)
@click.option('--reset-attempts', '-r', is_flag=True, help='Reset attempt counter')
def dlq_retry(job_id, reset_attempts):
    """
    Retry a job from the Dead Letter Queue.
    
    Example:
        queuectl dlq retry job1
        queuectl dlq retry job1 --reset-attempts
    """
    job = storage.get_job(job_id)
    
    if not job:
        click.echo(f"Error: Job '{job_id}' not found", err=True)
        sys.exit(1)
    
    if job.state != JobState.DEAD:
        click.echo(f"Error: Job '{job_id}' is not in DLQ (current state: {job.state})", err=True)
        sys.exit(1)
    
    # Reset job state
    job.state = JobState.PENDING
    job.error_message = None
    job.next_retry_at = None
    
    if reset_attempts:
        job.attempts = 0
    
    if storage.save_job(job):
        click.echo(f"✓ Job '{job_id}' moved back to pending queue")
        if reset_attempts:
            click.echo(f"  Attempts reset to 0")
    else:
        click.echo("Error: Failed to retry job", err=True)
        sys.exit(1)


@dlq.command('clear')
@click.confirmation_option(prompt='Are you sure you want to delete all DLQ jobs?')
def dlq_clear():
    """
    Clear all jobs from the Dead Letter Queue.
    
    Example:
        queuectl dlq clear
    """
    jobs = storage.get_jobs_by_state(JobState.DEAD)
    count = len(jobs)
    
    if count == 0:
        click.echo("No jobs in DLQ")
        return
    
    for job in jobs:
        storage.delete_job(job.id)
    
    click.echo(f"✓ Deleted {count} job(s) from DLQ")


@cli.group()
def config():
    """Manage system configuration."""
    pass


@config.command('show')
def config_show():
    """
    Show current configuration.
    
    Example:
        queuectl config show
    """
    cfg = storage.get_config()
    
    click.echo("\n=== Configuration ===\n")
    table_data = [
        ['max-retries', cfg.max_retries, 'Maximum retry attempts for failed jobs'],
        ['backoff-base', cfg.backoff_base, 'Base for exponential backoff (base^attempts)'],
        ['worker-poll-interval', cfg.worker_poll_interval, 'Worker polling interval (seconds)'],
        ['job-timeout', cfg.job_timeout, 'Job execution timeout (seconds)']
    ]
    
    click.echo(tabulate(table_data, headers=['Key', 'Value', 'Description'], tablefmt='grid'))
    click.echo()


@config.command('set')
@click.argument('key', type=str)
@click.argument('value', type=str)
def config_set(key, value):
    """
    Set a configuration value.
    
    Example:
        queuectl config set max-retries 5
        queuectl config set backoff-base 3
    """
    # Convert key format
    key_map = {
        'max-retries': 'max_retries',
        'backoff-base': 'backoff_base',
        'worker-poll-interval': 'worker_poll_interval',
        'job-timeout': 'job_timeout'
    }
    
    if key not in key_map:
        click.echo(f"Error: Invalid config key '{key}'", err=True)
        click.echo(f"Valid keys: {', '.join(key_map.keys())}", err=True)
        sys.exit(1)
    
    # Get current config
    cfg = storage.get_config()
    cfg_dict = cfg.to_dict()
    
    # Update value
    internal_key = key_map[key]
    try:
        # Convert value to appropriate type
        current_value = cfg_dict[internal_key]
        if isinstance(current_value, int):
            cfg_dict[internal_key] = int(value)
        elif isinstance(current_value, float):
            cfg_dict[internal_key] = float(value)
        else:
            cfg_dict[internal_key] = value
        
        # Save config
        new_cfg = Config.from_dict(cfg_dict)
        storage.save_config(new_cfg)
        
        click.echo(f"✓ Configuration updated: {key} = {cfg_dict[internal_key]}")
        click.echo(f"  Note: Restart workers for changes to take effect")
    
    except ValueError:
        click.echo(f"Error: Invalid value '{value}' for {key}", err=True)
        sys.exit(1)


@cli.command('clear')
@click.option('--state', '-s', type=str, help='Clear jobs in specific state')
@click.confirmation_option(prompt='Are you sure you want to delete jobs?')
def clear_jobs(state):
    """
    Clear jobs from the queue.
    
    Example:
        queuectl clear --state completed
    """
    if state:
        state = state.lower()
        if state not in [JobState.PENDING, JobState.PROCESSING, JobState.COMPLETED,
                        JobState.FAILED, JobState.DEAD]:
            click.echo(f"Error: Invalid state '{state}'", err=True)
            sys.exit(1)
        
        jobs = storage.get_jobs_by_state(state)
    else:
        jobs = storage.get_all_jobs()
    
    count = len(jobs)
    
    if count == 0:
        click.echo("No jobs to clear")
        return
    
    for job in jobs:
        storage.delete_job(job.id)
    
    click.echo(f"✓ Deleted {count} job(s)")


def main():
    """Entry point for the CLI."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
