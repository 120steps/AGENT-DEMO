"""Persistent, recoverable publication of approved local MOCK draft files.

Approval belongs to the graph. This ledger binds an operation to immutable bytes
and one controlled path; it never grants permission merely from an operation ID.
"""

import hashlib
import json
import os
import re
import sqlite3
import stat
import tempfile
from collections.abc import Callable
from pathlib import Path
from threading import RLock


class OperationError(ValueError):
    """An operation cannot safely be executed or recovered."""


def canonical_payload(payload: dict) -> bytes:
    """Return the exact UTF-8 JSON bytes bound to an operation, rejecting NaN."""
    if not isinstance(payload, dict):
        raise OperationError("operation payload must be a JSON object")
    try:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2)
    except (ValueError, TypeError) as exc:
        raise OperationError("operation payload is not valid finite JSON") from exc
    return (text + "\n").encode("utf-8")


def _no_links(path: Path) -> None:
    """Reject symlinks and Windows junctions in an existing path or its parents."""
    for component in (path, *path.parents):
        try:
            attributes = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(attributes.st_mode) or (
            getattr(attributes, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        ):
            raise OperationError("symlinks and junctions are not permitted")


def _digest_file(path: Path) -> str:
    _no_links(path)
    if not path.is_file():
        raise OperationError("operation artifact is missing or is not a regular file")
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class OperationLedger:
    """SQLite intent record plus non-overwriting, atomic local-file publication.

    The output root must be the caller project's ``outputs/phase05`` directory.
    A committed ``prepared`` intent precedes publication. A later execution can
    complete that intent after verifying the published bytes, including after a
    process crash between publication and recording ``completed``.
    """

    def __init__(self, db_path: Path, output_root: Path, *, artifact_kind="review_json"):
        output_root = Path(os.path.abspath(output_root))
        allowed = {"review_json": ("phase05", ".json"), "soc_excel": ("soc", ".xlsx")}
        if artifact_kind not in allowed:
            raise OperationError("unapproved artifact kind")
        name, self.suffix = allowed[artifact_kind]
        if output_root.name != name or output_root.parent.name != "outputs":
            raise OperationError(f"output root must be the project outputs/{name} directory")
        _no_links(output_root)
        output_root.mkdir(parents=True, exist_ok=True)
        self.output_root = output_root.resolve()
        db_path = Path(os.path.abspath(db_path))
        _no_links(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path.resolve()
        self._lock = RLock()
        self.connection = sqlite3.connect(
            self.db_path, timeout=15, isolation_level=None, check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS phase05_operations (
                operation_id TEXT PRIMARY KEY,
                target_path TEXT NOT NULL UNIQUE,
                sha256 TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('prepared', 'completed')),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                completed_at TEXT
            )"""
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    @staticmethod
    def _validate_id(operation_id: str) -> None:
        if not isinstance(operation_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", operation_id
        ):
            raise OperationError("invalid operation_id")

    def _target(self, operation_id: str, target_path: str | Path) -> Path:
        self._validate_id(operation_id)
        path = Path(target_path)
        expected = self.output_root / f"{operation_id}{self.suffix}"
        if not path.is_absolute():
            if path != Path(f"{operation_id}{self.suffix}"):
                raise OperationError("relative targets must be the controlled artifact filename")
            path = self.output_root / path
        # Check lexical segments before resolving: traversal is forbidden even if
        # it happens to resolve back into the allowed directory.
        if ".." in path.parts:
            raise OperationError("path traversal is not permitted")
        _no_links(path)
        if path.resolve() != expected:
            raise OperationError("target must be outputs/phase05/<operation_id>.json")
        return expected

    def get(self, operation_id: str) -> dict | None:
        self._validate_id(operation_id)
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM phase05_operations WHERE operation_id = ?", (operation_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def _verify_binding(record: dict, target: Path, sha256: str) -> None:
        if record["target_path"] != str(target) or record["sha256"] != sha256:
            raise OperationError("operation_id is already bound to different content or target")

    def _publish(self, operation_id: str, target: Path, payload: bytes, sha256: str) -> None:
        _no_links(self.output_root)
        _no_links(target)
        if target.exists():
            if _digest_file(target) != sha256:
                raise OperationError("existing artifact conflicts with the prepared operation")
            return
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{operation_id}.", suffix=".tmp", dir=self.output_root
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            # Unlike os.replace(), link never overwrites an existing destination.
            # Source and destination are in the same directory/filesystem.
            try:
                os.link(temporary, target)
            except FileExistsError:
                if _digest_file(target) != sha256:
                    raise OperationError("artifact appeared with conflicting bytes") from None
        finally:
            temporary.unlink(missing_ok=True)
        if _digest_file(target) != sha256:
            raise OperationError("published artifact checksum does not match its intent")

    def execute(
        self,
        operation_id: str,
        payload: dict,
        target_path: str | Path,
        *,
        after_publish: Callable[[], None] | None = None,
    ) -> dict:
        # Graph nodes may run in worker threads. Disabling SQLite's thread check
        # alone would permit interleaved transactions on this shared connection.
        with self._lock:
            return self._execute_locked(
                operation_id, canonical_payload(payload), target_path, after_publish=after_publish
            )

    def execute_bytes(self, operation_id, content, target_path, *, after_publish=None):
        """Reuse the same durable intent and recovery for a caller-approved XLSX."""
        if self.suffix != ".xlsx" or not isinstance(content, bytes):
            raise OperationError("binary publication is restricted to SOC Excel")
        with self._lock:
            return self._execute_locked(
                operation_id, content, target_path, after_publish=after_publish
            )

    def _execute_locked(
        self,
        operation_id: str,
        payload: bytes,
        target_path: str | Path,
        *,
        after_publish: Callable[[], None] | None = None,
    ) -> dict:
        target = self._target(operation_id, target_path)
        content = payload
        sha256 = hashlib.sha256(content).hexdigest()

        # The intent is durably committed separately from publication so a crash
        # cannot leave an unbound file that we later blindly trust.
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            record = self.get(operation_id)
            if record:
                self._verify_binding(record, target, sha256)
            else:
                if target.exists():
                    raise OperationError("preexisting artifact has no trusted operation record")
                self.connection.execute(
                    """INSERT INTO phase05_operations
                       (operation_id, target_path, sha256, status) VALUES (?, ?, ?, 'prepared')""",
                    (operation_id, str(target), sha256),
                )
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise

        # Serialize local writers around verification/publication/completion.
        # This does not claim a distributed exactly-once guarantee.
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            record = self.get(operation_id)
            self._verify_binding(record, target, sha256)
            reused = record["status"] == "completed" or target.exists()
            if record["status"] == "completed":
                if _digest_file(target) != sha256:
                    raise OperationError("completed operation artifact has been changed")
            else:
                self._publish(operation_id, target, content, sha256)
                if after_publish is not None:
                    after_publish()
                self.connection.execute(
                    """UPDATE phase05_operations SET status = 'completed',
                       completed_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                       WHERE operation_id = ? AND status = 'prepared'""",
                    (operation_id,),
                )
            self.connection.execute("COMMIT")
        except BaseException:
            self.connection.execute("ROLLBACK")
            raise
        return {
            "operation_id": operation_id,
            "path": str(target),
            "status": "completed",
            "sha256": sha256,
            "reused": reused,
        }
