"""Host-only private capture of head-consumed numbers, never an SDK request replay.

Token IDs and latents are sensitive even without prose/identifier strings.
Never publish these artifacts or use them as a completion witness.
"""

import hashlib
import json
import os
import re
import stat
import sys

MAX_HIDDEN_BYTES = 2**26
MAX_LOGIT_BYTES = 2**15
MAX_MANIFEST_BYTES = 2**19
CHUNK_BYTES = 2**21


def _private_directory(root):
    """Bind every path component without following links; subsequent IO uses this FD."""
    raw = os.fspath(root)
    if os.name != "posix" or not isinstance(raw, str) or not raw.startswith("/"):
        raise ValueError("private capture requires a POSIX absolute path")
    parts = raw.split("/")[1:]
    if not parts or any(part in {"", ".", ".."} or "\0" in part for part in parts):
        raise ValueError("private capture requires literal directory components")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open("/", flags)
    try:
        for part in parts:
            child = os.open(part, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        info = os.fstat(directory)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ValueError("diagnostic directory must be private and owned")
        with os.scandir(directory) as entries:
            if next(entries, None) is not None:
                raise ValueError("diagnostic directory must be empty")
        return directory
    except BaseException as failure:
        os.close(directory)
        if isinstance(failure, OSError):
            raise ValueError("private path must contain directories, not symlinks") from failure
        raise


def _source_metadata(metadata):
    enums = {
        "decision_model": {"Cloudflare/clef", "Cloudflare/clef-flash"},
        "backend": {"cpu", "cuda", "rocm", "mps", "xpu"},
        "compute_dtype": {"float16", "bfloat16", "float32"},
    }
    hashes = {"model_revision": 40, "frame_image_sha256": 64, "image_png_sha256": 64}
    integers = {"worker_pid", "quantized_modules"}
    allowed = enums.keys() | hashes.keys() | integers
    if type(metadata) is not dict or len(metadata) > len(allowed):
        raise ValueError("diagnostic metadata must be bounded scalar provenance")
    for key, value in metadata.items():
        if key not in allowed:
            raise ValueError("diagnostic metadata field is not allowlisted")
        if key in enums:
            valid = type(value) is str and len(value) <= 32 and value in enums[key]
        elif key in hashes:
            valid = value is None or (
                type(value) is str
                and len(value) == hashes[key]
                and re.fullmatch(r"[0-9a-f]+", value) is not None
            )
        else:
            valid = type(value) is int and 0 <= value < 2**31
        if not valid:
            raise ValueError("diagnostic metadata value is not bounded provenance")
    return dict(metadata)


def capture_head_inputs(model, infer, root, metadata):
    """Capture only numeric arguments consumed by the pinned head, without alteration."""
    import torch

    source = _source_metadata(metadata)
    directory = _private_directory(root)
    pre = post = None
    created = []
    manifest = {"format": "clef-use-head-inputs-v1", "byteorder": sys.byteorder, "source": source}
    try:

        def open_output(name):
            descriptor = os.open(
                name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
            )
            created.append(name)
            try:
                return os.fdopen(descriptor, "wb")
            except BaseException:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
                raise

        def raw_bytes(tensor):
            return tensor.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()

        def span(value, count):
            if len(value) != 2 or any(type(x) is not int for x in value):
                raise ValueError("diagnostic span must contain two integers")
            if not 0 <= value[0] < count or not value[0] <= value[1] <= count:
                raise ValueError("diagnostic span is outside the captured sequence")
            return list(value)

        def before(_module, arguments):
            if "hidden" in manifest:
                raise ValueError("diagnostic capture requires exactly one head call")
            hidden, ids, mask, records = arguments[:4]
            if hidden.ndim != 3 or hidden.shape[0] != 1 or len(records) != 1:
                raise ValueError("diagnostic capture requires one bounded record")
            count, width = hidden.shape[1:]
            size = hidden.numel() * hidden.element_size()
            if not 0 < count <= 8192 or not 0 < width or size > MAX_HIDDEN_BYTES:
                raise ValueError("diagnostic hidden byte budget exceeded")
            if width * hidden.element_size() > CHUNK_BYTES:
                raise ValueError("diagnostic row exceeds the chunk budget")
            if hidden.dtype not in {torch.float16, torch.bfloat16, torch.float32}:
                raise ValueError("unsupported diagnostic hidden dtype")
            if ids.shape != hidden.shape[:2] or mask.shape != ids.shape:
                raise ValueError("diagnostic record shape mismatch")
            if ids.dtype not in {torch.int32, torch.int64} or mask.dtype not in {
                torch.bool,
                torch.int32,
                torch.int64,
            }:
                raise ValueError("unsupported diagnostic token/mask dtype")
            questions = records[0].questions
            if not 0 < len(questions) <= 128:
                raise ValueError("diagnostic schema budget exceeded")
            schema = []
            total_options = 0
            for question in questions:
                if type(question.question_type) is not int or question.question_type not in {
                    0,
                    1,
                    2,
                }:
                    raise ValueError("invalid diagnostic question type")
                options = question.option_spans
                total_options += len(options)
                if not options or total_options > 4096:
                    raise ValueError("diagnostic option budget exceeded")
                schema.append(
                    {
                        "question_type": question.question_type,
                        "question_span": span(question.question_span, count),
                        "option_spans": [span(value, count) for value in options],
                    }
                )
            # The pinned head consumes these numeric fields, not IDs, prose, or record media.
            manifest["questions"] = schema
            manifest["input_ids"] = ids.detach().cpu().tolist()
            manifest["input_ids_dtype"] = str(ids.dtype).removeprefix("torch.")
            manifest["attention_mask"] = mask.detach().cpu().tolist()
            manifest["attention_mask_dtype"] = str(mask.dtype).removeprefix("torch.")
            digest = hashlib.sha256()
            finite = True
            rows = CHUNK_BYTES // (width * hidden.element_size())
            with open_output("hidden.bin") as stream:
                for start in range(0, count, rows):
                    chunk = hidden[:, start : start + rows].detach()
                    raw = raw_bytes(chunk)
                    finite = finite and bool(torch.isfinite(chunk).all())
                    stream.write(raw)
                    digest.update(raw)
                stream.flush()
                os.fsync(stream.fileno())
            manifest["hidden"] = {
                "shape": list(hidden.shape),
                "dtype": str(hidden.dtype).removeprefix("torch."),
                "bytes": size,
                "sha256": digest.hexdigest(),
                "finite": finite,
            }
            # Returning None leaves every actual argument untouched.

        def after(_module, _arguments, output):
            if len(output) != 1 or len(output[0]) != len(manifest["questions"]):
                raise ValueError("diagnostic logit/schema mismatch")
            total = 0
            for value, question in zip(output[0], manifest["questions"], strict=True):
                if value.ndim != 1 or value.numel() != len(question["option_spans"]):
                    raise ValueError("diagnostic logit/option shape mismatch")
                if value.dtype not in {torch.float16, torch.bfloat16, torch.float32, torch.float64}:
                    raise ValueError("unsupported diagnostic logit dtype")
                total += value.numel() * value.element_size()
                if total > MAX_LOGIT_BYTES:
                    raise ValueError("diagnostic logit byte budget exceeded")
            manifest["logits"] = []
            offset = 0
            with open_output("logits.bin") as stream:
                for value in output[0]:
                    raw = raw_bytes(value)
                    stream.write(raw)
                    manifest["logits"].append(
                        {
                            "offset": offset,
                            "bytes": len(raw),
                            "shape": list(value.shape),
                            "dtype": str(value.dtype).removeprefix("torch."),
                            "sha256": hashlib.sha256(raw).hexdigest(),
                            "finite": bool(torch.isfinite(value).all()),
                        }
                    )
                    offset += len(raw)
                stream.flush()
                os.fsync(stream.fileno())
            # Raw bits retain signed zero, infinity and NaN payloads; output is unchanged.

        pre = model.head.register_forward_pre_hook(before)
        post = model.head.register_forward_hook(after)
        result = infer()
        if "logits" not in manifest:
            raise ValueError("diagnostic head boundary was not executed")
        digest = hashlib.sha256()
        size = 0
        with open_output("manifest.json") as stream:
            for text in json.JSONEncoder(allow_nan=False, indent=2).iterencode(manifest):
                raw = text.encode("ascii")
                size += len(raw)
                if size > MAX_MANIFEST_BYTES:
                    raise ValueError("diagnostic manifest byte budget exceeded")
                stream.write(raw)
                digest.update(raw)
            stream.flush()
            os.fsync(stream.fileno())
        result["head_capture"] = {"manifest_sha256": digest.hexdigest()}
        return result
    except BaseException as failure:
        incomplete = []
        for name in created:
            try:
                os.unlink(name, dir_fd=directory)
            except OSError:
                incomplete.append(name)
        if incomplete:
            failure.add_note("private head capture cleanup incomplete: " + ",".join(incomplete))
            failure.__dict__["head_capture_cleanup_incomplete"] = True
        raise
    finally:
        try:
            if pre is not None:
                pre.remove()
        finally:
            try:
                if post is not None:
                    post.remove()
            finally:
                os.close(directory)
