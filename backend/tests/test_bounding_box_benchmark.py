import pytest
from app.services.ai_vision import BoundingBox


def calculate_iou(box_a: BoundingBox, box_b: BoundingBox) -> float:
    """Calculate Intersection over Union (IoU) between two normalized bounding boxes."""
    x_left = max(box_a.x, box_b.x)
    y_top = max(box_a.y, box_b.y)
    x_right = min(box_a.x + box_a.width, box_b.x + box_b.width)
    y_bottom = min(box_a.y + box_a.height, box_b.y + box_b.height)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    box_a_area = box_a.width * box_a.height
    box_b_area = box_b.width * box_b.height
    union_area = box_a_area + box_b_area - intersection_area

    if union_area <= 0:
        return 0.0

    return round(intersection_area / union_area, 4)


# Reference Ground Truth for Canonical UI Components on Benchmark Screen
BENCHMARK_GROUND_TRUTH_DESKTOP = {
    "visual_hierarchy": BoundingBox(x=0.72, y=0.04, width=0.24, height=0.07),
    "typography": BoundingBox(x=0.08, y=0.18, width=0.55, height=0.12),
    "accessibility_indicator": BoundingBox(x=0.08, y=0.32, width=0.40, height=0.06),
}

BENCHMARK_GROUND_TRUTH_MOBILE = {
    "usability": BoundingBox(x=0.05, y=0.88, width=0.90, height=0.09),
    "typography": BoundingBox(x=0.08, y=0.18, width=0.55, height=0.12),
    "accessibility_indicator": BoundingBox(x=0.08, y=0.32, width=0.40, height=0.06),
}


def test_iou_calculation_exact_match():
    box1 = BoundingBox(x=0.1, y=0.1, width=0.2, height=0.2)
    box2 = BoundingBox(x=0.1, y=0.1, width=0.2, height=0.2)
    assert calculate_iou(box1, box2) == 1.0


def test_iou_calculation_disjoint():
    box1 = BoundingBox(x=0.0, y=0.0, width=0.1, height=0.1)
    box2 = BoundingBox(x=0.5, y=0.5, width=0.1, height=0.1)
    assert calculate_iou(box1, box2) == 0.0


def test_iou_partial_overlap():
    box1 = BoundingBox(x=0.0, y=0.0, width=0.2, height=0.2)
    box2 = BoundingBox(x=0.1, y=0.0, width=0.2, height=0.2)
    # intersection: width 0.1, height 0.2 -> 0.02
    # union: 0.04 + 0.04 - 0.02 = 0.06
    # iou: 0.02 / 0.06 = 0.3333
    assert abs(calculate_iou(box1, box2) - 0.3333) < 0.001


def test_vision_engine_benchmark_accuracy_desktop():
    """
    Evaluates vision engine bounding box outputs against reference ground-truth annotations on desktop viewport.
    Target: Mean IoU >= 0.85 across all detected canonical elements.
    """
    from app.services.ai_vision import DeterministicVisionProvider

    provider = DeterministicVisionProvider()
    result = provider.analyze(
        image_bytes=b"benchmark_dummy_bytes",
        mime_type="image/png",
        image_width=1440,
        image_height=900,
    )

    detected_boxes = {}
    for finding in result.findings:
        if finding.bounding_boxes:
            detected_boxes[finding.category] = finding.bounding_boxes[0]

    ious = []
    for cat, gt_box in BENCHMARK_GROUND_TRUTH_DESKTOP.items():
        assert cat in detected_boxes, f"Expected detection for category {cat}"
        detected = detected_boxes[cat]
        iou = calculate_iou(detected, gt_box)
        ious.append(iou)
        assert iou >= 0.70, f"IoU for {cat} is {iou}, expected >= 0.70"

    mean_iou = sum(ious) / len(ious)
    assert mean_iou >= 0.85, f"Mean IoU {mean_iou} below benchmark threshold of 0.85"


def test_vision_engine_benchmark_accuracy_mobile():
    """
    Evaluates vision engine bounding box outputs against reference ground-truth annotations on mobile viewport.
    Target: Mean IoU >= 0.85 across all detected canonical elements.
    """
    from app.services.ai_vision import DeterministicVisionProvider

    provider = DeterministicVisionProvider()
    result = provider.analyze(
        image_bytes=b"benchmark_dummy_bytes",
        mime_type="image/png",
        image_width=390,
        image_height=844,
    )

    detected_boxes = {}
    for finding in result.findings:
        if finding.bounding_boxes:
            detected_boxes[finding.category] = finding.bounding_boxes[0]

    ious = []
    for cat, gt_box in BENCHMARK_GROUND_TRUTH_MOBILE.items():
        assert cat in detected_boxes, f"Expected detection for category {cat}"
        detected = detected_boxes[cat]
        iou = calculate_iou(detected, gt_box)
        ious.append(iou)
        assert iou >= 0.70, f"IoU for {cat} is {iou}, expected >= 0.70"

    mean_iou = sum(ious) / len(ious)
    assert mean_iou >= 0.85, f"Mean IoU {mean_iou} below benchmark threshold of 0.85"

