"""Configuration manager — backup, diff, version history.

Manages device configuration snapshots, provides diff capabilities,
and maintains version history for change tracking.
"""

from __future__ import annotations

import difflib
import hashlib
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

from netopshub.models import ConfigDiff, ConfigSnapshot

logger = logging.getLogger(__name__)


class ConfigManager:
    """Manages device configuration lifecycle.

    Provides:
    - Configuration backup and storage
    - Diff between versions
    - Version history with hashing
    - Golden config baseline comparison
    """

    def __init__(self):
        self._snapshots: dict[str, list[ConfigSnapshot]] = defaultdict(list)
        self._golden_configs: dict[str, str] = {}

    def backup_config(
        self,
        device_id: str,
        config_text: str,
        source: str = "manual",
        hostname: str = "",
    ) -> ConfigSnapshot:
        """Store a configuration snapshot."""
        config_hash = hashlib.sha256(config_text.encode()).hexdigest()

        # Check if config has changed
        existing = self._snapshots.get(device_id, [])
        if existing and existing[-1].config_hash == config_hash:
            logger.debug(f"Config unchanged for {device_id}")
            return existing[-1]

        snapshot = ConfigSnapshot(
            device_id=device_id,
            device_hostname=hostname or device_id,
            config_text=config_text,
            config_hash=config_hash,
            source=source,
        )
        self._snapshots[device_id].append(snapshot)
        logger.info(f"Config backed up for {device_id} (hash: {config_hash[:12]})")
        return snapshot

    def get_latest(self, device_id: str) -> Optional[ConfigSnapshot]:
        """Get the latest configuration snapshot for a device."""
        snapshots = self._snapshots.get(device_id, [])
        return snapshots[-1] if snapshots else None

    def get_history(self, device_id: str, limit: int = 10) -> list[ConfigSnapshot]:
        """Get configuration version history for a device."""
        return self._snapshots.get(device_id, [])[-limit:]

    def diff(
        self,
        device_id: str,
        before_id: Optional[str] = None,
        after_id: Optional[str] = None,
    ) -> Optional[ConfigDiff]:
        """Generate a diff between two configuration versions.

        If IDs not specified, diffs the two most recent versions.
        """
        snapshots = self._snapshots.get(device_id, [])
        if len(snapshots) < 2:
            return None

        if before_id:
            before = next((s for s in snapshots if s.id == before_id), None)
        else:
            before = snapshots[-2]

        if after_id:
            after = next((s for s in snapshots if s.id == after_id), None)
        else:
            after = snapshots[-1]

        if not before or not after:
            return None

        diff_lines = list(difflib.unified_diff(
            before.config_text.splitlines(keepends=True),
            after.config_text.splitlines(keepends=True),
            fromfile=f"{device_id} ({before.captured_at.isoformat()})",
            tofile=f"{device_id} ({after.captured_at.isoformat()})",
            lineterm="",
        ))

        added = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))

        return ConfigDiff(
            device_id=device_id,
            before_snapshot_id=before.id,
            after_snapshot_id=after.id,
            diff_text="\n".join(diff_lines),
            lines_added=added,
            lines_removed=removed,
            lines_changed=min(added, removed),
        )

    def set_golden_config(self, device_id: str, config_text: str) -> None:
        """Set the golden (baseline) configuration for a device."""
        self._golden_configs[device_id] = config_text

    def compare_to_golden(self, device_id: str) -> Optional[str]:
        """Compare current config against golden baseline."""
        golden = self._golden_configs.get(device_id)
        latest = self.get_latest(device_id)
        if not golden or not latest:
            return None

        diff_lines = list(difflib.unified_diff(
            golden.splitlines(keepends=True),
            latest.config_text.splitlines(keepends=True),
            fromfile=f"{device_id} (golden)",
            tofile=f"{device_id} (current)",
            lineterm="",
        ))
        return "\n".join(diff_lines) if diff_lines else "Configuration matches golden baseline."

    def search_configs(self, pattern: str) -> list[dict[str, Any]]:
        """Search all configs for a pattern."""
        results = []
        for device_id, snapshots in self._snapshots.items():
            if not snapshots:
                continue
            latest = snapshots[-1]
            for i, line in enumerate(latest.config_text.splitlines()):
                if pattern.lower() in line.lower():
                    results.append({
                        "device_id": device_id,
                        "line_number": i + 1,
                        "line": line.strip(),
                    })
        return results

    @property
    def device_count(self) -> int:
        return len(self._snapshots)

    @property
    def total_snapshots(self) -> int:
        return sum(len(v) for v in self._snapshots.values())
