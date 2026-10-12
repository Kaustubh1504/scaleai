"""Sample data for problem 28: raw rows exactly as a vendor's spreadsheet export hands them over."""

from __future__ import annotations

LABEL_MAPPING = {
    "vehicle": ["car", "truck", "Auto Mobile", "motor_vehicle"],
    "pedestrian": ["person", "walker", "ped"],
    "cyclist": ["bike rider", "bicyclist"],
}

SAMPLE_ROWS = [
    {"task_id": "007", "reward": "$1,234.50", "qa_passed": "Yes", "tags": "night; rain|night", "label": " Car "},
    {"task_id": " t-12 ", "reward": "(5.00)", "qa_passed": "false", "tags": "", "label": "MOTOR_VEHICLE"},
    {"task_id": 7.0, "reward": "12%", "qa_passed": 0, "tags": "fog,, ,fog", "label": "bike   rider"},
    {"task_id": "N/A", "reward": "1e3", "qa_passed": " ON ", "tags": None, "label": "Pedestrian"},
    {"task_id": "T 9", "reward": "12,34", "qa_passed": "maybe", "tags": "snow", "label": "horse"},
]
