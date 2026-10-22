import math

import numpy as np
import pytest

from app.services.face_embedding import (
    MIN_USABLE_PHOTOS, PhotoReport, average_template, build_template,
)
from app.services.face_quality import check_photo


# ---------- photo quality ----------
def test_good_photo_is_accepted():
    assert check_photo(brightness=120, sharpness=300, face_count=1, face_min_side=200).accepted


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        (dict(brightness=120, sharpness=300, face_count=0, face_min_side=200), "No face"),
        (dict(brightness=120, sharpness=300, face_count=2, face_min_side=200), "More than one"),
        (dict(brightness=20, sharpness=300, face_count=1, face_min_side=200), "too dark"),
        (dict(brightness=240, sharpness=300, face_count=1, face_min_side=200), "too bright"),
        (dict(brightness=120, sharpness=10, face_count=1, face_min_side=200), "too blurry"),
        (dict(brightness=120, sharpness=300, face_count=1, face_min_side=30), "too small"),
    ],
)
def test_bad_photos_are_rejected_with_reason(kwargs, fragment):
    result = check_photo(**kwargs)
    assert not result.accepted
    assert fragment in result.reason


# ---------- template averaging ----------
def test_template_is_unit_length():
    vectors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0]]
    template = average_template(vectors)
    assert math.isclose(np.linalg.norm(template), 1.0, rel_tol=1e-6)


def test_average_is_below_minimum_raises():
    with pytest.raises(ValueError):
        average_template([[1.0, 0.0], [0.0, 1.0]])


def test_template_from_five_good_photos():
    reports = [PhotoReport(True, None, [1.0, 0.1 * i, 0.0]) for i in range(5)]
    template, error = build_template(reports)
    assert error is None
    assert len(template) == 3


def test_template_fails_with_fewer_than_minimum_usable():
    reports = [PhotoReport(True, None, [1.0, 0.0])] * (MIN_USABLE_PHOTOS - 1)
    reports += [PhotoReport(False, "too dark", None)] * 3
    template, error = build_template(reports)
    assert template is None
    assert "clearer photos" in error


def test_rejected_photos_do_not_contribute():
    good = [PhotoReport(True, None, [1.0, 0.0, 0.0])] * 3
    bad = [PhotoReport(False, "blurry", [0.0, 0.0, 1.0])] * 2
    template, _ = build_template(good + bad)
    # Only the three good vectors count, so the result points along the first axis.
    assert template[0] == pytest.approx(1.0)
    assert template[2] == pytest.approx(0.0)