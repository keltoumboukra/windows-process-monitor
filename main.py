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
            # Get all processes
            print("Scanning processes...")
            self.processes = self.monitor.get_all_processes()
            
            if not self.processes:
                print("Warning: No processes found. You may need to run as administrator.")
                return
            
            print(f"Found {len(self.processes)} processes")
            
            # Execute requested action
            if args.hierarchy:
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
            table_data.append([
                proc.pid,
                proc.name,
                proc.status,
                f"{proc.cpu_percent:.1f}%",
                f"{proc.memory_mb:.1f} MB",
                proc.parent_pid or "N/A",
                proc.username
            ])
        
        # Create table
        headers = ["PID", "Name", "Status", "CPU %", "Memory", "Parent PID", "User"]
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
