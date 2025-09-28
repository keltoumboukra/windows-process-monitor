#!/usr/bin/env python3
"""
Windows Process Monitor - Main CLI Interface

This is the main entry point for the Windows Process Monitor tool.
It provides a command-line interface for viewing process information,
system resources, and process hierarchies.
"""

import argparse
import sys
from typing import List, Optional
from tabulate import tabulate
from process_monitor import ProcessMonitor, ProcessInfo
from logging_manager import LoggingManager


class ProcessMonitorCLI:
    """Command-line interface for the Windows Process Monitor."""
    
    def __init__(self):
        """Initialize the CLI interface."""
        self.monitor = ProcessMonitor()
        self.processes: List[ProcessInfo] = []
    
    def run(self, args: argparse.Namespace) -> None:
        """
        Main entry point for the CLI.
        
        Args:
            args: Parsed command line arguments
        """
        try:
            # Get all processes with I/O data
            print("Scanning processes and collecting I/O data...")
            self.processes = self.monitor.get_all_processes_with_io()
            
            if not self.processes:
                print("Warning: No processes found. You may need to run as administrator.")
                return
            
            print(f"Found {len(self.processes)} processes")
            
            # Execute requested action
            if args.log:
                self._start_logging(args.log, args.log_interval, args.log_dir)
            elif args.hierarchy:
                self._display_hierarchy()
            elif args.summary:
                self._display_system_summary()
            elif args.top:
                self._display_top_processes(args.top)
            else:
                self._display_process_list()
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    
    def _display_process_list(self) -> None:
        """Display a formatted list of all processes."""
        print("\n" + "="*80)
        print("PROCESS LIST")
        print("="*80)
        
        # Prepare data for table
        table_data = []
        for proc in self.processes:
            # Format I/O information
            disk_info = "N/A"
            if proc.disk_io:
                disk_info = f"{proc.disk_io.total_bytes() / 1024:.1f} KB"
            
            network_info = "N/A"
            if proc.network_io:
                network_info = f"{proc.network_io.total_connections()} conns"
            
            table_data.append([
                proc.pid,
                proc.name,
                proc.status,
                f"{proc.cpu_percent:.1f}%",
                f"{proc.memory_mb:.1f} MB",
                disk_info,
                network_info,
                proc.parent_pid or "N/A",
                proc.username
            ])
        
        # Create table
        headers = ["PID", "Name", "Status", "CPU %", "Memory", "Disk I/O", "Network", "Parent PID", "User"]
        table = tabulate(table_data, headers=headers, tablefmt="grid")
        
        print(table)
        print(f"\nTotal processes: {len(self.processes)}")
    
    def _display_hierarchy(self) -> None:
        """Display process hierarchy."""
        print("\n" + "="*80)
        print("PROCESS HIERARCHY")
        print("="*80)
        
        hierarchy = self.monitor.get_process_hierarchy()
        
        if not hierarchy:
            print("No process hierarchy found.")
            print(f"Debug: Found {len(self.processes)} processes")
            print(f"Debug: Parent-child map has {len(self.monitor.parent_child_map)} entries")
            if self.monitor.parent_child_map:
                print("Debug: Sample parent-child relationships:")
                for parent, children in list(self.monitor.parent_child_map.items())[:5]:
                    print(f"  {parent} -> {children}")
            return
        
        # Display hierarchy in tree format
        for parent_pid, children in hierarchy.items():
            parent_name = self._get_process_name(parent_pid)
            print(f"\n{parent_pid} ({parent_name})")
            
            for child_pid in children:
                child_name = self._get_process_name(child_pid)
                print(f"  └── {child_pid} ({child_name})")
                
                # Show grandchildren if they exist
                if child_pid in hierarchy:
                    for grandchild_pid in hierarchy[child_pid]:
                        grandchild_name = self._get_process_name(grandchild_pid)
                        print(f"      └── {grandchild_pid} ({grandchild_name})")
    
    def _display_system_summary(self) -> None:
        """Display system resource summary."""
        print("\n" + "="*80)
        print("SYSTEM RESOURCE SUMMARY")
        print("="*80)
        
        summary = self.monitor.get_system_summary()
        
        print(f"CPU Usage: {summary['cpu_percent']:.1f}%")
        print(f"Memory Usage: {summary['memory_percent']:.1f}%")
        print(f"Available Memory: {summary['memory_available_gb']:.2f} GB")
        print(f"Total Memory: {summary['memory_total_gb']:.2f} GB")
        print(f"Disk Usage: {summary['disk_usage_percent']:.1f}%")
        
        # Show top memory consumers
        print("\nTop 5 Memory Consumers:")
        top_memory = sorted(self.processes, key=lambda p: p.memory_mb, reverse=True)[:5]
        
        for i, proc in enumerate(top_memory, 1):
            print(f"{i}. {proc.name} (PID: {proc.pid}) - {proc.memory_mb:.1f} MB")
        
        # Show top disk I/O consumers
        print("\nTop 5 Disk I/O Consumers:")
        processes_with_disk_io = [p for p in self.processes if p.disk_io and p.disk_io.total_bytes() > 0]
        if processes_with_disk_io:
            top_disk_io = sorted(processes_with_disk_io, key=lambda p: p.disk_io.total_bytes(), reverse=True)[:5]
            for i, proc in enumerate(top_disk_io, 1):
                print(f"{i}. {proc.name} (PID: {proc.pid}) - {proc.disk_io.total_bytes() / 1024:.1f} KB")
        else:
            print("No disk I/O data available")
        
        # Show top network connection consumers
        print("\nTop 5 Network Connection Consumers:")
        processes_with_network_io = [p for p in self.processes if p.network_io and p.network_io.total_connections() > 0]
        if processes_with_network_io:
            top_network_io = sorted(processes_with_network_io, key=lambda p: p.network_io.total_connections(), reverse=True)[:5]
            for i, proc in enumerate(top_network_io, 1):
                connection_summary = proc.network_io.get_connection_summary()
                print(f"{i}. {proc.name} (PID: {proc.pid}) - {connection_summary}")
        else:
            print("No network connection data available")
    
    def _display_top_processes(self, count: int) -> None:
        """Display top N processes by CPU usage."""
        # Validate input
        if count <= 0:
            print("Error: Count must be a positive integer")
            return
        
        if count > len(self.processes):
            print(f"Warning: Requested {count} processes, but only {len(self.processes)} available")
            count = len(self.processes)
        
        print(f"\n" + "="*80)
        print(f"TOP {count} PROCESSES BY CPU USAGE")
        print("="*80)
        
        # Sort by CPU usage
        top_processes = sorted(self.processes, key=lambda p: p.cpu_percent, reverse=True)[:count]
        
        if not top_processes:
            print("No processes found to display")
            return
        
        table_data = []
        for i, proc in enumerate(top_processes, 1):
            table_data.append([
                i,
                proc.pid,
                proc.name,
                f"{proc.cpu_percent:.1f}%",
                f"{proc.memory_mb:.1f} MB",
                proc.username
            ])
        
        headers = ["Rank", "PID", "Name", "CPU %", "Memory", "User"]
        table = tabulate(table_data, headers=headers, tablefmt="grid")
        
        print(table)
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name by PID."""
        for proc in self.processes:
            if proc.pid == pid:
                return proc.name
        return "Unknown"
    
    def _start_logging(self, duration: Optional[int], interval: int, output_dir: str) -> None:
        """Start continuous logging of process data."""
        logging_manager = LoggingManager(output_dir=output_dir, log_interval=interval)
        logging_manager.start_continuous_logging(duration=duration)


def main():
    """Main entry point for the application."""
    parser = argparse.ArgumentParser(
        description="Windows Process Monitor - View and analyze running processes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # List all processes
  python main.py --hierarchy        # Show process hierarchy
  python main.py --summary         # Show system resource summary
  python main.py --top 10          # Show top 10 processes by CPU
  python main.py --log 60          # Log for 60 seconds
  python main.py --log 300 --log-interval 10  # Log for 5 minutes every 10 seconds
        """
    )
    
    parser.add_argument(
        "--hierarchy", 
        action="store_true",
        help="Display process hierarchy (parent-child relationships)"
    )
    
    parser.add_argument(
        "--summary",
        action="store_true", 
        help="Display system resource summary"
    )
    
    parser.add_argument(
        "--top",
        type=int,
        metavar="N",
        help="Display top N processes by CPU usage"
    )
    
    parser.add_argument(
        "--log",
        type=int,
        metavar="SECONDS",
        help="Start continuous logging for specified duration in seconds"
    )
    
    parser.add_argument(
        "--log-interval",
        type=int,
        default=5,
        metavar="SECONDS",
        help="Logging interval in seconds (default: 5)"
    )
    
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        metavar="DIRECTORY",
        help="Directory to save log files (default: logs)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.top is not None and args.top <= 0:
        print("Error: --top must be a positive integer")
        sys.exit(1)
    
    # Create and run CLI
    cli = ProcessMonitorCLI()
    cli.run(args)


if __name__ == "__main__":
    main()
