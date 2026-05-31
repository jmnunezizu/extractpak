from __future__ import annotations


class BuildProgress:
    def __init__(self, total: int, enabled: bool = False, width: int = 24) -> None:
        self.total = total
        self.enabled = enabled
        self.width = width
        self.current = 0

    def _bar(self) -> str:
        filled = int(self.width * self.current / self.total)
        return "#" * filled + "-" * (self.width - filled)

    def start(self, label: str) -> None:
        if not self.enabled:
            return
        print(f"[{self._bar()}] {self.current}/{self.total} {label}...")

    def done(self, label: str) -> None:
        if not self.enabled:
            return
        self.current += 1
        print(f"[{self._bar()}] {self.current}/{self.total} {label} done")

    def step(self, label: str) -> None:
        self.done(label)
