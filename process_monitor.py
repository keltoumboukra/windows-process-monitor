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
                
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Skip processes we can't access
                continue
        
        self.processes = processes
        self._build_parent_child_map()
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
            # Find processes with no parent (system processes)
            root_processes = [p.pid for p in self.processes if p.parent_pid is None]
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
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'memory_available_gb': psutil.virtual_memory().available / (1024**3),
            'memory_total_gb': psutil.virtual_memory().total / (1024**3),
            'disk_usage_percent': psutil.disk_usage('/').percent if sys.platform != 'win32' else psutil.disk_usage('C:').percent
        }
