"""Pytest fixtures and configuration."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Session-scoped FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_resume_text() -> str:
    return """
    Jane Doe - Full Stack Software Engineer

    SKILLS
    Python, FastAPI, TypeScript, React, PostgreSQL, Docker, Git

    WORK EXPERIENCE
    Senior Developer at TechCorp (2022 - Present)
    - Architected RESTful APIs using Python and FastAPI serving 1M requests/day.
    - Designed relational schemas and query optimizations in PostgreSQL.
    - Containerized microservices using Docker and orchestrated CI/CD pipelines with GitHub Actions.

    PROJECTS
    Distributed Cache Engine
    - Implemented high-throughput in-memory caching in Go with Redis protocol compatibility.
    """


@pytest.fixture
def sample_evidence_items():
    return [
        {
            "skill_id": "python",
            "source_type": "verified_assessment",
            "verification_status": "verified",
            "raw_score": 95.0,
            "days_ago": 20,
            "title": "Backend Engineering Certification"
        },
        {
            "skill_id": "python",
            "source_type": "capstone_project",
            "verification_status": "verified",
            "raw_score": 90.0,
            "days_ago": 60,
            "title": "Capstone Microservice"
        },
        {
            "skill_id": "docker",
            "source_type": "github_repository",
            "verification_status": "unverified",
            "raw_score": 75.0,
            "days_ago": 15,
            "title": "Docker Compose Manifests"
        },
        {
            "skill_id": "docker",
            "source_type": "resume_mention",
            "verification_status": "unverified",
            "raw_score": 60.0,
            "days_ago": 400,
            "title": "Old Resume Skill List"
        }
    ]
