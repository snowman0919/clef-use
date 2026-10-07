"""Exact-pixel icon reuse must never leak captions onto changed controls."""

import importlib
from collections import OrderedDict
from pathlib import Path

from PIL import Image


def worker_module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "src/clef_use"))
    return importlib.import_module("model_worker")


def test_unchanged_icons_reuse_captions_but_changed_pixels_are_recognized(monkeypatch):
    worker = worker_module(monkeypatch)
    cache = OrderedDict()
    calls = []
    image = Image.new("RGB", (20, 10), "red")

    def recognize(boxes):
        calls.append(list(boxes))
        return [
            "red icon" if image.getpixel((int(b[0] * 20), 0)) == (255, 0, 0) else "blue icon"
            for b in boxes
        ]

    boxes = [[0, 0, 0.5, 1], [0.5, 0, 1, 1]]
    telemetry = {}
    assert worker.caption_regions(image, boxes, recognize, cache, telemetry=telemetry) == [
        "red icon",
        "red icon",
    ]
    assert telemetry["caption_regions"] == 2
    assert telemetry["cache_hits"] == 0
    assert telemetry["unique_misses"] == 1
    assert telemetry["duplicate_misses"] == 1
    first_count = len(calls)
    assert worker.caption_regions(image, boxes, recognize, cache, telemetry=telemetry) == [
        "red icon",
        "red icon",
    ]
    assert len(calls) == first_count
    assert telemetry["cache_hits"] == 2
    assert telemetry["unique_misses"] == 0
    assert telemetry["duplicate_misses"] == 0
    assert telemetry["caption_ms"] == 0
    image.paste("blue", (10, 0, 20, 10))
    assert worker.caption_regions(image, boxes, recognize, cache, telemetry=telemetry) == [
        "red icon",
        "blue icon",
    ]
    assert calls[-1] == [boxes[1]]
    assert telemetry["cache_hits"] == 1
    assert telemetry["unique_misses"] == 1
    assert telemetry["duplicate_misses"] == 0


def test_float32_crop_boundary_changes_are_not_hidden_by_cache(monkeypatch):
    worker = worker_module(monkeypatch)
    cache = OrderedDict()
    image = Image.new("RGB", (10, 10), "red")
    # Pinned OmniParser's float32 multiplication rounds this x2 * 10 to 7,
    # although Python's float64 product is below 7 and int() truncates to 6.
    boxes = [[0, 0, 0.699999988079071, 1]]
    calls = []

    def recognize(_boxes):
        calls.append(len(_boxes))
        return ["red icon" if image.getpixel((6, 0)) == (255, 0, 0) else "blue edge"]

    assert worker.caption_regions(image, boxes, recognize, cache) == ["red icon"]
    image.putpixel((6, 0), (0, 0, 255))
    assert worker.caption_regions(image, boxes, recognize, cache) == ["blue edge"]
    assert calls == [1, 1]


def test_caption_cache_evicts_old_pixels_and_preserves_box_order(monkeypatch):
    worker = worker_module(monkeypatch)
    cache = OrderedDict()
    calls = []
    image = Image.new("RGB", (10, 10))

    def recognize(boxes):
        calls.append(len(boxes))
        return [str(image.getpixel((0, 0))) for _ in boxes]

    for c in ["red", "blue", "green", "red"]:
        image.paste(c, (0, 0, 10, 10))
        assert worker.caption_regions(image, [[0, 0, 1, 1]], recognize, cache, limit=2) == [
            str(image.getpixel((0, 0)))
        ]
    assert calls == [1, 1, 1, 1]
    assert len(cache) == 2
