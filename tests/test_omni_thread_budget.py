"""Prepared-parser regression: native initialization preserves caller CPU policy."""

import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


@unittest.skipUnless(
    os.environ.get("CLEF_TEST_OMNI_CONFIG") and importlib.util.find_spec("torch"),
    "requires an explicit prepared-parser configuration and local pinned models",
)
class OmniThreadBudgetTests(unittest.TestCase):
    def initialize(self, omp_threads):
        config_path = Path(os.environ["CLEF_TEST_OMNI_CONFIG"]).resolve(strict=True)
        configuration = json.loads(config_path.read_text(encoding="utf-8"))
        worker_dir = Path(__file__).resolve().parents[1] / "src/clef_use"
        environment = dict(os.environ)
        model_dir = Path(configuration["model_dir"])
        environment.update(
            HF_HOME=str(model_dir / "huggingface"),
            HF_HUB_OFFLINE="1",
            PYTORCH_ENABLE_MPS_FALLBACK="1",
            TOKENIZERS_PARALLELISM="false",
            EASYOCR_MODULE_PATH=str(model_dir / "easyocr"),
            PADDLE_OCR_BASE_DIR=str(model_dir / "paddleocr"),
        )
        if configuration.get("rocm_arch"):
            environment["ROCM_SDK_TARGET_FAMILY"] = configuration["rocm_arch"]
        for key in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
            environment.pop(key, None)
        if omp_threads is not None:
            environment["OMP_NUM_THREADS"] = str(omp_threads)
        # Each real constructor runs in a fresh child: upstream imports and the
        # OpenMP environment must not be cached by a preceding test or caller.
        code = """
import contextlib,json,sys
with contextlib.redirect_stdout(sys.stderr):
    sys.path.insert(0,sys.argv[1])
    import torch
    caller_threads=torch.get_num_threads()
    from model_worker import OmniWorker
    with open(sys.argv[2],encoding='utf-8') as stream:
        configuration=json.load(stream)
    worker=OmniWorker(configuration)
    effective_threads=torch.get_num_threads()
print(json.dumps({'caller_threads':caller_threads,'effective_threads':effective_threads,
                  'reported_threads':worker.load_metrics['effective_torch_threads']}))
"""
        completed = subprocess.run(
            [sys.executable, "-c", code, str(worker_dir), str(config_path)],
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        self.assertEqual(completed.returncode, 0, "Real parser initialization failed")
        return json.loads(completed.stdout)

    def check_budget(self, threads):
        result = self.initialize(threads)
        if threads is None and result["caller_threads"] == 1:
            self.skipTest("Native caller budget is already one thread")
        if threads is not None:
            self.assertEqual(result["caller_threads"], threads)
        self.assertEqual(result["effective_threads"], result["caller_threads"])
        self.assertEqual(result["reported_threads"], result["caller_threads"])

    def test_unset_omp_preserves_native_caller_budget(self):
        self.check_budget(None)

    def test_explicit_single_thread_budget_is_preserved(self):
        self.check_budget(1)

    def test_explicit_multiple_thread_budget_is_preserved(self):
        self.check_budget(4)


if __name__ == "__main__":
    unittest.main()
