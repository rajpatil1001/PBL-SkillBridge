"""Tests for Skill Extraction endpoints and disambiguation logic."""

from fastapi.testclient import TestClient


def test_extract_skills_valid_resume(client: TestClient, sample_resume_text: str):
    response = client.post(
        "/api/v1/skills/extract",
        json={
            "text": sample_resume_text,
            "document_type": "resume",
            "confidence_threshold": 0.40,
            "include_context": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_detected"] > 0
    assert data["document_type"] == "resume"
    assert "metadata" in data
    assert data["metadata"]["pipeline"] == "rule_taxonomy_baseline_v1"

    detected_ids = [s["skill_id"] for s in data["skills"]]
    assert "python" in detected_ids
    assert "fastapi" in detected_ids
    assert "react" in detected_ids
    assert "docker" in detected_ids
    assert "postgresql" in detected_ids

    # Check section detection on Python
    py_skill = next(s for s in data["skills"] if s["skill_id"] == "python")
    assert py_skill["confidence"] >= 0.85
    assert py_skill["context_snippet"] is not None


def test_extract_skills_empty_text_validation_error(client: TestClient):
    response = client.post(
        "/api/v1/skills/extract",
        json={"text": "ab"},  # min_length is 3
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"
    assert len(data["details"]) > 0


def test_extract_skills_invalid_threshold(client: TestClient):
    response = client.post(
        "/api/v1/skills/extract",
        json={"text": "Proficient in Python and React.", "confidence_threshold": 1.5},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["error"] == "VALIDATION_ERROR"


def test_extract_disambiguation_ambiguous_words(client: TestClient):
    # Ordinary English sentences using words like 'go' and 'c' should NOT extract them as skills
    text = "We will go to the office and see our colleagues."
    response = client.post(
        "/api/v1/skills/extract",
        json={"text": text, "document_type": "general"},
    )
    assert response.status_code == 200
    detected_ids = [s["skill_id"] for s in response.json()["skills"]]
    assert "go" not in detected_ids

    # Proper Go programming mention should extract 'go'
    text_with_golang = "Backend engineer writing services in Golang and Python."
    response_go = client.post(
        "/api/v1/skills/extract",
        json={"text": text_with_golang, "document_type": "job_description"},
    )
    assert response_go.status_code == 200
    detected_ids_go = [s["skill_id"] for s in response_go.json()["skills"]]
    assert "go" in detected_ids_go
    assert "python" in detected_ids_go


def test_extract_special_character_skills(client: TestClient):
    text = "Core skills include C++, C#, and PostgreSQL with Next.js web applications."
    response = client.post(
        "/api/v1/skills/extract",
        json={"text": text, "document_type": "resume", "confidence_threshold": 0.4},
    )
    assert response.status_code == 200
    detected_ids = [s["skill_id"] for s in response.json()["skills"]]
    assert "cpp" in detected_ids
    assert "csharp" in detected_ids
    assert "postgresql" in detected_ids
    assert "next_js" in detected_ids


def test_extract_section_boosting(client: TestClient):
    # Same skill in 'SKILLS' section vs generic body has higher confidence
    text_with_section = "SKILLS:\nPython, Docker\n\nOTHER:\nGeneral text mention."
    response = client.post(
        "/api/v1/skills/extract",
        json={"text": text_with_section, "document_type": "resume"},
    )
    assert response.status_code == 200
    py = next(s for s in response.json()["skills"] if s["skill_id"] == "python")
    assert py["section_header"] == "SKILLS"
    assert py["confidence"] >= 0.90
