import math
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from clef_use.grounding import Grounder, NormalizedDotProductHead, SpatialPrediction
from clef_use.schema import BoundingBox


class ColorBackbone:
    image_size = 64

    def encode_image(self, image):
        # Real pixel-derived spatial features, independent of the grounder's geometry.
        return [
            [
                tuple(
                    channel.getextrema()[1]
                    for channel in image.crop((x, y, x + 4, y + 4)).split()[:2]
                )
                + (1.0,)
                for x in range(0, 64, 4)
            ]
            for y in range(0, 64, 4)
        ]


class ColorText:
    def encode_query(self, query):
        return {"red": (1, 0, 0), "green": (0, 1, 0)}[query]


def grounder():
    return Grounder(ColorBackbone(), ColorText(), NormalizedDotProductHead())


def target_image(size, target):
    image = Image.new("RGB", size)
    image.putpixel(target, (255, 0, 0))
    return image


@pytest.mark.parametrize(
    "size,target",
    [((480, 60), (465, 31)), ((60, 480), (31, 465)), ((91, 37), (90, 36)), ((37, 91), (0, 90))],
)
def test_grounding_maps_aspect_and_border_pixels_into_original_screenshot(size, target):
    result = grounder().ground(target_image(size, target), "red")
    assert result.point == pytest.approx(target, abs=3)
    assert 0 <= result.point[0] < size[0] and 0 <= result.point[1] < size[1]
    left, top, right, bottom = result.coarse_roi
    assert left <= result.point[0] < right and top <= result.point[1] < bottom
    assert result.fine_target == pytest.approx(result.point, abs=1e-9)


@pytest.mark.parametrize("size,target,region", [
    ((320, 140), (241, 87), BoundingBox(x1=.25, y1=.1, x2=.9, y2=.9)),
    ((960, 240), (783, 115), BoundingBox(x1=.65, y1=.2, x2=.95, y2=.8)),
    ((240, 960), (115, 783), BoundingBox(x1=.2, y1=.65, x2=.8, y2=.95)),
])
def test_overview_preserves_scoped_non_square_coordinates_and_fine_pixel(size, target, region):
    result = grounder().ground(target_image(size, target), "red", region,
                               coarse_strategy="overview")
    assert result.point == pytest.approx(target, abs=3)
    left, top, right, bottom = result.coarse_roi
    assert left <= target[0] < right and top <= target[1] < bottom
    # Magnification retains the original-pixel fine crop radius, independent
    # of the overview's downsampling ratio.
    assert right - left <= 33 and bottom - top <= 33


def test_overview_does_not_change_default_tiled_small_target_behavior():
    image = target_image((960, 240), (783, 115))
    assert grounder().ground(image, "red").point == pytest.approx((783, 115), abs=3)
    assert grounder().ground(image, "red", coarse_strategy="tiled").point == pytest.approx(
        (783, 115), abs=3
    )


def test_overview_retains_distinct_visible_border_patches_under_partial_padding():
    class VisibleRedBackbone:
        image_size = 64

        def encode_image(self, image):
            return [[image.crop((x, y, x + 4, y + 4)).getextrema()[0][1] > 180
                     for x in range(0, 64, 4)] for y in range(0, 64, 4)]

    class PresenceHead:
        dense_head = SimpleNamespace(coarse_strategies={"tiled", "overview"})

        def predict(self, features, text):
            return SpatialPrediction(
                [[20 if red else -20 for red in row] for row in features],
                target_probabilities=[[.99 if red else .01 for red in row] for row in features],
            )

    image = Image.new("RGB", (960, 750))
    draw = ImageDraw.Draw(image)
    # Letterboxing puts part of the first target patch in padding. Its visible
    # part and the adjacent patch represent distinct contiguous screen areas.
    draw.rectangle((180, 0, 239, 74), fill="red")
    draw.rectangle((665, 380, 715, 425), fill="red")
    result = Grounder(VisibleRedBackbone(), ColorText(), PresenceHead(), temperature=1).ground(
        image, "red", coarse_strategy="overview"
    )
    # Two connected valid patches versus one competing patch: dropping either
    # border patch falsely changes this to equally supported competing targets.
    assert result.confidence == pytest.approx(1 / 3, abs=1e-8)


@pytest.mark.parametrize("x", [47, 48, 63, 64, 95, 96])
def test_overlapping_tiles_preserve_targets_across_tile_seams(x):
    result = grounder().ground(target_image((160, 64), (x, 31)), "red")
    assert result.point == pytest.approx((x, 31), abs=3)
    assert result.confidence > 0.1


class ColorPresenceHead:
    def predict(self, features, text):
        scores = [[4.6 if pixel[0] > 80 and pixel[0] > 2 * pixel[1] else -.1
                   for pixel in row] for row in features]
        return SpatialPrediction(scores, target_probabilities=[
            [1 / (1 + math.exp(-score)) for score in row] for row in scores
        ])


@pytest.mark.parametrize("size,target", [((64, 64), (31, 31)), ((512, 384), (463, 287))])
def test_supervised_target_remains_actionable_amid_diffuse_background(size, target):
    result = Grounder(ColorBackbone(), ColorText(), ColorPresenceHead(), temperature=1).ground(
        target_image(size, target), "red"
    )
    assert result.point == pytest.approx(target, abs=3)
    assert result.confidence > .55


def test_configured_presence_floor_refuses_a_localized_but_weak_target():
    image = target_image((64, 64), (31, 31))
    result = Grounder(ColorBackbone(), ColorText(), ColorPresenceHead(), temperature=1,
                      presence_threshold=.999).ground(image, "red")
    assert result.confidence == 0


def test_equally_supported_supervised_targets_require_replanning():
    image = target_image((128, 64), (19, 31))
    image.putpixel((99, 31), (255, 0, 0))
    result = Grounder(ColorBackbone(), ColorText(), ColorPresenceHead(), temperature=1).ground(
        image, "red"
    )
    assert result.confidence < .55


def test_query_and_region_change_the_actual_pixel_target():
    image = target_image((128, 64), (19, 31))
    image.putpixel((99, 31), (0, 255, 0))
    assert grounder().ground(image, "red").point == pytest.approx((19, 31), abs=3)
    assert grounder().ground(image, "green").point == pytest.approx((99, 31), abs=3)
    region = BoundingBox(x1=0.5, y1=0, x2=1, y2=1)
    scoped = grounder().ground(image, "red", region)
    assert scoped.point[0] >= 64
    assert scoped.confidence == pytest.approx(0, abs=1e-9)


def test_flat_or_spatially_ambiguous_heatmaps_have_zero_confidence():
    flat = grounder().ground(Image.new("RGB", (128, 64)), "red")
    assert flat.entropy == pytest.approx(1, abs=1e-9)
    assert flat.confidence == pytest.approx(0, abs=1e-9)
    image = target_image((128, 64), (19, 31))
    image.putpixel((99, 31), (255, 0, 0))
    assert grounder().ground(image, "red").confidence == pytest.approx(0, abs=1e-9)


def test_contiguous_wide_target_is_confident_even_with_many_equally_valid_pixels():
    image = Image.new("RGB", (128, 128))
    ImageDraw.Draw(image).rectangle((24, 24, 95, 95), fill="red")
    result = grounder().ground(image, "red")
    assert result.confidence > 0.55
    assert 24 <= result.point[0] <= 95 and 24 <= result.point[1] <= 95
    assert result.entropy > 0.5
    x1, y1, x2, y2 = result.target_region
    assert x1 <= result.point[0] < x2 and y1 <= result.point[1] < y2


def test_two_distant_equal_target_regions_do_not_pass_default_confidence_threshold():
    image = Image.new("RGB", (128, 64))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 43, 43), fill="red")
    draw.rectangle((84, 12, 115, 43), fill="red")
    assert grounder().ground(image, "red").confidence <= 0.5


def test_explicit_horizontal_line_unifies_fragmented_collinear_support():
    image = Image.new("RGB", (64, 64))
    for x in range(8, 57, 8):
        image.putpixel((x, 31), (255, 0, 0))
    assert grounder().ground(image, "red").confidence < 0.55
    result = grounder().ground(image, "red", geometry="horizontal_line")
    assert result.confidence > 0.55
    assert result.point[1] == pytest.approx(31, abs=3)
    assert 5 <= result.point[0] <= 59


def test_horizontal_line_does_not_merge_competing_parallel_boundaries():
    image = Image.new("RGB", (64, 64))
    for y in (15, 47):
        for x in range(8, 57, 8):
            image.putpixel((x, y), (255, 0, 0))
    assert grounder().ground(image, "red", geometry="horizontal_line").confidence < 0.55


def test_isolated_point_or_blank_cannot_establish_horizontal_line():
    image = target_image((64, 64), (31, 31))
    assert grounder().ground(image, "red", geometry="horizontal_line").confidence == 0
    assert grounder().ground(Image.new("RGB", (64, 64)), "red",
                             geometry="horizontal_line").confidence == 0


@pytest.mark.parametrize("geometry", ["circle", True, None, []])
def test_unsupported_target_geometry_is_rejected(geometry):
    with pytest.raises(ValueError, match="unsupported visual target geometry"):
        grounder().ground(target_image((64, 64), (31, 31)), "red", geometry=geometry)


def test_low_contrast_spatial_evidence_cannot_claim_a_unique_region():
    class LowContrastHead:
        def predict(self, features, text):
            return SpatialPrediction(
                [
                    [score * 0.025 for score in row]
                    for row in NormalizedDotProductHead().predict(features, text).scores
                ]
            )

    result = Grounder(ColorBackbone(), ColorText(), LowContrastHead()).ground(
        target_image((128, 64), (19, 31)), "red"
    )
    assert result.confidence == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_spatial_scores_fail_closed(bad):
    class BadHead:
        def predict(self, features, text):
            return SpatialPrediction([[bad] * 16 for _ in range(16)])

    with pytest.raises(ValueError, match="finite"):
        Grounder(ColorBackbone(), ColorText(), BadHead()).ground(Image.new("RGB", (64, 64)), "red")


def test_dot_product_normalizes_both_modalities_and_rejects_invalid_vectors():
    head = NormalizedDotProductHead()
    assert head.predict([[(3, 4), (0, 9)]], (6, 8)).scores[0] == pytest.approx([1, 0.8])
    with pytest.raises(ValueError, match="dimension"):
        head.predict([[(1, 2)]], (1, 2, 3))
    with pytest.raises(ValueError, match="norm"):
        head.predict([[(0, 0)]], (1, 2))
    with pytest.raises(ValueError, match="finite"):
        head.predict([[(1, math.nan)]], (1, 2))


def test_refinement_preserves_coordinates_for_offset_region():
    image = target_image((200, 100), (175, 73))
    region = BoundingBox(x1=0.6, y1=0.4, x2=1, y2=1)
    result = grounder().ground(image, "red", region, refinement=2)
    assert result.point == pytest.approx((175, 73), abs=3)
    assert result.coarse_roi[0] >= 120 and result.coarse_roi[1] >= 40


def test_fine_heatmap_is_probability_mass_over_valid_original_pixels():
    result = grounder().ground(target_image((91, 37), (90, 36)), "red")
    assert sum(probability for _, _, probability in result.heatmap) == pytest.approx(1, abs=1e-9)
    assert all(0 <= x < 91 and 0 <= y < 37 and 0 <= p <= 1 for x, y, p in result.heatmap)


@pytest.mark.parametrize("kwargs", [{"query": " "}, {"refinement": -1}, {"refinement": 5}])
def test_invalid_grounding_request_is_rejected(kwargs):
    with pytest.raises(ValueError):
        grounder().ground(Image.new("RGB", (64, 64)), **({"query": "red"} | kwargs))


def test_subpatch_offsets_follow_separate_inverse_resize_axes_and_keep_anchor_topology():
    class OffsetHead:
        def predict(self, features, text):
            return SpatialPrediction(
                [[-10, -10, 10, -10], [-10] * 4],
                [[[0.25, 0.4]] * 4 for _ in range(2)],
                [[0.99] * 4 for _ in range(2)],
            )

    g = Grounder(ColorBackbone(), ColorText(), OffsetHead(), temperature=1)
    samples = g._samples(Image.new("RGB", (111, 57)), (10, 10, 101, 47), (1, 0, 0))
    selected = max(samples, key=lambda sample: sample.score)
    # 91x37 -> 64x26 at padding (0,19); offsets use the 16x32 model patch.
    assert (selected.x, selected.y) == pytest.approx((10 + 44 * 91 / 64, 10 + 9.8 * 37 / 26))
    assert (selected.center_x, selected.center_y) == pytest.approx(
        (10 + 40 * 91 / 64, 10 - 3 * 37 / 26)
    )
    assert all(10 <= s.x < 101 and 10 <= s.y < 47 for s in samples)


def test_binary_absence_score_rejects_a_spatially_unique_peak():
    class AbsentHead:
        def predict(self, features, text):
            prediction = NormalizedDotProductHead().predict(features, text)
            return SpatialPrediction(
                [[20 * score for score in row] for row in prediction.scores],
                target_probabilities=[[0.02] * len(row) for row in prediction.scores],
            )

    result = Grounder(ColorBackbone(), ColorText(), AbsentHead(), temperature=1).ground(
        target_image((64, 64), (19, 31)), "red"
    )
    assert result.point == pytest.approx((19, 31), abs=4)
    assert result.confidence <= 0.02


@pytest.mark.parametrize("offset", [(float("nan"), 0), (0.51, 0)])
def test_invalid_subpatch_offsets_fail_closed(offset):
    class InvalidOffsetHead:
        def predict(self, features, text):
            return SpatialPrediction([[0]], [[offset]])

    with pytest.raises(ValueError, match="offsets"):
        Grounder(ColorBackbone(), ColorText(), InvalidOffsetHead()).ground(
            Image.new("RGB", (64, 64)), "red"
        )


@pytest.mark.parametrize(
    "fine_kind,supervised,expected",
    [
        ("positive", True, 0.99),
        ("negative", True, 0.01),
        ("islands", True, 0.5),
        ("positive", False, 0),
    ],
)
def test_dense_fine_crop_can_be_entirely_positive_without_bypassing_ambiguity(
    fine_kind, supervised, expected
):
    class PresenceHead:
        dense_head = SimpleNamespace(coarse_strategies={"tiled"}) if supervised else None

        def predict(self, features, text):
            scores = NormalizedDotProductHead().predict(features, text).scores
            scores = [[20 if value > 0.9 else -20 for value in row] for row in scores]
            if all(value == 20 for row in scores for value in row):
                if fine_kind == "negative":
                    scores = [[-20] * len(row) for row in scores]
                elif fine_kind == "islands":
                    scores = [
                        [20 if i < 4 or i >= 12 else -20 for i in range(len(row))] for row in scores
                    ]
            return SpatialPrediction(
                scores,
                [[[0.5, 0.5]] * len(row) for row in scores],
                [[0.99 if value == 20 else 0.01 for value in row] for row in scores]
                if supervised else None,
            )

    image = Image.new("RGB", (128, 64))
    ImageDraw.Draw(image).rectangle((20, 20, 43, 43), fill="red")
    result = Grounder(ColorBackbone(), ColorText(), PresenceHead(), temperature=1).ground(
        image, "red", refinement=2
    )
    if fine_kind == "positive" and supervised:
        assert result.confidence == pytest.approx(expected, abs=1e-6)
    else:
        assert result.confidence <= expected


def test_dense_positive_fine_crop_cannot_override_flat_unknown_coarse_domain():
    class EntirelyPositiveHead:
        dense_head = SimpleNamespace(coarse_strategies={"tiled"})

        def predict(self, features, text):
            return SpatialPrediction(
                [[20] * 16 for _ in range(16)],
                target_probabilities=[[0.99] * 16 for _ in range(16)],
            )

    result = Grounder(ColorBackbone(), ColorText(), EntirelyPositiveHead(), temperature=1).ground(
        Image.new("RGB", (128, 64), "red"), "red", refinement=2
    )
    assert result.confidence == 0
