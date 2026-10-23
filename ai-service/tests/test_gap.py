"""Tests for Skill Gap Analysis and Learning Path Recommendation endpoints."""

from fastapi.testclient import TestClient


def test_analyze_gaps_valid(client: TestClient):
    payload = {
        "student_id": "student_dev_42",
        "target_role_title": "Full Stack Cloud Developer",
        "target_skills": [
            {"skill_id": "python", "target_score": 80.0, "priority": "high"},
            {"skill_id": "react", "target_score": 75.0, "priority": "high"},
            {"skill_id": "docker", "target_score": 70.0, "priority": "critical"},
            {"skill_id": "kubernetes", "target_score": 60.0, "priority": "medium"},
        ],
        "current_skills": [
            {"skill_id": "python", "current_score": 85.0, "confidence": 0.90},  # Exceeds target!
            {"skill_id": "react", "current_score": 45.0, "confidence": 0.70},   # Gap = 30 pts
            # Docker & Kubernetes have 0 current score (missing)
        ],
        "max_recommendations_per_skill": 2,
    }

    response = client.post("/api/v1/gaps/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["student_id"] == "student_dev_42"
    assert data["target_role_title"] == "Full Stack Cloud Developer"
    assert data["total_gaps_identified"] == 3  # react, docker, kubernetes
    assert data["critical_gaps_count"] >= 1   # docker is critical missing
    assert data["readiness_percentage"] > 0
    assert data["total_estimated_learning_hours"] > 0
    assert len(data["priority_action_plan"]) > 0

    # Verify sample resource labeling
    for gap in data["gaps"]:
        for resource in gap["recommended_resources"]:
            assert resource["is_sample"] is True
            assert resource["provider"] is not None
            assert resource["estimated_hours"] > 0


def test_analyze_gaps_perfect_profile(client: TestClient):
    # Candidate who satisfies all target skills
    payload = {
        "student_id": "student_expert",
        "target_role_title": "Python Specialist",
        "target_skills": [
            {"skill_id": "python", "target_score": 80.0, "priority": "high"}
        ],
        "current_skills": [
            {"skill_id": "python", "current_score": 90.0, "confidence": 0.95}
        ],
    }
    response = client.post("/api/v1/gaps/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total_gaps_identified"] == 0
    assert data["readiness_percentage"] == 100.0


def test_analyze_gaps_invalid_target_skills(client: TestClient):
    payload = {
        "student_id": "student_fail",
        "target_skills": [],  # Min length 1
    }
    response = client.post("/api/v1/gaps/analyze", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"
