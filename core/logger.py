# core/logger.py

from pathlib import Path

class Logger:
    def __init__(self, mode: str, output_file: Path):
        self.mode = mode
        self.output_file = output_file
        self._printed = set()

    def _should_print(self, level):
        if self.mode == "debug":
            return True
        if self.mode == "verbose":
            return level in ("info", "warn", "discover")
        if self.mode == "discovery":
            return level == "discover"
        if self.mode == "quiet":
            return False
        return False

    def info(self, msg: str):
        if self._should_print("info"):
            print(msg, flush=True)

    def warn(self, msg: str):
        if self._should_print("warn"):
            print(msg, flush=True)

    def discover(self, tag: str, value: str):
        line = f"[{tag}] {value}"
        if self._should_print("discover") and line not in self._printed:
            print(line, flush=True)
            self._printed.add(line)

        try:
            with open(self.output_file, "a") as fh:
                fh.write(line + "\n")
        except Exception:
            pass
