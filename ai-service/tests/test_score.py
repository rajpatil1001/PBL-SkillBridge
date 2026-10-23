"""Tests for Evidence-Aware Skill Scoring and Confidence Estimation."""

from fastapi.testclient import TestClient


def test_score_skills_valid(client: TestClient, sample_evidence_items):
    response = client.post(
        "/api/v1/skills/score",
        json={
            "candidate_id": "test_candidate_1",
            "evidence": sample_evidence_items,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["candidate_id"] == "test_candidate_1"
    assert data["overall_skill_index"] > 0
    assert len(data["skills"]) == 2  # 'python' and 'docker'

    # Python has verified assessment (95) and capstone (90), both verified
    py_result = next(s for s in data["skills"] if s["skill_id"] == "python")
    assert py_result["composite_score"] >= 90.0
    assert py_result["confidence"] >= 0.85
    assert py_result["evidence_count"] == 2
    assert len(py_result["distinct_sources"]) == 2
    assert py_result["corroboration_bonus_applied"] > 0
    assert "Python" in py_result["explanation"]

    # Docker has unverified GitHub repo (recent) and unverified old resume mention (400 days old)
    docker_result = next(s for s in data["skills"] if s["skill_id"] == "docker")
    assert docker_result["composite_score"] > 0
    # Because one evidence is 400 days old, recency factor must have decayed
    recency_factors = [f["recency_factor"] for f in docker_result["factors"]]
    assert any(rf < 0.6 for rf in recency_factors)


def test_score_skills_rejected_evidence(client: TestClient):
    evidence = [
        {
            "skill_id": "fastapi",
            "source_type": "self_reported",
            "verification_status": "rejected",
            "raw_score": 100.0,
            "days_ago": 0,
        }
    ]
    response = client.post(
        "/api/v1/skills/score",
        json={"candidate_id": "cand_rejected", "evidence": evidence},
    )
    assert response.status_code == 200
    data = response.json()
    fastapi_result = data["skills"][0]
    assert fastapi_result["composite_score"] == 0.0
    assert fastapi_result["factors"][0]["is_rejected"] is True


def test_score_skills_empty_evidence_validation(client: TestClient):
    response = client.post(
        "/api/v1/skills/score",
        json={"candidate_id": "cand_empty", "evidence": []},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"


def test_score_skills_invalid_score_range(client: TestClient):
    evidence = [
        {
            "skill_id": "python",
            "source_type": "verified_assessment",
            "raw_score": 150.0,  # Max is 100
        }
    ]
    response = client.post(
        "/api/v1/skills/score",
        json={"candidate_id": "cand_invalid", "evidence": evidence},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"


def test_score_skills_multi_source_corroboration(client: TestClient):
    evidence = [
        {
            "skill_id": "typescript",
            "source_type": "verified_assessment",
            "verification_status": "verified",
            "raw_score": 90.0,
            "days_ago": 10,
        },
        {
            "skill_id": "typescript",
            "source_type": "capstone_project",
            "verification_status": "verified",
            "raw_score": 85.0,
            "days_ago": 20,
        },
        {
            "skill_id": "typescript",
            "source_type": "github_repository",
            "verification_status": "unverified",
            "raw_score": 80.0,
            "days_ago": 5,
        },
    ]
    response = client.post(
        "/api/v1/skills/score",
        json={"candidate_id": "cand_ts_expert", "evidence": evidence},
    )
    assert response.status_code == 200
    ts = response.json()["skills"][0]
    assert len(ts["distinct_sources"]) == 3
    assert ts["corroboration_bonus_applied"] == 0.16
    assert ts["confidence"] >= 0.85


def test_score_skills_custom_weight_config(client: TestClient):
    evidence = [
        {
            "skill_id": "python",
            "source_type": "self_reported",
            "verification_status": "verified",
            "raw_score": 80.0,
            "days_ago": 0,
        }
    ]
    custom_cfg = {
        "source_weights": {"self_reported": 1.5},
        "verification_multipliers": {"verified": 1.0},
        "recency_half_life_days": 180,
    }
    response = client.post(
        "/api/v1/skills/score",
        json={
            "candidate_id": "cand_custom",
            "evidence": evidence,
            "weight_config": custom_cfg,
        },
    )
    assert response.status_code == 200
    py = response.json()["skills"][0]
    assert py["factors"][0]["source_weight"] == 1.5
