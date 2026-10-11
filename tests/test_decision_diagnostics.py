from PIL import Image

from clef_use.candidates import CandidateBuilder
from clef_use.decision_diagnostics import distribution_metrics
from clef_use.schema import BoundingBox, Contract, Frame, Observation, UIObject


def test_singleton_is_distinct_from_uniform_and_repeat_invariance():
    singleton = distribution_metrics({"only": 1})
    uniform = distribution_metrics({"a": 0.5, "b": 0.5})
    assert singleton["classification"] == "SINGLETON"
    assert singleton["normalized_entropy"] is None
    assert not singleton["singleton_is_safety_evidence"]
    assert uniform["classification"] == "UNIFORM"
    assert uniform["normalized_entropy"] == 1
    assert uniform["repeat_invariance"] == "NOT_MEASURED"
    assert uniform["raw_logit_variance"] is None


def test_candidate_limit_reports_lost_targets_and_preserves_duplicate_ids():
    objects = tuple(
        UIObject(
            id=str(i),
            label="Same menu label",
            role="button",
            bbox=BoundingBox(x1=0, y1=0, x2=1, y2=1),
            actions=frozenset({"click"}),
        )
        for i in range(20)
    )
    builder = CandidateBuilder(limit=12)
    candidates = builder.build(
        Observation("same", Frame(Image.new("RGB", (100, 100))), objects),
        Contract(goal="Click Same menu label"),
    )
    assert len(candidates) == 12
    assert builder.metrics["targets_before_limit"] == 20
    assert builder.metrics["targets_after_limit"] == 12
    assert builder.metrics["proposal_target_retention"] == 0.6
    assert set(builder.metrics["semantic_duplicate_groups"][0]) == {str(i) for i in range(20)}
    assert builder.metrics["coverage_at_k"] is None
