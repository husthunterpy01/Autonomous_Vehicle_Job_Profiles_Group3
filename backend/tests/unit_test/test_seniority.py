import pytest

from app.enums.seniority_type import SeniorityLevel as S
from app.utils.seniority import infer_seniority


@pytest.mark.parametrize(
    ("title", "level"),
    [
        ("Senior Calibration Engineer", S.SENIOR),
        ("Sr. Autonomous Driving Software Engineer", S.SENIOR),
        ("Senior / Staff Software Engineer, Web Tools", S.PRINCIPAL),
        ("Principal Engineer / Director, Motion Planning", S.DIRECTOR),
        ("Senior Engineering Manager, Perception", S.MANAGER),
        ("Head of Autonomy", S.DIRECTOR),
        ("Tech Lead, Simulation", S.LEAD),
        ("Research Intern - Deep Learning", S.JUNIOR),
        ("Compiler Engineer Intern", S.JUNIOR),
        ("Robotic Software Engineer, Perception", S.MID),
        ("Chief Technology Officer", S.CEO),
        (None, S.MID),
    ],
)
def test_infer_seniority(title, level):
    assert infer_seniority(title) == level
