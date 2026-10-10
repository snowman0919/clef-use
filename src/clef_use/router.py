"""Execution routing and observation-bound visual actions; no OS input implementation."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .candidates import pointer_allowed
from .grounding import GroundingQueryTooLong, GroundingStrategyUnsupported
from .schema import ActionCandidate, BoundingBox, PointerInput, PointerPoint, VisualIntent


@dataclass(frozen=True)
class Route:
    mode: str
    candidate_count: int
    reason: str
    native_target: str | None = None
    semantic_targets: tuple[str, ...] = ()


class GroundingUncertain(RuntimeError):
    pass


class ExecutionRouter:
    def __init__(self, config, grounder=None):
        self.config = config
        self.grounder = grounder

    @staticmethod
    def scoped_observation(observation, contract):
        from .schema import Observation

        region = contract.visual_intent.region if contract.visual_intent else None
        if region is None:
            return observation
        frame = observation.frame
        width, height = frame.logical_size or frame.image.size
        objects = []
        for obj in observation.objects:
            x, y = frame.point(obj.bbox)
            x, y = (x - frame.origin[0]) / width, (y - frame.origin[1]) / height
            if region.x1 <= x <= region.x2 and region.y1 <= y <= region.y2:
                objects.append(obj)
        return Observation(observation.id, frame, tuple(objects))

    def route(self, observation, contract):
        objects = tuple(
            o
            for o in observation.objects
            if o.actions
            and not o.sensitive
            and o.visible is not False
            and o.enabled is not False
            and o.occluded is not True
        )
        # Count potential actions before CandidateBuilder truncates its output.
        count = sum(len(o.actions) for o in objects)
        if contract.execution_mode == "ASSESS":
            return Route("ASSESS", count, "read-only goal assessment; no action proposals")
        if contract.pointer_inputs or contract.execution_mode == "STRUCTURED":
            return Route("STRUCTURED", count, "explicit structured/pixel contract")
        if contract.execution_mode in {"VISUAL", "CANVAS"}:
            return Route(contract.execution_mode, count, "explicit execution contract")
        intent = contract.visual_intent
        if intent is not None and intent.operation != "click":
            mode = "CANVAS" if intent.operation in {"drag", "stroke", "move"} else "VISUAL"
            return Route(mode, count, "preserve explicit visual primitive")
        if self.grounder is None:
            return Route("STRUCTURED", count, "visual backend disabled")
        scoped = self.scoped_observation(observation, contract)
        ids = {o.id for o in scoped.objects}
        objects = tuple(o for o in objects if o.id in ids)
        query = (
            contract.visual_intent.query if contract.visual_intent else contract.goal
        ).casefold()
        native = [
            o
            for o in objects
            if o.label.casefold() == query
            and {"ax", "dom", "native", "uia", "atspi"}.intersection(o.source)
            and o.confidence is not None
            and o.confidence >= self.config.native_confidence_threshold
            and "click" in o.actions
        ]
        if len(native) == 1:
            return Route("STRUCTURED", count, "unique native semantic target", native[0].id)
        if intent is not None and intent.target_geometry == "point":
            # OCR-backed labels are useful proposals, not trusted native clicks.
            # Match display text without mutating its original label or identity;
            # CLEF still selects/vetoes within this observation-bound subset.
            semantic = tuple(
                o.id
                for o in objects
                if o.label.strip().casefold() == query.strip()
                and "click" in o.actions
                and any(
                    s in {"ocr", "ax", "dom", "native", "uia", "atspi"} or s.endswith("_ocr")
                    for s in o.source
                )
            )
            limit = min(self.config.structured_candidate_threshold, self.config.max_candidates)
            if query.strip() and 0 < len(semantic) <= limit:
                return Route(
                    "STRUCTURED",
                    count,
                    "bounded semantic target candidates",
                    semantic_targets=semantic,
                )
        if not objects:
            return Route("CANVAS", count, "no useful interactive UI candidates")
        scoped_count = sum(len(o.actions) for o in objects)
        if scoped_count > self.config.structured_candidate_threshold:
            return Route("VISUAL", count, "scoped candidate count exceeds configured threshold")
        return Route("STRUCTURED", count, "bounded semantic candidates")

    def uncertain(self, decision, threshold):
        return decision.mode == "ACT" and (
            decision.confidence < threshold
            or decision.mode_confidence < threshold
            or (
                decision.entropy is not None
                and decision.entropy > self.config.clef_entropy_threshold
            )
        )

    def visual_candidates(self, observation, contract, row, cancelled):
        if self.grounder is None:
            raise GroundingUncertain("visual backend unavailable")
        if contract.visual_intent is None and len(contract.goal) > 1000:
            raise GroundingUncertain("long goal requires an explicit visual query")
        intent = contract.visual_intent or VisualIntent(query=contract.goal)
        if intent.operation == "wait":
            return (
                ActionCandidate(
                    id="visual-wait",
                    operation="wait",
                    observation_id=observation.id,
                    description="Wait for target",
                    effect_roi=intent.region,
                ),
            )
        queries = [intent.query]
        if intent.operation in {"drag", "stroke"}:
            queries.extend((*intent.path_queries, intent.end_query))
        points = []
        traces = []
        for index, query in enumerate(queries):
            geometry = intent.target_geometry if index == 0 else "point"
            accepted = None
            for refinement in range(self.config.visual_refinement_retries + 1):
                if cancelled.is_set():
                    raise GroundingUncertain("grounding cancelled")
                try:
                    result = self.grounder.ground(
                        observation.frame.image,
                        query,
                        region=intent.region,
                        refinement=refinement,
                        geometry=geometry,
                        coarse_strategy=intent.coarse_strategy,
                    )
                except (GroundingQueryTooLong, GroundingStrategyUnsupported) as exc:
                    raise GroundingUncertain(str(exc)) from exc
                trace = {
                    "confidence": result.confidence,
                    "entropy": result.entropy,
                    "coarse_roi": result.coarse_roi,
                    "fine_target": result.fine_target,
                    "refinement": refinement,
                    "geometry": geometry,
                    "coarse_strategy": intent.coarse_strategy,
                }
                traces.append(trace)
                row.update(
                    visual_grounding=traces,
                    visual_confidence=result.confidence,
                    coarse_roi=result.coarse_roi,
                    fine_target=result.fine_target,
                )
                x, y = result.point
                width, height = observation.frame.image.size
                if not all(math.isfinite(v) for v in (x, y, result.confidence, result.entropy)):
                    raise GroundingUncertain("nonfinite visual grounding")
                if not (0 <= x < width and 0 <= y < height):
                    raise GroundingUncertain("visual target outside original screenshot")
                if result.confidence >= self.config.visual_confidence_threshold:
                    accepted = PointerPoint(x=x / width, y=y / height)
                    break
            if accepted is None:
                raise GroundingUncertain(
                    "visual confidence remains below threshold after refinement"
                )
            points.append(accepted)
        if intent.operation in {"drag", "stroke"} and len({(p.x, p.y) for p in points}) < 2:
            raise GroundingUncertain("visual gesture has no distinct grounded endpoints")
        # Use the explicitly supplied canvas surface or a minimal gesture surface.
        # The convex box covers every delivered segment and sensitive-region checks.
        width, height = observation.frame.image.size
        surface = intent.region or BoundingBox(
            x1=max(0, min(p.x for p in points) - 2 / width),
            y1=max(0, min(p.y for p in points) - 2 / height),
            x2=min(1, max(p.x for p in points) + 2 / width),
            y2=min(1, max(p.y for p in points) + 2 / height),
        )
        pointer = PointerInput(
            operation=intent.operation,
            label=intent.query[:200],
            reference=observation.frame.reference(),
            surface=surface,
            points=tuple(points),
            duration=intent.duration,
            scroll_direction=intent.scroll_direction,
            scroll_magnitude=intent.scroll_magnitude,
        )
        if not pointer_allowed(pointer, observation):
            raise GroundingUncertain("visual target crosses sensitive or unscoped pixels")
        # Verify a wider region: opening a panel changes pixels beyond the tiny icon.
        return (
            ActionCandidate(
                id="visual-target",
                operation=intent.operation,
                observation_id=observation.id,
                description=intent.query,
                pointer=pointer,
                expected_effect="content_change",
                effect_roi=intent.region,
            ),
        )

    def decision_observation(self, observation, candidates, contract):
        """Keep bounded evidence near a unique observed anchor, not new actions."""
        from .schema import Observation

        ids = {a.target for a in candidates if a.target is not None}
        targets = [o for o in observation.objects if o.id in ids][:32]
        hints = [o for o in observation.objects if o.id not in ids and o.label and not o.sensitive]
        query = contract.visual_intent.query if contract.visual_intent else contract.goal
        eligible = [
            o
            for o in self.scoped_observation(observation, contract).objects
            if not o.sensitive and o.visible is not False and o.occluded is not True
        ]
        anchors = [o for o in eligible if o.label.strip().casefold() == query.strip().casefold()]
        if not anchors and contract.visual_intent is None:
            # A literal success-condition label can focus evidence, never grant input.
            conditions = [condition.casefold() for condition in contract.success_conditions]
            anchors = [
                o
                for o in eligible
                if (label := o.label.strip().casefold())
                and any(
                    re.search(r"(?<!\w)" + re.escape(label) + r"(?!\w)", condition)
                    for condition in conditions
                )
            ]
        if len(anchors) == 1:
            anchor = anchors[0]
            # OCR boxes are image-normalized; measure proximity in the native raster.
            width, height = observation.frame.image.size

            def rank(obj):
                box, reference = obj.bbox, anchor.bbox
                dx = max(reference.x1 - box.x2, box.x1 - reference.x2, 0) * width
                dy = max(reference.y1 - box.y2, box.y1 - reference.y2, 0) * height
                return (obj.id != anchor.id, dx * dx + dy * dy, box.y1, box.x1, obj.id)

            hints.sort(key=rank)
        # A missing or ambiguous anchor grants no spatial inference. Neither
        # hint selection nor raw OCR geometry changes the executable choice set.
        return Observation(
            observation.id,
            observation.frame,
            tuple(targets + hints[:8]),
            evidence=observation.evidence,
        )
