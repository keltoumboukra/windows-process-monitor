"""
Windows Process Monitor - Core Module

This module provides the core functionality for monitoring Windows processes,
including process enumeration, resource tracking, and parent-child relationships.
"""

import psutil
import sys
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class DiskIO:
    """Data class to hold disk I/O information for a process."""
    read_bytes: int = 0
    write_bytes: int = 0
    read_count: int = 0
    write_count: int = 0
    
    def total_bytes(self) -> int:
        """Get total bytes read and written."""
        return self.read_bytes + self.write_bytes
    
    def total_operations(self) -> int:
        """Get total number of read and write operations."""
        return self.read_count + self.write_count


@dataclass
class NetworkIO:
    """Data class to hold network I/O information for a process."""
    connections_count: int = 0
    established_connections: int = 0
    listening_connections: int = 0
    connection_states: Dict[str, int] = None
    
    def __post_init__(self):
        """Initialize connection_states if not provided."""
        if self.connection_states is None:
            self.connection_states = {}
    
    def total_connections(self) -> int:
        """Get total number of network connections."""
        return self.connections_count
    
    def get_connection_summary(self) -> str:
        """Get a summary of connection states."""
        if not self.connection_states:
            return f"{self.connections_count} connections"
        
        summary_parts = []
        for state, count in self.connection_states.items():
            if count > 0:
                summary_parts.append(f"{count} {state}")
        
        return ", ".join(summary_parts) if summary_parts else f"{self.connections_count} connections"


@dataclass
class ProcessInfo:
    """Data class to hold process information."""
    pid: int
    name: str
    status: str
    cpu_percent: float
    memory_mb: float
    parent_pid: Optional[int]
    create_time: datetime
    username: str
    disk_io: Optional[DiskIO] = None
    network_io: Optional[NetworkIO] = None


class ProcessMonitor:
    """Main class for monitoring Windows processes."""
    
    def __init__(self):
        """Initialize the process monitor."""
        self.processes: List[ProcessInfo] = []
        self.parent_child_map: Dict[int, List[int]] = {}
    
    def get_all_processes(self) -> List[ProcessInfo]:
        """
        Get information about all running processes.
        
        Returns:
            List of ProcessInfo objects for all accessible processes.
        """
        processes = []
        access_denied_count = 0
        no_such_process_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                       'memory_info', 'ppid', 'create_time', 'username']):
            try:
                proc_info = proc.info
                
                # Calculate memory usage in MB
                memory_mb = proc_info['memory_info'].rss / (1024 * 1024) if proc_info['memory_info'] else 0.0
                
                process_info = ProcessInfo(
                    pid=proc_info['pid'],
                    name=proc_info['name'],
                    status=proc_info['status'],
                    cpu_percent=proc_info['cpu_percent'] or 0.0,
                    memory_mb=memory_mb,
                    parent_pid=proc_info['ppid'],
                    create_time=datetime.fromtimestamp(proc_info['create_time']),
                    username=proc_info['username'] or 'Unknown'
                )
                
                processes.append(process_info)
                
            except psutil.AccessDenied:
                access_denied_count += 1
                continue
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                no_such_process_count += 1
                continue
        
        self.processes = processes
        self._build_parent_child_map()
        
        # Log access issues if significant
        if access_denied_count > 0:
            print(f"Warning: {access_denied_count} processes could not be accessed (permission denied)")
            if access_denied_count > len(processes) * 0.5:  # More than 50% inaccessible
                print("Consider running as administrator for full process access")
        
        if no_such_process_count > 0:
            print(f"Info: {no_such_process_count} processes terminated during scan")
        
        return processes
    
    def _build_parent_child_map(self):
        """Build a mapping of parent PIDs to their child PIDs."""
        self.parent_child_map = {}
        
        for proc in self.processes:
            if proc.parent_pid is not None:
                if proc.parent_pid not in self.parent_child_map:
                    self.parent_child_map[proc.parent_pid] = []
                self.parent_child_map[proc.parent_pid].append(proc.pid)
    
    def get_process_hierarchy(self, root_pid: Optional[int] = None) -> Dict[int, List[int]]:
        """
        Get the process hierarchy starting from a root process.
        
        Args:
            root_pid: Starting PID for hierarchy. If None, starts from system processes.
            
        Returns:
            Dictionary mapping parent PIDs to lists of child PIDs.
        """
        if root_pid is None:
            # Find processes with no parent (system processes) or PID 1 (init/launchd)
            root_processes = [p.pid for p in self.processes if p.parent_pid is None or p.pid == 1]
            
            # If no root processes found, use the process with the lowest PID as root
            if not root_processes:
                root_processes = [min(p.pid for p in self.processes)]
            
            hierarchy = {}
            for root_pid in root_processes:
                hierarchy.update(self._get_children_recursive(root_pid))
            return hierarchy
        else:
            return self._get_children_recursive(root_pid)
    
    def _get_children_recursive(self, parent_pid: int) -> Dict[int, List[int]]:
        """Recursively get all children of a parent process."""
        hierarchy = {}
        if parent_pid in self.parent_child_map:
            children = self.parent_child_map[parent_pid]
            hierarchy[parent_pid] = children
            
            for child_pid in children:
                hierarchy.update(self._get_children_recursive(child_pid))
        
        return hierarchy
    
    def get_system_summary(self) -> Dict[str, float]:
        """
        Get system-wide resource usage summary.
        
        Returns:
            Dictionary with system resource information.
        """
        summary = {}
        
        try:
            summary['cpu_percent'] = psutil.cpu_percent(interval=1)
        except Exception:
            summary['cpu_percent'] = 0.0
        
        try:
            memory = psutil.virtual_memory()
            summary['memory_percent'] = memory.percent
            summary['memory_available_gb'] = memory.available / (1024**3)
            summary['memory_total_gb'] = memory.total / (1024**3)
        except Exception:
            summary['memory_percent'] = 0.0
            summary['memory_available_gb'] = 0.0
            summary['memory_total_gb'] = 0.0
        
        try:
            if sys.platform == 'win32':
                summary['disk_usage_percent'] = psutil.disk_usage('C:').percent
            else:
                summary['disk_usage_percent'] = psutil.disk_usage('/').percent
        except Exception:
            summary['disk_usage_percent'] = 0.0
        
        return summary
    
    def get_disk_io(self, pid: int) -> Optional[DiskIO]:
        """
        Get disk I/O information for a specific process.
        
        Args:
            pid: Process ID to get disk I/O for
            
        Returns:
            DiskIO object with disk I/O information, or None if not available
        """
        try:
            proc = psutil.Process(pid)
            io_counters = proc.io_counters()
            
            if io_counters:
                return DiskIO(
                    read_bytes=io_counters.read_bytes,
                    write_bytes=io_counters.write_bytes,
                    read_count=io_counters.read_count,
                    write_count=io_counters.write_count
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            # Process doesn't exist, no access, or I/O counters not available
            pass
        
        return None
    
    def get_network_io(self, pid: int) -> Optional[NetworkIO]:
        """
        Get network connection information for a specific process.
        
        Args:
            pid: Process ID to get network connections for
            
        Returns:
            NetworkIO object with connection information, or None if not available
        """
        try:
            proc = psutil.Process(pid)
            connections = proc.connections()
            
            if connections:
                # Count connections by state
                connection_states = {}
                established_count = 0
                listening_count = 0
                
                for conn in connections:
                    state = conn.status
                    if state in connection_states:
                        connection_states[state] += 1
                    else:
                        connection_states[state] = 1
                    
                    # Count specific states
                    if state == 'ESTABLISHED':
                        established_count += 1
                    elif state == 'LISTEN':
                        listening_count += 1
                
                return NetworkIO(
                    connections_count=len(connections),
                    established_connections=established_count,
                    listening_connections=listening_count,
                    connection_states=connection_states
                )
        except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
            # Process doesn't exist, no access, or network info not available
            pass
        
        return None
    
    def get_all_processes_with_io(self) -> List[ProcessInfo]:
        """
        Get information about all running processes including I/O data.
        
        Returns:
            List of ProcessInfo objects with I/O information for all accessible processes.
        """
        processes = []
        access_denied_count = 0
        no_such_process_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 
                                       'memory_info', 'ppid', 'create_time', 'username']):
            try:
                proc_info = proc.info
                
                # Calculate memory usage in MB
                memory_mb = proc_info['memory_info'].rss / (1024 * 1024) if proc_info['memory_info'] else 0.0
                
                # Get I/O information
                disk_io = self.get_disk_io(proc_info['pid'])
                network_io = self.get_network_io(proc_info['pid'])
                
                process_info = ProcessInfo(
                    pid=proc_info['pid'],
                    name=proc_info['name'],
                    status=proc_info['status'],
                    cpu_percent=proc_info['cpu_percent'] or 0.0,
                    memory_mb=memory_mb,
                    parent_pid=proc_info['ppid'],
                    create_time=datetime.fromtimestamp(proc_info['create_time']),
                    username=proc_info['username'] or 'Unknown',
                    disk_io=disk_io,
                    network_io=network_io
                )
                
                processes.append(process_info)
                
            except psutil.AccessDenied:
                access_denied_count += 1
                continue
            except (psutil.NoSuchProcess, psutil.ZombieProcess):
                no_such_process_count += 1
                continue
        
        self.processes = processes
        self._build_parent_child_map()
        
        # Log access issues if significant
        if access_denied_count > 0:
            print(f"Warning: {access_denied_count} processes could not be accessed (permission denied)")
            if access_denied_count > len(processes) * 0.5:  # More than 50% inaccessible
                print("Consider running as administrator for full process access")
        
        if no_such_process_count > 0:
            print(f"Info: {no_such_process_count} processes terminated during scan")
        
        return processes
