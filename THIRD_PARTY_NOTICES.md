# Third-party notices

The clef-use wrapper is Apache-2.0. Dependencies and downloaded weights retain
their own licenses. Release archives include dependency wheels; consult each
wheel's LICENSE/NOTICE metadata. Model weights are not redistributed here.

| Component | Source | License / use |
| --- | --- | --- |
| CLEF and CLEF-Flash | https://huggingface.co/Cloudflare/clef-flash | Apache-2.0 model repository; pinned release code |
| OmniParser V2 wrapper | https://github.com/microsoft/OmniParser | MIT utilities |
| YOLOv9 V3 detector | OmniParser `util/yolov9` and model card | MIT detector code; pinned V3 weights |
| Florence-2 | https://huggingface.co/microsoft/Florence-2-base-ft | MIT model code and weights |
| EasyOCR | https://github.com/JaidedAI/EasyOCR | Apache-2.0 |
| PaddleOCR/PaddlePaddle | https://github.com/PaddlePaddle/PaddleOCR | Apache-2.0 |
| PyTorch / Transformers | https://pytorch.org / https://github.com/huggingface/transformers | BSD-style / Apache-2.0 |
| MCP Python SDK | https://github.com/modelcontextprotocol/python-sdk | MIT |
| PyAutoGUI / MSS | https://github.com/asweigart/pyautogui / https://github.com/BoboTiG/python-mss | BSD-3-Clause / MIT |

The original OmniParser Ultralytics detector is not downloaded by this package.
The current pinned upstream model repository contains the MIT V3 detector.
Switching to another detector/revision can change licensing obligations.
Exact acquisition revisions are in `src/clef_use/models.py`.
