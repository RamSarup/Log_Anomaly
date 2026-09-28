"""Incremental tail-following for an append-only log file."""

import logging
import os
from collections.abc import Iterator
from pathlib import Path
from threading import Event

logger = logging.getLogger(__name__)


class LogTailer:
    """Read complete appended lines while retaining the current byte offset."""

    def __init__(self, path: str | Path, poll_interval: float = 0.1) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be positive")
        self.path = Path(path)
        self.poll_interval = poll_interval
        self.offset = 0
        self._identity: tuple[int, int] | None = None
        self._partial = b""
        self._stop_event = Event()

    def _reset_for_file(self, identity: tuple[int, int]) -> None:
        if self._partial:
            logger.warning("Discarding an incomplete line because the log file rotated")
        self._partial = b""
        self._identity = identity
        self.offset = 0

    def read_available(self) -> list[str]:
        """Return newly completed lines without blocking or rereading old bytes."""
        try:
            with self.path.open("rb") as log_file:
                file_stat = os.fstat(log_file.fileno())
                identity = (file_stat.st_dev, file_stat.st_ino)
                if identity != self._identity or file_stat.st_size < self.offset:
                    self._reset_for_file(identity)
                log_file.seek(self.offset)
                chunk = log_file.read()
                self.offset = log_file.tell()
        except FileNotFoundError:
            return []

        if not chunk:
            return []

        self._partial += chunk
        pieces = self._partial.split(b"\n")
        self._partial = pieces.pop()
        lines: list[str] = []
        for piece in pieces:
            try:
                lines.append(piece.rstrip(b"\r").decode("utf-8"))
            except UnicodeDecodeError as error:
                logger.warning("Skipping undecodable log line at byte offset %d: %s", self.offset, error)
        return lines

    def follow(self) -> Iterator[str]:
        """Yield each newly appended complete line, polling until stopped."""
        self._stop_event.clear()
        while not self._stop_event.is_set():
            for line in self.read_available():
                yield line
            self._stop_event.wait(self.poll_interval)

    def stop(self) -> None:
        """Stop an active ``follow`` iterator."""
        self._stop_event.set()

    def close(self) -> None:
        """Close the current file handle and stop active polling."""
        self.stop()

    def __enter__(self) -> "LogTailer":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()