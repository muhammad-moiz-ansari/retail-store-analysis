"""Checks for the weighted customer/employee agent."""

from .cust_emp_classifier import CustEmpClassifier


def test_yolo_employee_decision_dominates() -> None:
    role, score, _ = CustEmpClassifier().decide({"yolo": 0.9, "bib_colour": 0.5, "staff_zone": 0.0, "stationary": 0.0})
    assert role == "employee" and score >= 0.6


def test_yolo_customer_decision_overrides_other_factors() -> None:
    role, score, _ = CustEmpClassifier().decide({"yolo": -0.9, "bib_colour": 1.0, "staff_zone": 1.0, "stationary": 1.0})
    assert role == "customer" and score == 0.0


def test_missing_yolo_moves_weight_to_bib() -> None:
    _, _, contributions = CustEmpClassifier().decide({"yolo": None, "bib_colour": 1.0, "staff_zone": 0.0, "stationary": 0.0})
    assert "yolo" not in contributions and contributions["bib_colour"] == 0.85


def test_person_decision_averages_frames_and_skips_missing_yolo() -> None:
    frames = [{"yolo": 1.0, "bib_colour": 0.0}, {"yolo": None, "bib_colour": 0.0}, {"yolo": 0.8, "bib_colour": 0.0}]
    result = CustEmpClassifier().classify_person(frames)
    assert result["factors"]["yolo"] == 0.9 and result["role"] == "employee"


def test_calibrated_reference_takes_the_role_model_slot_and_decides_alone() -> None:
    role, _, contributions = CustEmpClassifier().decide({"reference": 1.0, "yolo": -0.9, "bib_colour": 0.0})
    assert role == "employee" and contributions == {"reference": 0.55, "yolo": 0.0, "bib_colour": 0.0, "staff_zone": 0.0, "stationary": 0.0}
    _, _, blended = CustEmpClassifier({"reference": 0.3, "yolo": 0.25}).decide({"reference": 1.0, "yolo": None, "bib_colour": 1.0})
    assert "yolo" not in blended and blended["bib_colour"] == 0.55  # blended weights still fall back


def test_unknown_band_abstains_near_the_threshold() -> None:
    agent = CustEmpClassifier(threshold=0.45, unknown_band=0.1)
    assert [agent.role_for(s) for s in (0.3, 0.4, 0.5, 0.6)] == ["customer", "unknown", "unknown", "employee"]
