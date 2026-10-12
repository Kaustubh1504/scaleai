"""Sample change-data-capture stream for problem 23: task record versions, out of order."""

from __future__ import annotations

STREAM: list[dict] = [
    {"id": "task_2", "version": 1, "updated_at": "2024-05-01T09:00:00Z", "deleted": False, "status": "queued", "assignee": None},
    {"id": "task_10", "version": 1, "updated_at": "2024-05-01T08:00:00Z", "deleted": False, "status": "queued", "assignee": None},
    {"id": "task_2", "version": 2, "updated_at": "2024-05-01T11:30:00+02:00", "deleted": False, "status": "in_progress", "assignee": "ann_7"},
    {"id": "task_2", "version": 3, "updated_at": "2024-05-01T09:15:00Z", "deleted": False, "status": "submitted", "assignee": "ann_7"},
    {"id": "task_10", "version": 2, "updated_at": "2024-05-01T10:00:00Z", "deleted": True},
    {"id": "task_3", "version": 1, "updated_at": "2024-05-01T12:00:00Z", "deleted": False, "status": "queued", "assignee": None},
    {"id": "task_3", "version": 2, "updated_at": "2024-05-01T12:00:00Z", "deleted": False, "status": "in_progress", "assignee": "ann_2"},
    {"id": "task_3", "version": 2, "updated_at": "2024-05-01T14:00:00+02:00", "deleted": False, "status": "in_progress", "assignee": "ann_2"},
    {"id": "task_7", "version": 4, "updated_at": "2024-05-02T00:00:00Z", "deleted": False, "status": "accepted", "assignee": "ann_1"},
    {"id": "task_7", "version": 4, "updated_at": "2024-05-02T00:00:00Z", "deleted": False, "status": "rejected", "assignee": "ann_1"},
    {"id": "task_5", "version": 1, "updated_at": "2024-05-01T07:00:00-04:00", "status": "queued", "assignee": None},
]
