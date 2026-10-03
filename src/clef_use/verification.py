import hashlib
from collections import deque

from PIL import ImageChops, ImageStat

from .schema import Frame


class VisualVerifier:
    def change(self, before: Frame, after: Frame) -> float:
        a = before.image.convert("RGB").resize((160, 90))
        b = after.image.convert("RGB").resize((160, 90))
        return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / (3 * 255)

    def fingerprint(self, frame: Frame) -> bytes:
        values = bytes(p // 16 for p in frame.image.convert("L").resize((320, 180)).tobytes())
        return hashlib.sha256(values).digest()


class ProgressTracker:
    def __init__(self, limit: int):
        self.limit = limit
        self.unchanged = 0
        self.states = deque(maxlen=limit * 3)

    def update(self, score: float, fingerprint: bytes) -> bool:
        unchanged = score < 0.002 and bool(self.states) and self.states[-1] == fingerprint
        self.unchanged = self.unchanged + 1 if unchanged else 0
        self.states.append(fingerprint)
        return self.unchanged >= self.limit or self.states.count(fingerprint) >= self.limit
