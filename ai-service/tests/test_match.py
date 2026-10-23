"""Tests for Role Matching and Multi-Candidate Ranking endpoints."""

from fastapi.testclient import TestClient


def test_rank_candidates_deterministic(client: TestClient):
    payload = {
        "role": {
            "role_id": "role_lead_backend",
            "role_title": "Lead Backend Engineer",
            "required_skills": [
                {"skill_id": "python", "minimum_score": 80.0, "importance": "critical"},
                {"skill_id": "fastapi", "minimum_score": 75.0, "importance": "critical"},
                {"skill_id": "postgresql", "minimum_score": 70.0, "importance": "important"},
                {"skill_id": "docker", "minimum_score": 60.0, "importance": "nice_to_have"},
            ],
        },
        "candidates": [
            {
                "candidate_id": "alice_high_fit",
                "skills": [
                    {"skill_id": "python", "score": 90.0, "confidence": 0.95},
                    {"skill_id": "fastapi", "score": 85.0, "confidence": 0.90},
                    {"skill_id": "postgresql", "score": 80.0, "confidence": 0.85},
                    {"skill_id": "docker", "score": 75.0, "confidence": 0.80},
                ],
            },
            {
                "candidate_id": "bob_moderate_fit",
                "skills": [
                    {"skill_id": "python", "score": 82.0, "confidence": 0.80},
                    {"skill_id": "fastapi", "score": 65.0, "confidence": 0.70},  # weak on critical
                    {"skill_id": "postgresql", "score": 72.0, "confidence": 0.75},
                ],
            },
            {
                "candidate_id": "charlie_missing_critical",
                "skills": [
                    {"skill_id": "docker", "score": 90.0, "confidence": 0.90},
                    {"skill_id": "postgresql", "score": 75.0, "confidence": 0.80},
                ],
            },
        ],
    }

    response = client.post("/api/v1/matches/rank", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["role_id"] == "role_lead_backend"
    assert data["total_candidates_evaluated"] == 3

    rankings = data["rankings"]
    # Alice should be Rank 1
    assert rankings[0]["candidate_id"] == "alice_high_fit"
    assert rankings[0]["rank"] == 1
    assert rankings[0]["fit_level"] in ("Strong Fit", "Moderate Fit")
    assert len(rankings[0]["matched_skills"]) == 4
    assert len(rankings[0]["missing_skills"]) == 0

    # Bob should have weak skills
    bob = next(r for r in rankings if r["candidate_id"] == "bob_moderate_fit")
    assert any(w["skill_id"] == "fastapi" for w in bob["weak_skills"])

    # Charlie is missing critical skills (Python, FastAPI)
    charlie = next(r for r in rankings if r["candidate_id"] == "charlie_missing_critical")
    assert any(m["skill_id"] == "python" for m in charlie["missing_skills"])
    assert charlie["match_score"] < bob["match_score"]


def test_rank_candidates_empty_candidates_validation(client: TestClient):
    payload = {
        "role": {
            "role_id": "role_empty",
            "role_title": "Empty Candidate Test",
            "required_skills": [{"skill_id": "python", "minimum_score": 70.0}],
        },
        "candidates": [],  # Min length 1
    }
    response = client.post("/api/v1/matches/rank", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"
