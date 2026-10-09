import threading

import pytest
from PIL import Image

from clef_use.config import Config
from clef_use.router import ExecutionRouter, GroundingUncertain
from clef_use.schema import BoundingBox, Contract, Frame, Observation, UIObject, VisualIntent


def observation(count, **fields):
    return Observation(
        "frame",
        Frame(Image.new("RGB", (1000, 500))),
        tuple(
            UIObject(
                id=str(i),
                label="Settings",
                bbox=BoundingBox(x1=0.1, y1=0.1, x2=0.2, y2=0.2),
                actions=frozenset({"click"}),
                **fields,
            )
            for i in range(count)
        ),
    )


def test_raw_candidate_explosion_routes_before_truncation():
    router = ExecutionRouter(Config(structured_candidate_threshold=24), grounder=object())
    route = router.route(observation(160), Contract(goal="Settings"))
    assert route.mode == "VISUAL"
    assert route.candidate_count == 160


def test_sparse_and_native_semantic_precedence():
    router = ExecutionRouter(Config(), grounder=object())
    assert router.route(observation(3), Contract(goal="Settings")).mode == "STRUCTURED"
    obs = observation(160, source=("ax",), confidence=0.99)
    # Ambiguous native labels are not confidently unique targets.
    assert router.route(obs, Contract(goal="Settings")).mode == "VISUAL"
    native = obs.objects[0].model_copy(update={"label": "Save"})
    obs = Observation(obs.id, obs.frame, (native, *obs.objects[1:]))
    route = router.route(obs, Contract(goal="Save"))
    assert route.mode == "STRUCTURED"
    assert route.native_target == "0"


def test_ocr_display_target_bounds_dense_candidates_without_native_trust():
    router = ExecutionRouter(Config(), grounder=object())
    obs = observation(160)
    targets = tuple(
        o.model_copy(update={"label": label, "source": ("box_yolo_content_ocr",)})
        for o, label in zip(obs.objects[:2], ("Apply", "Apply "), strict=True)
    )
    obs = Observation(obs.id, obs.frame, (*targets, *obs.objects[2:]))
    route = router.route(
        obs, Contract(goal="Apply the operation", visual_intent=VisualIntent(query="Apply"))
    )
    assert route.mode == "STRUCTURED"
    assert route.semantic_targets == ("0", "1")
    assert route.native_target is None
    assert targets[1].label == "Apply "


@pytest.mark.parametrize(
    "fields",
    [
        {"sensitive": True},
        {"visible": False},
        {"enabled": False},
        {"occluded": True},
        {"actions": frozenset({"type"})},
        {"source": ("box_yolo_content_yolo",)},
    ],
)
def test_ineligible_semantic_target_cannot_replace_dense_grounding(fields):
    router = ExecutionRouter(Config(), grounder=object())
    obs = observation(160)
    target = obs.objects[0].model_copy(
        update={"label": "Apply", "source": ("box_yolo_content_ocr",), **fields}
    )
    obs = Observation(obs.id, obs.frame, (target, *obs.objects[1:]))
    route = router.route(
        obs, Contract(goal="Apply the operation", visual_intent=VisualIntent(query="Apply"))
    )
    assert route.mode == "VISUAL"
    assert not route.semantic_targets
    assert route.native_target is None


def test_semantic_matching_is_exact_and_excludes_out_of_region_targets():
    router = ExecutionRouter(Config(), grounder=object())
    obs = observation(160)
    target = obs.objects[0].model_copy(update={"label": "Apply all", "source": ("ocr",)})
    obs = Observation(obs.id, obs.frame, (target, *obs.objects[1:]))
    contract = Contract(goal="Apply", visual_intent=VisualIntent(query="Apply"))
    assert router.route(obs, contract).mode == "VISUAL"
    contract = contract.model_copy(
        update={
            "visual_intent": VisualIntent(
                query="Apply", region=BoundingBox(x1=0.6, y1=0.6, x2=0.9, y2=0.9)
            )
        }
    )
    target = target.model_copy(update={"label": "Apply"})
    obs = Observation(obs.id, obs.frame, (target, *obs.objects[1:]))
    assert router.route(obs, contract).mode == "CANVAS"
    assert not router.route(obs, contract).semantic_targets


@pytest.mark.parametrize("count,expected", [(12, "STRUCTURED"), (13, "VISUAL")])
def test_semantic_candidates_do_not_silently_truncate_ambiguous_targets(count, expected):
    router = ExecutionRouter(
        Config(structured_candidate_threshold=24, max_candidates=12), grounder=object()
    )
    obs = observation(160)
    matches = tuple(
        o.model_copy(update={"label": "Apply", "source": ("ocr",)}) for o in obs.objects[:count]
    )
    obs = Observation(obs.id, obs.frame, (*matches, *obs.objects[count:]))
    route = router.route(obs, Contract(goal="Apply", visual_intent=VisualIntent(query="Apply")))
    assert route.mode == expected
    assert len(route.semantic_targets) == (count if expected == "STRUCTURED" else 0)


def test_horizontal_line_request_is_not_replaced_by_semantic_point_click():
    router = ExecutionRouter(Config(), grounder=object())
    obs = observation(160)
    target = obs.objects[0].model_copy(update={"label": "Apply", "source": ("ocr",)})
    obs = Observation(obs.id, obs.frame, (target, *obs.objects[1:]))
    route = router.route(
        obs,
        Contract(
            goal="Apply",
            visual_intent=VisualIntent(query="Apply", target_geometry="horizontal_line"),
        ),
    )
    assert route.mode == "VISUAL"
    assert not route.semantic_targets


def test_canvas_contract_does_not_depend_on_omniparser_objects():
    router = ExecutionRouter(Config(), grounder=object())
    contract = Contract(
        goal="Move the selected mesh",
        execution_mode="CANVAS",
        visual_intent=VisualIntent(
            query="selected mesh", operation="drag", end_query="empty area on the right"
        ),
    )
    assert router.route(observation(160), contract).mode == "CANVAS"


def test_hidden_disabled_sensitive_objects_do_not_trigger_explosion():
    router = ExecutionRouter(Config(), grounder=object())
    assert router.route(observation(160, enabled=False), Contract(goal="Settings")).mode == "CANVAS"


def test_missing_visual_backend_preserves_structured_path():
    router = ExecutionRouter(Config())
    assert router.route(observation(160), Contract(goal="Settings")).mode == "STRUCTURED"


def test_explicit_visual_contract_is_not_silently_downgraded():
    router = ExecutionRouter(Config())
    assert (
        router.route(observation(3), Contract(goal="Settings", execution_mode="VISUAL")).mode
        == "VISUAL"
    )


def test_auto_preserves_visual_gesture_instead_of_native_click():
    router = ExecutionRouter(Config(), grounder=object())
    contract = Contract(
        goal="Move Settings",
        visual_intent=VisualIntent(query="Settings", operation="drag", end_query="right region"),
    )
    assert router.route(observation(1, source=("ax",), confidence=0.99), contract).mode == "CANVAS"


def test_native_target_outside_visual_region_cannot_be_selected():
    router = ExecutionRouter(Config(), grounder=object())
    contract = Contract(
        goal="Settings",
        visual_intent=VisualIntent(
            query="Settings", region=BoundingBox(x1=0.6, y1=0.6, x2=0.9, y2=0.9)
        ),
    )
    assert router.route(observation(1, source=("ax",), confidence=0.99), contract).mode == "CANVAS"


def test_sparse_target_region_preserves_structured_execution_on_dense_screen():
    router = ExecutionRouter(Config(), grounder=object())
    obs = observation(160)
    inside = obs.objects[0].model_copy(update={"bbox": BoundingBox(x1=0.6, y1=0.6, x2=0.7, y2=0.7)})
    obs = Observation(obs.id, obs.frame, (inside, *obs.objects[1:]))
    contract = Contract(
        goal="Settings",
        visual_intent=VisualIntent(
            query="Settings", region=BoundingBox(x1=0.5, y1=0.5, x2=0.9, y2=0.9)
        ),
    )
    route = router.route(obs, contract)
    assert route.mode == "STRUCTURED"
    assert route.candidate_count == 160


def test_long_goal_requires_explicit_visual_query_instead_of_crashing_or_truncating():
    router = ExecutionRouter(Config(), grounder=object())
    contract = Contract(goal="x" * 1001)
    obs = observation(0)
    assert router.route(obs, contract).mode == "CANVAS"
    with pytest.raises(GroundingUncertain, match="explicit visual query"):
        router.visual_candidates(obs, contract, {}, threading.Event())


@pytest.mark.parametrize("logical_size,origin", [(None, (0, 0)), ((1000, 500), (42, -10))])
def test_native_region_filter_checks_delivered_pixel(logical_size, origin):
    router = ExecutionRouter(Config(), grounder=object())
    obs = observation(1, source=("ax",), confidence=0.99)
    target = obs.objects[0].model_copy(
        update={"bbox": BoundingBox(x1=0.5004, y1=0.4, x2=0.5014, y2=0.6)}
    )
    obs = Observation(
        obs.id,
        Frame(Image.new("RGB", (2000, 1000)), logical_size=logical_size, origin=origin),
        (target,),
    )
    # At 2000px the integer coordinate is inside; at logical 1000px it is outside.
    contract = Contract(
        goal="Settings",
        visual_intent=VisualIntent(
            query="Settings", region=BoundingBox(x1=0.5004, y1=0.3, x2=0.6, y2=0.7)
        ),
    )
    route = router.route(obs, contract)
    assert route.native_target == ("0" if logical_size is None else None)
    assert route.mode == ("STRUCTURED" if logical_size is None else "CANVAS")
