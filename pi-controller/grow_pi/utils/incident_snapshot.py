#!/usr/bin/env python3
"""
Incident Snapshot Utility

Captures comprehensive system state on critical errors for debugging.
Snapshots include error details, system metrics, thread state, and sensor cache.

Version: 6.22.5
"""

import os
import json
import time
import threading
import traceback
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Incident snapshot storage directory
SNAPSHOT_DIR = Path("/var/log/grow-pi/incidents")
MAX_SNAPSHOTS = 100  # Keep only the most recent 100 snapshots


class IncidentSnapshot:
    """Captures system state on critical errors."""

    @classmethod
    def capture(cls, error: Exception, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Capture full incident snapshot.

        Args:
            error: The exception that triggered the snapshot
            context: Optional context dictionary with additional information

        Returns:
            Snapshot ID for reference (e.g., "incident_20251226_143022")
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_id = f"incident_{timestamp}"

        snapshot = {
            "id": snapshot_id,
            "timestamp": time.time(),
            "iso_timestamp": datetime.now().isoformat(),
            "error": {
                "type": type(error).__name__,
                "message": str(error),
                "traceback": traceback.format_exc()
            },
            "context": context or {},
            "system": cls._capture_system_state(),
            "threads": cls._capture_thread_state(),
            "sensor_cache": cls._capture_sensor_cache(),
            "database": cls._capture_database_state()
        }

        # Save to file
        cls._save_snapshot(snapshot_id, snapshot)

        # Cleanup old snapshots
        cls._cleanup_old_snapshots()

        logger.error(f"Incident snapshot captured: {snapshot_id}")

        return snapshot_id

    @classmethod
    def _capture_system_state(cls) -> Dict[str, Any]:
        """Capture system metrics (CPU, memory, disk, etc.)."""
        try:
            import psutil

            process = psutil.Process()

            return {
                "cpu": {
                    "percent": psutil.cpu_percent(interval=0.1),
                    "count": psutil.cpu_count(),
                    "load_average": list(os.getloadavg())
                },
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                    "used": psutil.virtual_memory().used
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "used": psutil.disk_usage('/').used,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                },
                "process": {
                    "pid": process.pid,
                    "memory_percent": process.memory_percent(),
                    "num_threads": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "connections": len(process.connections()),
                    "create_time": process.create_time()
                },
                "boot_time": psutil.boot_time()
            }
        except Exception as e:
            logger.warning(f"Failed to capture system state: {e}")
            return {"error": str(e)}

    @classmethod
    def _capture_thread_state(cls) -> list:
        """Capture information about all active threads."""
        threads = []
        try:
            for t in threading.enumerate():
                threads.append({
                    "name": t.name,
                    "daemon": t.daemon,
                    "alive": t.is_alive(),
                    "ident": t.ident
                })
        except Exception as e:
            logger.warning(f"Failed to capture thread state: {e}")
            threads.append({"error": str(e)})

        return threads

    @classmethod
    def _capture_sensor_cache(cls) -> Dict[str, Any]:
        """Capture sensor cache state for debugging."""
        try:
            from grow_pi.utils.sensor_cache import get_cache_status
            return get_cache_status()
        except Exception as e:
            logger.warning(f"Failed to capture sensor cache: {e}")
            return {"error": str(e)}

    @classmethod
    def _capture_database_state(cls) -> Dict[str, Any]:
        """Capture database connection state."""
        try:
            from grow_pi.database.db import get_database

            db = get_database()
            db_path = getattr(db, 'db_path', 'unknown')

            # Get database file size if possible
            db_size = None
            if os.path.exists(db_path):
                db_size = os.path.getsize(db_path)

            return {
                "path": str(db_path),
                "size_bytes": db_size,
                "accessible": os.path.exists(db_path) if db_path != 'unknown' else False
            }
        except Exception as e:
            logger.warning(f"Failed to capture database state: {e}")
            return {"error": str(e)}

    @classmethod
    def _save_snapshot(cls, snapshot_id: str, data: Dict[str, Any]) -> None:
        """
        Save snapshot to disk.

        Args:
            snapshot_id: Unique identifier for this snapshot
            data: Snapshot data to save
        """
        try:
            # Create directory if it doesn't exist
            SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

            filepath = SNAPSHOT_DIR / f"{snapshot_id}.json"

            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)

            logger.info(f"Incident snapshot saved to: {filepath}")

        except Exception as e:
            logger.error(f"Failed to save incident snapshot: {e}")

    @classmethod
    def _cleanup_old_snapshots(cls) -> None:
        """Remove old snapshots to keep only the most recent MAX_SNAPSHOTS."""
        try:
            if not SNAPSHOT_DIR.exists():
                return

            # Get all snapshot files sorted by modification time
            snapshots = sorted(
                SNAPSHOT_DIR.glob("incident_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove old snapshots
            if len(snapshots) > MAX_SNAPSHOTS:
                for old_snapshot in snapshots[MAX_SNAPSHOTS:]:
                    try:
                        old_snapshot.unlink()
                        logger.debug(f"Removed old snapshot: {old_snapshot.name}")
                    except Exception as e:
                        logger.warning(f"Failed to remove old snapshot {old_snapshot}: {e}")

        except Exception as e:
            logger.warning(f"Failed to cleanup old snapshots: {e}")

    @classmethod
    def list_snapshots(cls) -> list:
        """
        List all available snapshots.

        Returns:
            List of snapshot IDs sorted by timestamp (newest first)
        """
        try:
            if not SNAPSHOT_DIR.exists():
                return []

            snapshots = sorted(
                SNAPSHOT_DIR.glob("incident_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            return [s.stem for s in snapshots]

        except Exception as e:
            logger.error(f"Failed to list snapshots: {e}")
            return []

    @classmethod
    def load_snapshot(cls, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a snapshot by ID.

        Args:
            snapshot_id: Snapshot identifier (e.g., "incident_20251226_143022")

        Returns:
            Snapshot data dictionary or None if not found
        """
        try:
            filepath = SNAPSHOT_DIR / f"{snapshot_id}.json"

            if not filepath.exists():
                logger.warning(f"Snapshot not found: {snapshot_id}")
                return None

            with open(filepath, 'r') as f:
                return json.load(f)

        except Exception as e:
            logger.error(f"Failed to load snapshot {snapshot_id}: {e}")
            return None
