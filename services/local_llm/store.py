"""Local model selection + install registry.

The store is the single source of truth for *which* catalog model is active and
*which* files are already on disk. It persists a tiny JSON registry inside the
models directory (default `/app/data/models`, i.e. under the mounted `data/`
volume), so the selection survives restarts and is shared by the helpdesk and
agent services when they share that volume.

It never downloads anything and never executes a command: it only reads/writes
JSON and resolves catalog filenames to paths.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .catalog import ModelOption, get_model

REGISTRY_FILENAME = 'models.json'


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelStore:
    """Thread-safe registry of installed models and the active selection."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.registry_path = self.root / REGISTRY_FILENAME
        self._lock = threading.RLock()

    # -- filesystem ------------------------------------------------------
    def ensure_dir(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    def target_path(self, model_id: str) -> Optional[Path]:
        """Where a catalog model's file lives, or None for an unknown id."""
        option = get_model(model_id)
        if option is None:
            return None
        return self.root / option.filename

    # -- registry I/O ----------------------------------------------------
    def _read_registry(self) -> dict[str, Any]:
        try:
            raw = self.registry_path.read_text(encoding='utf-8')
        except (OSError, ValueError):
            return {'selected_id': None, 'installed': {}}
        try:
            data = json.loads(raw)
        except ValueError:
            return {'selected_id': None, 'installed': {}}
        if not isinstance(data, dict):
            return {'selected_id': None, 'installed': {}}
        installed = data.get('installed')
        if not isinstance(installed, dict):
            installed = {}
        selected = data.get('selected_id')
        return {
            'selected_id': selected if isinstance(selected, str) else None,
            'installed': installed,
        }

    def _write_registry(self, data: dict[str, Any]) -> None:
        self.ensure_dir()
        tmp = self.registry_path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
        tmp.replace(self.registry_path)

    # -- queries ---------------------------------------------------------
    def is_installed(self, model_id: str) -> bool:
        with self._lock:
            path = self.target_path(model_id)
            return path is not None and path.is_file()

    def installed_ids(self) -> list[str]:
        with self._lock:
            registry = self._read_registry()
            present = []
            for model_id in registry['installed']:
                if self.is_installed(model_id):
                    present.append(model_id)
            return present

    def installed_size(self, model_id: str) -> Optional[int]:
        path = self.target_path(model_id)
        if path is None or not path.is_file():
            return None
        try:
            return path.stat().st_size
        except OSError:
            return None

    def selected_id(self) -> Optional[str]:
        with self._lock:
            registry = self._read_registry()
            selected = registry['selected_id']
            if selected and self.is_installed(selected):
                return selected
            return None

    def selected_model_path(self) -> str:
        """Absolute path of the active model, or '' when nothing is selected."""
        selected = self.selected_id()
        if not selected:
            return ''
        path = self.target_path(selected)
        return str(path) if path is not None and path.is_file() else ''

    # -- mutations -------------------------------------------------------
    def record_installed(self, model_id: str, option: ModelOption) -> None:
        with self._lock:
            registry = self._read_registry()
            registry['installed'][model_id] = {
                'filename': option.filename,
                'size_bytes': self.installed_size(model_id) or option.size_bytes,
                'completed_at': _utc_now(),
            }
            if not registry['selected_id']:
                registry['selected_id'] = model_id
            self._write_registry(registry)

    def select(self, model_id: str) -> str:
        """Make an installed model active. Raises ValueError when not installed."""
        with self._lock:
            if not self.is_installed(model_id):
                raise ValueError(f'model is not installed: {model_id}')
            registry = self._read_registry()
            registry['selected_id'] = model_id
            self._write_registry(registry)
            return model_id

    def remove(self, model_id: str) -> bool:
        """Delete an installed model's file and registry entry."""
        with self._lock:
            path = self.target_path(model_id)
            removed = False
            if path is not None and path.is_file():
                try:
                    path.unlink()
                    removed = True
                except OSError:
                    removed = False
            registry = self._read_registry()
            registry['installed'].pop(model_id, None)
            if registry['selected_id'] == model_id:
                registry['selected_id'] = None
            self._write_registry(registry)
            return removed
