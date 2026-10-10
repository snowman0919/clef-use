import threading

import pytest
from PIL import Image

from clef_use.config import Config
from clef_use.router import ExecutionRouter, GroundingUncertain
from clef_use.schema import (
    ActionCandidate,
    BoundingBox,
    Contract,
    Frame,
    Observation,
    UIObject,
    VisualIntent,
)


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


def test_actionless_context_uses_unique_observed_anchor_not_roster_prefix():
    router = ExecutionRouter(Config())
    items = tuple(
        UIObject(
            id=f"context_{i}",
            label=label,
            role="text",
            source=("ocr",),
            bbox=BoundingBox(x1=x, y1=y, x2=x + 0.03, y2=y + 0.01),
        )
        for i, (label, x, y) in enumerate(
            [(f"Unrelated {i}", 0.7, 0.6 + i * 0.01) for i in range(9)]
            + [
                ("Tools ", 0.02, 0.01),
                ("Add Item", 0.025, 0.03),
                ("Recent Items", 0.025, 0.05),
                ("Raw_OCR_", 0.025, 0.07),
            ]
        )
    )
    contract = Contract(goal="Show Tools", visual_intent=VisualIntent(query="Tools"))
    obs = Observation("context_epoch", Frame(Image.new("RGB", (1000, 500))), items)
    bounded = router.decision_observation(obs, (), contract)
    ids = {o.id for o in bounded.objects}
    assert {o.id for o in items[-4:]} <= ids
    assert len(bounded.objects) <= 8
    assert all(o == next(x for x in items if x.id == o.id) for o in bounded.objects)
    assert all(not o.actions and o.confidence is None for o in bounded.objects)
    assert bounded.id == obs.id and bounded.frame is obs.frame
    reordered = Observation(obs.id, obs.frame, tuple(reversed(items)))
    assert router.decision_observation(reordered, (), contract).objects == bounded.objects


@pytest.mark.parametrize("size", [(1000, 500), (500, 1000)])
@pytest.mark.parametrize("mapped", [False, True])
def test_bounded_context_keeps_native_pixel_nearest_hint_on_rectangular_frames(size, mapped):
    width, height = size

    def item(id, label, x, y):
        return UIObject(
            id=id,
            label=label,
            role="text",
            source=("ocr",),
            bbox=BoundingBox(
                x1=x / width, y1=y / height, x2=(x + 10) / width, y2=(y + 10) / height
            ),
        )

    anchor = item("anchor", "Anchor ", 100, 100)
    overlap = tuple(item(f"overlap_{i}", f"Observed {i}", 100, 100) for i in range(6))
    near_xy, far_xy = ((100, 120), (128, 100)) if width > height else ((120, 100), (100, 128))
    near = item("near_raw", "Near_Raw_", *near_xy)
    far = item("far", "Farther", *far_xy)
    objects = (far, *overlap, near, anchor)
    frame = Frame(
        Image.new("RGB", size),
        origin=(73, -41) if mapped else (0, 0),
        logical_size=(height, width) if mapped else None,
    )
    evidence = (object(),)
    obs = Observation("rectangular_epoch", frame, objects, evidence)
    contract = Contract(goal="Assess visible state", visual_intent=VisualIntent(query="Anchor"))
    router = ExecutionRouter(Config())
    bounded = router.decision_observation(obs, (), contract)
    assert near in bounded.objects  # Native rectangle gaps: near10 pixels, far18 pixels.
    assert far not in bounded.objects
    assert len(bounded.objects) == 8 and bounded.objects[0] is anchor
    assert all(not obj.actions and obj.confidence is None for obj in bounded.objects)
    assert bounded.frame is frame and bounded.id == obs.id
    assert bounded.evidence is evidence
    by_id = {obj.id: obj for obj in objects}
    assert all(obj is by_id[obj.id] for obj in bounded.objects)
    reordered = Observation(obs.id, frame, tuple(reversed(objects)), evidence)
    assert router.decision_observation(reordered, (), contract).objects == bounded.objects


def test_context_uses_unique_success_condition_label_without_visual_intent():
    items = tuple(
        UIObject(
            id=f"context_{i}",
            label=label,
            role="text",
            source=("ocr",),
            bbox=BoundingBox(x1=x, y1=y, x2=x + 0.03, y2=y + 0.01),
        )
        for i, (label, x, y) in enumerate(
            [(f"Unrelated {i}", 0.7, 0.6 + i * 0.01) for i in range(9)]
            + [
                ("Tools ", 0.02, 0.01),
                ("Add Item", 0.025, 0.03),
                ("Recent Items", 0.025, 0.05),
                ("Raw_OCR_", 0.025, 0.07),
            ]
        )
    )
    contract = Contract(
        goal="Open the Tools menu in the task-owned application window.",
        success_conditions=["The TOOLS dropdown is visibly open."],
        execution_mode="ASSESS",
    )
    frame = Frame(Image.new("RGB", (1000, 500)))
    evidence = (object(),)
    obs = Observation("condition_context_epoch", frame, items, evidence)
    router = ExecutionRouter(Config())
    bounded = router.decision_observation(obs, (), contract)
    assert {o.id for o in items[-4:]} <= {o.id for o in bounded.objects}
    assert len(bounded.objects) == 8
    assert bounded.objects[0] is items[-4]
    by_id = {o.id: o for o in items}
    assert all(o is by_id[o.id] for o in bounded.objects)
    assert all(not o.actions and o.confidence is None for o in bounded.objects)
    assert bounded.id == obs.id and bounded.frame is frame and bounded.evidence is evidence
    reordered = Observation(obs.id, frame, tuple(reversed(items)), evidence)
    assert router.decision_observation(reordered, (), contract).objects == bounded.objects
    assert router.route(obs, contract).mode == "ASSESS"


@pytest.mark.parametrize(
    "variant",
    [
        "duplicate",
        "second_condition_label",
        "substring",
        "goal_only",
        "explicit_missing",
        "hidden",
        "occluded",
        "sensitive",
        "blank",
    ],
)
def test_success_condition_context_fallback_does_not_invent_or_override_anchor(variant):
    prefix = tuple(
        UIObject(
            id=f"unrelated_{i}",
            label=f"Other {i}",
            bbox=BoundingBox(x1=0.7, y1=0.6, x2=0.8, y2=0.7),
        )
        for i in range(8)
    )
    anchor = UIObject(
        id="raw_anchor", label="Tools", bbox=BoundingBox(x1=0.02, y1=0.01, x2=0.05, y2=0.02)
    )
    near = UIObject(
        id="raw_neighbor",
        label="Nearby Item",
        bbox=BoundingBox(x1=0.02, y1=0.03, x2=0.05, y2=0.04),
    )
    extras = []
    contract = Contract(
        goal="Open the Tools menu", success_conditions=["The Tools dropdown is visible."]
    )
    if variant == "duplicate":
        extras.append(anchor.model_copy(update={"id": "duplicate"}))
    elif variant == "second_condition_label":
        contract = contract.model_copy(
            update={"success_conditions": [*contract.success_conditions, "Nearby Item is shown."]}
        )
    elif variant == "substring":
        contract = contract.model_copy(
            update={"success_conditions": ["The Toolset dropdown is visible."]}
        )
    elif variant == "goal_only":
        contract = contract.model_copy(update={"success_conditions": ["The dropdown is visible."]})
    elif variant == "explicit_missing":
        contract = contract.model_copy(
            update={"visual_intent": VisualIntent(query="Explicit Missing")}
        )
    elif variant == "blank":
        anchor = anchor.model_copy(update={"label": " "})
    else:
        fields = {
            "hidden": {"visible": False},
            "occluded": {"occluded": True},
            "sensitive": {"sensitive": True},
        }
        anchor = anchor.model_copy(update=fields[variant])
    obs = Observation(
        "ambiguous_epoch", Frame(Image.new("RGB", (1000, 500))), (*prefix, anchor, near, *extras)
    )
    assert ExecutionRouter(Config()).decision_observation(obs, (), contract).objects == prefix


@pytest.mark.parametrize(
    "label,condition",
    [("Tools (v2)", "The Tools (v2) menu is visible."), ("設定", "The 「設定」 panel is visible.")],
)
def test_success_condition_label_is_literal_and_unicode_safe(label, condition):
    anchor = UIObject(id="literal", label=label, bbox=BoundingBox(x1=0, y1=0, x2=0.1, y2=0.1))
    far = tuple(
        UIObject(id=str(i), label=f"Other {i}", bbox=BoundingBox(x1=0.7, y1=0.7, x2=0.8, y2=0.8))
        for i in range(8)
    )
    obs = Observation("literal_epoch", Frame(Image.new("RGB", (1000, 500))), (*far, anchor))
    contract = Contract(goal="Show the requested menu", success_conditions=[condition])
    assert ExecutionRouter(Config()).decision_observation(obs, (), contract).objects[0] is anchor


@pytest.mark.parametrize("duplicate", [False, True])
def test_exact_goal_anchor_precedes_literal_success_condition_fallback(duplicate):
    prefix = tuple(
        UIObject(id=str(i), label=f"Other {i}", bbox=BoundingBox(x1=0.7, y1=0.7, x2=0.8, y2=0.8))
        for i in range(8)
    )
    goal_anchor = UIObject(
        id="goal", label="Exact Goal", bbox=BoundingBox(x1=0.02, y1=0.01, x2=0.05, y2=0.02)
    )
    condition_anchor = UIObject(
        id="condition", label="Tools", bbox=BoundingBox(x1=0.6, y1=0.3, x2=0.65, y2=0.35)
    )
    extras = (goal_anchor.model_copy(update={"id": "duplicate"}),) if duplicate else ()
    obs = Observation(
        "exact_epoch",
        Frame(Image.new("RGB", (1000, 500))),
        (*prefix, goal_anchor, condition_anchor, *extras),
    )
    contract = Contract(goal="Exact Goal", success_conditions=["The Tools dropdown is visible."])
    bounded = ExecutionRouter(Config()).decision_observation(obs, (), contract)
    if duplicate:
        assert bounded.objects == prefix
    else:
        assert bounded.objects[0] is goal_anchor


def test_condition_context_fallback_preserves_executable_targets_and_bound():
    from clef_use.backends import decision_request

    targets = tuple(
        UIObject(
            id=f"target_{i}",
            label=f"Allowed {i}",
            actions=frozenset({"click"}),
            bbox=BoundingBox(x1=0.7, y1=0.7, x2=0.8, y2=0.8),
        )
        for i in range(32)
    )
    far = tuple(
        UIObject(id=f"hint_{i}", label=f"Other {i}", bbox=targets[0].bbox) for i in range(9)
    )
    anchor = UIObject(
        id="anchor", label="Tools", bbox=BoundingBox(x1=0.02, y1=0.01, x2=0.05, y2=0.02)
    )
    near = UIObject(
        id="near", label="Observed Item", bbox=BoundingBox(x1=0.02, y1=0.03, x2=0.05, y2=0.04)
    )
    obs = Observation(
        "choices_epoch", Frame(Image.new("RGB", (1000, 500))), (*targets, *far, anchor, near)
    )
    candidates = tuple(
        ActionCandidate(
            id=f"action_{i}",
            operation="click",
            observation_id=obs.id,
            target=obj.id,
            description=obj.label,
        )
        for i, obj in enumerate(reversed(targets))
    )
    contract = Contract(
        goal="Show the Tools menu", success_conditions=["The Tools dropdown is visible."]
    )
    bounded = ExecutionRouter(Config()).decision_observation(obs, candidates, contract)
    assert len(bounded.objects) == 40
    assert all(
        actual is expected for actual, expected in zip(bounded.objects[:32], targets, strict=True)
    )
    assert bounded.objects[32] is anchor and near in bounded.objects[32:]
    packet = decision_request(bounded, contract, candidates, [])
    assert [a["id"] for a in packet["state"]["allowed_candidates"]] == [a.id for a in candidates]
    assert list(packet["questions"]["action"]["criteria"]) == [a.id for a in candidates]


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
