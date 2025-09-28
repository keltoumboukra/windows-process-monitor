"""
Logging Manager for Windows Process Monitor

This module provides functionality to log process monitoring data to CSV and JSON formats
with configurable intervals and output options.
"""

import csv
import json
import os
import time
from datetime import datetime
from typing import List, Dict, Optional, Union
from pathlib import Path
from process_monitor import ProcessInfo, ProcessMonitor


class LoggingManager:
    """Manages logging of process monitoring data to various formats."""
    
    def __init__(self, output_dir: str = "logs", log_interval: int = 5):
        """
        Initialize the logging manager.
        
        Args:
            output_dir: Directory to save log files
            log_interval: Interval between log entries in seconds
        """
        self.output_dir = Path(output_dir)
        self.log_interval = log_interval
        self.monitor = ProcessMonitor()
        
        # Create output directory if it doesn't exist
        self.output_dir.mkdir(exist_ok=True)
        
        # Log file paths
        self.csv_file = self.output_dir / "process_monitor.csv"
        self.json_file = self.output_dir / "process_monitor.json"
        
        # Initialize log files with headers
        self._initialize_csv_file()
        self._initialize_json_file()
    
    def _initialize_csv_file(self):
        """Initialize CSV file with headers."""
        if not self.csv_file.exists():
            with open(self.csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp', 'pid', 'name', 'status', 'cpu_percent', 'memory_mb',
                    'parent_pid', 'username', 'disk_read_bytes', 'disk_write_bytes',
                    'disk_read_count', 'disk_write_count', 'network_connections',
                    'network_established', 'network_listening'
                ])
    
    def _initialize_json_file(self):
        """Initialize JSON file with metadata."""
        if not self.json_file.exists():
            metadata = {
                "log_start_time": datetime.now().isoformat(),
                "log_interval_seconds": self.log_interval,
                "entries": []
            }
            with open(self.json_file, 'w') as f:
                json.dump(metadata, f, indent=2)
    
    def log_processes(self, processes: List[ProcessInfo]) -> None:
        """
        Log process information to both CSV and JSON files.
        
        Args:
            processes: List of ProcessInfo objects to log
        """
        timestamp = datetime.now().isoformat()
        
        # Log to CSV
        self._log_to_csv(processes, timestamp)
        
        # Log to JSON
        self._log_to_json(processes, timestamp)
    
    def _log_to_csv(self, processes: List[ProcessInfo], timestamp: str) -> None:
        """Log process data to CSV file."""
        with open(self.csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            
            for proc in processes:
                # Extract disk I/O data
                disk_read_bytes = proc.disk_io.read_bytes if proc.disk_io else 0
                disk_write_bytes = proc.disk_io.write_bytes if proc.disk_io else 0
                disk_read_count = proc.disk_io.read_count if proc.disk_io else 0
                disk_write_count = proc.disk_io.write_count if proc.disk_io else 0
                
                # Extract network I/O data
                network_connections = proc.network_io.total_connections() if proc.network_io else 0
                network_established = proc.network_io.established_connections if proc.network_io else 0
                network_listening = proc.network_io.listening_connections if proc.network_io else 0
                
                writer.writerow([
                    timestamp,
                    proc.pid,
                    proc.name,
                    proc.status,
                    f"{proc.cpu_percent:.2f}",
                    f"{proc.memory_mb:.2f}",
                    proc.parent_pid or "",
                    proc.username,
                    disk_read_bytes,
                    disk_write_bytes,
                    disk_read_count,
                    disk_write_count,
                    network_connections,
                    network_established,
                    network_listening
                ])
    
    def _log_to_json(self, processes: List[ProcessInfo], timestamp: str) -> None:
        """Log process data to JSON file."""
        # Read existing JSON data
        with open(self.json_file, 'r') as f:
            data = json.load(f)
        
        # Create entry for this timestamp
        entry = {
            "timestamp": timestamp,
            "process_count": len(processes),
            "processes": []
        }
        
        for proc in processes:
            process_data = {
                "pid": proc.pid,
                "name": proc.name,
                "status": proc.status,
                "cpu_percent": round(proc.cpu_percent, 2),
                "memory_mb": round(proc.memory_mb, 2),
                "parent_pid": proc.parent_pid,
                "username": proc.username,
                "disk_io": {
                    "read_bytes": proc.disk_io.read_bytes if proc.disk_io else 0,
                    "write_bytes": proc.disk_io.write_bytes if proc.disk_io else 0,
                    "read_count": proc.disk_io.read_count if proc.disk_io else 0,
                    "write_count": proc.disk_io.write_count if proc.disk_io else 0
                },
                "network_io": {
                    "connections": proc.network_io.total_connections() if proc.network_io else 0,
                    "established": proc.network_io.established_connections if proc.network_io else 0,
                    "listening": proc.network_io.listening_connections if proc.network_io else 0,
                    "connection_states": proc.network_io.connection_states if proc.network_io else {}
                }
            }
            entry["processes"].append(process_data)
        
        # Add entry to data
        data["entries"].append(entry)
        
        # Write back to file
        with open(self.json_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def start_continuous_logging(self, duration: Optional[int] = None) -> None:
        """
        Start continuous logging of process data.
        
        Args:
            duration: Duration to log in seconds. If None, logs indefinitely.
        """
        print(f"Starting continuous logging to {self.output_dir}")
        print(f"Log interval: {self.log_interval} seconds")
        print(f"CSV file: {self.csv_file}")
        print(f"JSON file: {self.json_file}")
        print("Press Ctrl+C to stop logging")
        
        start_time = time.time()
        
        try:
            while True:
                # Get current process data
                processes = self.monitor.get_all_processes_with_io()
                
                # Log the data
                self.log_processes(processes)
                
                # Check if duration limit reached
                if duration and (time.time() - start_time) >= duration:
                    print(f"\nLogging completed after {duration} seconds")
                    break
                
                # Wait for next interval
                time.sleep(self.log_interval)
                
        except KeyboardInterrupt:
            print(f"\nLogging stopped by user")
            print(f"Data saved to {self.output_dir}")
    
    def get_log_summary(self) -> Dict[str, Union[str, int]]:
        """
        Get summary information about the log files.
        
        Returns:
            Dictionary with log file information
        """
        summary = {
            "csv_file": str(self.csv_file),
            "json_file": str(self.json_file),
            "csv_exists": self.csv_file.exists(),
            "json_exists": self.json_file.exists(),
            "log_interval": self.log_interval
        }
        
        if self.csv_file.exists():
            # Count CSV entries (subtract 1 for header)
            with open(self.csv_file, 'r') as f:
                summary["csv_entries"] = sum(1 for line in f) - 1
        
        if self.json_file.exists():
            with open(self.json_file, 'r') as f:
                data = json.load(f)
                summary["json_entries"] = len(data.get("entries", []))
                summary["log_start_time"] = data.get("log_start_time", "Unknown")
        
        return summary
