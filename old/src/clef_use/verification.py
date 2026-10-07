import hashlib
import time
from collections import deque

from PIL import ImageChops, ImageFilter, ImageOps, ImageStat

from .schema import BoundingBox, Frame


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


class VisualWaitResult:
    def __init__(self, state, frame, polls, elapsed_ms, changed=False, verification_ms=0):
        self.state, self.frame = state, frame
        self.polls, self.elapsed_ms, self.changed = polls, elapsed_ms, changed
        self.verification_ms = verification_ms

    def metrics(self):
        return {
            "visual_wait_state": self.state,
            "wait_frames": self.polls,
            "wait_ms": self.elapsed_ms,
            "related_change": self.changed,
            "verification_ms": self.verification_ms,
        }


def same_context(before, after):
    return (
        before.image.size,
        before.origin,
        before.logical_size,
        before.foreground_window,
        before.foreground_bounds,
    ) == (
        after.image.size,
        after.origin,
        after.logical_size,
        after.foreground_window,
        after.foreground_bounds,
    )


def region_pixels(frame, roi=None):
    image = frame.image
    if roi is not None:
        width, height = image.size
        image = image.crop(
            (
                int(roi.x1 * width),
                int(roi.y1 * height),
                max(int(roi.x1 * width) + 1, int(roi.x2 * width)),
                max(int(roi.y1 * height) + 1, int(roi.y2 * height)),
            )
        )
    return image if image.mode == "RGB" else image.convert("RGB")


def region_change_count(before, after, roi=None):
    if not same_context(before, after):
        return before.image.width * before.image.height
    a, b = region_pixels(before, roi), region_pixels(after, roi)
    # Preserve small glyphs/controls rather than averaging a downsampled full screen.
    difference = ImageChops.difference(a, b)
    channels = difference.split()
    maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
    histogram = maximum.histogram()
    return sum(histogram[21:])


def region_changed(before, after, roi=None):
    return region_change_count(before, after, roi) >= 4


def content_changed(before, after, roi):
    def edges(frame):
        image = region_pixels(frame, roi).convert("L").filter(ImageFilter.FIND_EDGES)
        if image.width <= 2 or image.height <= 2:
            return image
        image = image.crop((1, 1, image.width - 1, image.height - 1))
        return ImageOps.autocontrast(image).point(lambda pixel: 255 if pixel > 64 else 0)

    return sum(ImageChops.difference(edges(before), edges(after)).histogram()[1:]) >= 4


def foreground_region(frame):
    if frame.foreground_bounds is None:
        return None
    left, top, right, bottom = frame.foreground_bounds
    width, height = frame.image.size
    x1, y1 = max(0, (left - frame.origin[0]) / width), max(0, (top - frame.origin[1]) / height)
    x2, y2 = min(1, (right - frame.origin[0]) / width), min(1, (bottom - frame.origin[1]) / height)
    if x1 >= x2 or y1 >= y2:
        return None
    return BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)


def text_effect(objects, target, value):
    if target is None:
        return "UNVERIFIED"
    texts = [
        obj
        for obj in objects
        if obj.role == "text"
        and obj.label
        and target.bbox.x1 <= obj.bbox.center()[0] <= target.bbox.x2
        and target.bbox.y1 <= obj.bbox.center()[1] <= target.bbox.y2
    ]
    texts.sort(key=lambda obj: (obj.bbox.y1, obj.bbox.x1))
    if not texts:
        return "UNVERIFIED"
    return (
        "VISIBLE_TEXT_MATCH" if " ".join(obj.label for obj in texts) == value else "TEXT_MISMATCH"
    )


class VisualWaiter:
    """Wait for relevant change and stable pixels; never certify semantic success."""

    def __init__(self, timeout=5, interval=0.05, stable_samples=2, clock=None, pause=None):
        import time

        self.timeout, self.interval, self.stable_samples = timeout, interval, stable_samples
        self.clock = clock or time.monotonic
        self.pause = pause or (lambda event, seconds: event.wait(seconds))

    def wait(self, capture, before, roi, cancelled, *, require_change=True, predicate=None):
        started = self.clock()
        previous, changed, stable, polls = before, False, 0, 0
        check_started = time.perf_counter()
        already_true = predicate is not None and predicate(before)
        verification_ms = (time.perf_counter() - check_started) * 1000

        def result(state):
            return VisualWaitResult(
                state, previous, polls, (self.clock() - started) * 1000, changed, verification_ms
            )

        while True:
            if cancelled.is_set():
                return result("CANCELLED")
            fresh = capture.capture()
            polls += 1
            if cancelled.is_set():
                return result("CANCELLED")
            check_started = time.perf_counter()
            if not same_context(before, fresh):
                previous = fresh
                verification_ms += (time.perf_counter() - check_started) * 1000
                return result("CONTEXT_CHANGED")
            changed |= region_changed(before, fresh, roi)
            same = not region_changed(previous, fresh, roi)
            stable = stable + 1 if same else 0
            previous = fresh
            expected = predicate(fresh) if predicate else (changed or not require_change)
            verification_ms += (time.perf_counter() - check_started) * 1000
            if expected and stable >= self.stable_samples:
                return result("ALREADY_TRUE" if already_true else "STABLE")
            elapsed = self.clock() - started
            if elapsed >= self.timeout:
                if (
                    changed
                    and predicate is not None
                    and stable >= self.stable_samples
                    and not expected
                ):
                    return result("CONDITION_UNMET")
                return result("UNSTABLE" if changed else "NO_CHANGE")
            if self.pause(cancelled, min(self.interval, self.timeout - elapsed)):
                return result("CANCELLED")
