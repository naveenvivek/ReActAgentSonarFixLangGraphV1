#!/usr/bin/env python3
"""
Log Viewer Utility for SonarAI Agent JSON logs.
Provides various viewing and analysis options for JSON-formatted logs.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
import sys
from typing import Dict, List, Any


def load_json_logs(log_file: str) -> List[Dict[str, Any]]:
    """Load and parse JSON log entries from file, handling both JSONL and JSON array formats."""
    logs = []
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()

        if not content:
            print(f"Warning: Log file is empty: {log_file}")
            return logs

        # Try to parse as JSON array first (new format)
        try:
            data = json.loads(content)
            if isinstance(data, list):
                logs = data
                print(f"📊 Loaded {len(logs)} log entries from {log_file}")
            else:
                logs = [data]  # Single JSON object
                print(f"📊 Loaded 1 log entry from {log_file}")
            return logs
        except json.JSONDecodeError:
            # Fallback to JSONL format (legacy)
            print(f"📊 Parsing as JSONL format...")
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    log_entry = json.loads(line)
                    logs.append(log_entry)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {line_num}: {e}")

    except FileNotFoundError:
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading log file: {e}")
        sys.exit(1)
    return logs


def find_latest_log_file() -> str:
    """Find the latest datetime-stamped JSON log file."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print("Error: logs directory not found")
        sys.exit(1)

    log_files = list(logs_dir.glob("sonar_ai_agent_*.json"))
    if not log_files:
        print("Error: No JSON log files found")
        sys.exit(1)

    # Sort by modification time, newest first
    latest_log = sorted(
        log_files, key=lambda x: x.stat().st_mtime, reverse=True)[0]
    return str(latest_log)


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    except:
        return iso_timestamp


def view_logs(logs: List[Dict[str, Any]], level_filter: str = None,
              limit: int = None, show_metadata: bool = True):
    """Display logs in a readable format."""
    filtered_logs = logs

    if level_filter:
        filtered_logs = [log for log in logs if log.get(
            'level', '').upper() == level_filter.upper()]

    if limit:
        filtered_logs = filtered_logs[-limit:]  # Show latest N entries

    print(f"📋 Displaying {len(filtered_logs)} log entries")
    print("=" * 80)

    for i, log in enumerate(filtered_logs, 1):
        timestamp = format_timestamp(log.get('timestamp', ''))
        level = log.get('level', 'UNKNOWN')
        message = log.get('message', '')
        logger = log.get('logger', '')

        # Color code by level
        level_colors = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m'  # Magenta
        }
        color = level_colors.get(level, '')
        reset = '\033[0m' if color else ''

        print(f"\n{i}. [{timestamp}] {color}{level}{reset}: {message}")
        print(f"   Logger: {logger}")

        if show_metadata:
            metadata = log.get('metadata', {})
            performance = log.get('performance_data', {})

            if metadata:
                print(f"   Metadata:")
                for key, value in metadata.items():
                    if isinstance(value, (dict, list)):
                        print(
                            f"     {key}: {json.dumps(value, indent=2)[:100]}...")
                    else:
                        print(f"     {key}: {value}")

            if performance:
                print(f"   Performance:")
                for key, value in performance.items():
                    if key == 'duration_ms':
                        print(f"     Duration: {value:.2f}ms")
                    elif key == 'throughput_per_second':
                        print(f"     Throughput: {value:.2f}/sec")
                    else:
                        print(f"     {key}: {value}")

        # Show exception info if present
        if log.get('exception'):
            exc = log['exception']
            print(f"   Exception: {exc.get('type')} - {exc.get('message')}")


def analyze_performance(logs: List[Dict[str, Any]]):
    """Analyze performance metrics from logs."""
    print("🔍 Performance Analysis")
    print("=" * 50)

    perf_logs = [log for log in logs if log.get('performance_data')]

    if not perf_logs:
        print("No performance data found in logs.")
        return

    # Extract duration data
    durations = []
    throughputs = []
    operations = {}

    for log in perf_logs:
        perf = log['performance_data']

        # Collect durations
        if 'duration_ms' in perf:
            durations.append(perf['duration_ms'])

        # Collect throughputs
        if 'throughput_per_second' in perf:
            throughputs.append(perf['throughput_per_second'])

        # Group by operation
        operation = log.get('metadata', {}).get('operation', 'unknown')
        if operation not in operations:
            operations[operation] = []
        operations[operation].append(perf.get('duration_ms', 0))

    # Overall statistics
    if durations:
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        min_duration = min(durations)

        print(f"Duration Statistics:")
        print(f"  Average: {avg_duration:.2f}ms")
        print(f"  Maximum: {max_duration:.2f}ms")
        print(f"  Minimum: {min_duration:.2f}ms")
        print(f"  Total operations: {len(durations)}")

    if throughputs:
        avg_throughput = sum(throughputs) / len(throughputs)
        print(f"\nThroughput Statistics:")
        print(f"  Average: {avg_throughput:.2f} items/sec")
        print(f"  Maximum: {max(throughputs):.2f} items/sec")

    # Per-operation statistics
    if operations:
        print(f"\nPer-Operation Statistics:")
        for op, times in operations.items():
            if times:
                avg_time = sum(times) / len(times)
                print(f"  {op}: {avg_time:.2f}ms avg ({len(times)} calls)")


def analyze_errors(logs: List[Dict[str, Any]]):
    """Analyze error patterns from logs."""
    print("🚨 Error Analysis")
    print("=" * 50)

    error_logs = [log for log in logs if log.get(
        'level') in ['ERROR', 'CRITICAL', 'WARNING']]

    if not error_logs:
        print("No errors found in logs.")
        return

    # Group by error type
    error_types = {}
    error_contexts = {}

    for log in error_logs:
        level = log.get('level', 'UNKNOWN')
        metadata = log.get('metadata', {})

        # Group by error type
        error_type = metadata.get('error_type', 'Unknown')
        if error_type not in error_types:
            error_types[error_type] = []
        error_types[error_type].append(log)

        # Group by context
        context = metadata.get('context', 'Unknown')
        if context not in error_contexts:
            error_contexts[context] = []
        error_contexts[context].append(log)

    print(f"Total errors/warnings: {len(error_logs)}")

    print(f"\nBy Error Type:")
    for error_type, logs_list in error_types.items():
        print(f"  {error_type}: {len(logs_list)} occurrences")

    print(f"\nBy Context:")
    for context, logs_list in error_contexts.items():
        print(f"  {context}: {len(logs_list)} occurrences")

    # Show recent errors
    recent_errors = error_logs[-5:]  # Last 5 errors
    print(f"\nRecent Errors:")
    for i, log in enumerate(recent_errors, 1):
        timestamp = format_timestamp(log.get('timestamp', ''))
        level = log.get('level', '')
        message = log.get('message', '')
        print(f"  {i}. [{timestamp}] {level}: {message}")


def export_summary(logs: List[Dict[str, Any]], output_file: str):
    """Export a summary of the logs to a file."""
    summary = {
        'analysis_timestamp': datetime.now().isoformat(),
        'total_logs': len(logs),
        'log_levels': {},
        'time_range': {},
        'performance_summary': {},
        'error_summary': {}
    }

    # Count by level
    for log in logs:
        level = log.get('level', 'UNKNOWN')
        summary['log_levels'][level] = summary['log_levels'].get(level, 0) + 1

    # Time range
    timestamps = [log.get('timestamp') for log in logs if log.get('timestamp')]
    if timestamps:
        summary['time_range']['first'] = min(timestamps)
        summary['time_range']['last'] = max(timestamps)

    # Performance summary
    perf_logs = [log for log in logs if log.get('performance_data')]
    if perf_logs:
        durations = [log['performance_data'].get(
            'duration_ms', 0) for log in perf_logs]
        if durations:
            summary['performance_summary'] = {
                'total_operations': len(durations),
                'avg_duration_ms': sum(durations) / len(durations),
                'max_duration_ms': max(durations),
                'min_duration_ms': min(durations)
            }

    # Error summary
    error_logs = [log for log in logs if log.get(
        'level') in ['ERROR', 'CRITICAL', 'WARNING']]
    summary['error_summary']['total_errors'] = len(error_logs)

    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"📊 Summary exported to: {output_file}")


def main():
    """Main function for log viewer utility."""
    parser = argparse.ArgumentParser(description="SonarAI Agent Log Viewer")
    parser.add_argument(
        '--file', '-f', help='Log file to analyze (default: latest)')
    parser.add_argument(
        '--level', '-l', help='Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
    parser.add_argument('--limit', '-n', type=int,
                        help='Limit number of entries to show')
    parser.add_argument('--performance', '-p',
                        action='store_true', help='Show performance analysis')
    parser.add_argument('--errors', '-e', action='store_true',
                        help='Show error analysis')
    parser.add_argument('--export', help='Export summary to JSON file')
    parser.add_argument('--no-metadata', action='store_true',
                        help='Hide metadata in log display')

    args = parser.parse_args()

    # Determine log file to use
    if args.file:
        log_file = args.file
    else:
        log_file = find_latest_log_file()
        print(f"📁 Using latest log file: {log_file}")

    # Load logs
    logs = load_json_logs(log_file)

    if not logs:
        print("No log entries found.")
        return

    print(f"📊 Loaded {len(logs)} log entries from {log_file}")

    # Perform requested analysis
    if args.performance:
        analyze_performance(logs)
    elif args.errors:
        analyze_errors(logs)
    elif args.export:
        export_summary(logs, args.export)
    else:
        # Default view
        view_logs(logs,
                  level_filter=args.level,
                  limit=args.limit,
                  show_metadata=not args.no_metadata)


if __name__ == "__main__":
    main()
