"""Exercise the actual request with pinned overlap code, without ML weights.

Run in a prepared parser environment with CLEF_TEST_OMNI_SOURCE set. Only
OCR/detection/model recognition are fixtures; PNG decode, Torch scaling,
pinned fusion, crop caching and response assembly are the real path.
"""

import ast
import base64
import importlib
import importlib.util
import io
import os
import sys
import unittest
from collections import OrderedDict
from pathlib import Path

from PIL import Image


@unittest.skipUnless(
    os.environ.get("CLEF_TEST_OMNI_SOURCE")
    and importlib.util.find_spec("torch")
    and importlib.util.find_spec("numpy"),
    "requires the prepared parser environment and explicit pinned source",
)
class OmniRequestBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/clef_use"))
        try:
            cls.module = importlib.import_module("model_worker")
        finally:
            sys.path.pop(0)
        cls.torch = importlib.import_module("torch")
        path = Path(os.environ["CLEF_TEST_OMNI_SOURCE"]) / "util/utils.py"
        function = next(
            n
            for n in ast.parse(path.read_text()).body
            if isinstance(n, ast.FunctionDef) and n.name == "remove_overlap_new"
        )
        namespace = {"List": list}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), namespace)
        cls.overlap = staticmethod(namespace["remove_overlap_new"])

    def request(self, detections, ocr_boxes=(), labels=()):
        worker = self.module.OmniWorker.__new__(self.module.OmniWorker)
        worker.check_ocr_box = lambda *a, **k: ((list(labels), list(ocr_boxes)), None)
        boxes = self.torch.tensor(detections, dtype=self.torch.float32).reshape(-1, 4)
        worker.predict = lambda *a, **k: (boxes, None, None)
        worker.detector = worker.caption = worker.processor = None
        worker.overlap = self.overlap
        worker.area = lambda b, w, h: (b[2] - b[0]) * w * (b[3] - b[1]) * h
        worker.icon_caption_cache = OrderedDict()
        self.captioned = []

        def caption(boxes, start, image, models, batch_size):
            self.captioned.extend(boxes.tolist())
            return ["Red tool icon"] * len(boxes)

        worker.caption_icons = caption
        png = io.BytesIO()
        Image.new("RGB", (10, 10), "red").save(png, format="PNG")
        return worker.request({"image": base64.b64encode(png.getvalue()).decode()})["objects"]

    def test_icon_only_screen_preserves_detected_control_and_caption(self):
        objects = self.request([[1, 1, 3, 3]])
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["type"], "icon")
        self.assertTrue(objects[0]["interactivity"])
        self.assertEqual(objects[0]["content"], "Red tool icon")
        for actual, expected in zip(objects[0]["bbox"], (0.1, 0.1, 0.3, 0.3), strict=True):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(len(self.captioned), 1)

    def test_empty_screen_does_not_invent_controls_or_run_caption_model(self):
        self.assertEqual(self.request([]), [])
        self.assertEqual(self.captioned, [])

    def test_ocr_only_screen_preserves_text_without_captioning(self):
        objects = self.request([], [(7, 7, 9, 9)], ["Render"])
        self.assertEqual(
            [(o["type"], o["content"], o["interactivity"]) for o in objects],
            [("text", "Render", False)],
        )
        self.assertEqual(self.captioned, [])

    def test_ocr_inside_icon_keeps_visible_label_and_skips_caption(self):
        objects = self.request([[1, 1, 9, 9]], [(3, 3, 6, 6)], ["Render"])
        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0]["type"], "icon")
        self.assertEqual(objects[0]["content"].strip(), "Render")
        self.assertTrue(objects[0]["interactivity"])
        self.assertEqual(self.captioned, [])


if __name__ == "__main__":
    unittest.main()
