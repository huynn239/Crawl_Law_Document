from typing import Dict
from pathlib import Path
import json

class JsonlWriter:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def write(self, item: Dict):
        self._fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self):
        self._fh.close()
