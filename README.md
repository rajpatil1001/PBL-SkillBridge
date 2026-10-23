# SkillBridge — AI-Powered Skill Intelligence & Career Pathway Platform

Welcome to **SkillBridge**! This repository hosts the Project-Based Learning (PBL) solution for automated skill extraction, evidence-aware proficiency scoring, candidate-role matching, and curriculum gap analysis.

---

## Workspace Structure & Team Roles

This codebase is organized into cleanly decoupled, separable microservices:

| Service Directory | Team Member | Stack | Role Description |
| :--- | :--- | :--- | :--- |
| **`ai-service/`** | **Person 3 (AI/ML Lead)** | **Python / FastAPI / Pydantic** | **Skill extraction, weighted scoring, role matching, candidate ranking, gap analysis, and explainability.** |
| `server/` (or `express-api/`) | Person 2 (Backend Lead) | Node.js / Express / MongoDB | Application API, user auth (JWT/RBAC), data persistence, integrations. |
| `client/` (or `frontend/`) | Person 1 (Frontend Lead) | React / Tailwind CSS | Responsive UI dashboards, student skill views, recruiter match portals. |

---

## AI/ML & Skill Intelligence Service (`ai-service`)

Person 3's service is completely implemented, tested, and ready for integration.

### Quick Start
```bash
# 1. Move into the AI service directory
cd ai-service

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch service
python run.py
```
- **Service URL**: `http://localhost:8000`
- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

### Running Tests
```bash
cd ai-service
pytest -v
```
*Current test suite: 20 passing unit tests covering validation, extraction, scoring, matching, and gap analysis.*

### Integration Guide for Express
See [`ai-service/EXPRESS_INTEGRATION_GUIDE.md`](./ai-service/EXPRESS_INTEGRATION_GUIDE.md) for complete Node.js/Axios client snippets, timeout configurations, and graceful degradation fallback strategies.
