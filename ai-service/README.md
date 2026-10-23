# SkillBridge AI/ML & Skill Intelligence Service

**Role**: Person 3 — AI/ML & Skill Intelligence Service Lead  
**Package**: `ai-service`  
**Framework**: Python 3.10+ / FastAPI / Pydantic v2 / Uvicorn  
**Port**: `8000` (Default)  

---

## 1. Overview & Architecture

The SkillBridge AI/ML service is a high-performance, stateless microservice that powers automated skill extraction, evidence-aware proficiency scoring, job/role matching, candidate ranking, and personalized skill-gap learning path recommendations.

### Architectural Boundary & Separation of Concerns
```
+-----------------------------------------------------------+
|                     React Frontend                        |
+-----------------------------------------------------------+
                              |
                              v  (HTTP / REST / JWT Auth)
+-----------------------------------------------------------+
|                   Express Application API                 |
|  - Owns User Auth, RBAC & Session Management              |
|  - Owns MongoDB Persistence & Transaction History         |
|  - Orchestrates Ingestion (Resumes, Assessments, GitHub)  |
+-----------------------------------------------------------+
                              |
                              v  (Internal HTTP / JSON Contract)
+-----------------------------------------------------------+
|       SkillBridge AI/ML Skill Intelligence Service        |
|  - Pure Stateless Evaluation & Mathematical Modeling      |
|  - Evidence-Weighted Scoring & Corroboration Engine       |
|  - Deterministic Candidate-Role Matcher & Ranker          |
|  - Curriculum Gap Analyzer & Sample Resource Recommender  |
+-----------------------------------------------------------+
```

> **Design Principle**: This service is completely **stateless** and does **not** connect directly to MongoDB. The Express API owns user authorization and data persistence, invoking this Python service via structured HTTP REST contracts.

---

## 2. Directory Structure

```
ai-service/
├── .env.example                     # Sample environment configuration
├── Dockerfile                       # Multi-stage container definition
├── pyproject.toml                   # Project metadata and pytest configuration
├── requirements.txt                 # Production dependencies
├── requirements-dev.txt             # Testing and linting dependencies
├── run.py                           # Direct Python server launcher
├── README.md                        # Service documentation
├── EXPRESS_INTEGRATION_GUIDE.md     # Node.js/Express client integration manual
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app entry point & error handlers
│   ├── config.py                    # Pydantic Settings & environment parsing
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── health.py            # GET /health & telemetry
│   │       ├── skills.py            # POST /skills/extract, POST /skills/score
│   │       ├── matches.py           # POST /matches/rank
│   │       └── gaps.py              # POST /gaps/analyze
│   ├── models/
│   │   ├── common.py                # Enums (SkillCategory, EvidenceSourceType)
│   │   ├── extract.py               # Pydantic schemas for extraction
│   │   ├── score.py                 # Pydantic schemas for evidence scoring
│   │   ├── match.py                 # Pydantic schemas for role matching & ranking
│   │   └── gap.py                   # Pydantic schemas for gap analysis
│   ├── services/
│   │   ├── extractor.py             # Skill extraction & disambiguation engine
│   │   ├── scorer.py                # Evidence scoring & confidence estimation
│   │   ├── matcher.py               # Role matcher & multi-candidate ranker
│   │   └── recommender.py           # Gap analyzer & sample resource recommender
│   ├── data/
│   │   ├── taxonomy.json            # Curated canonical technical taxonomy
│   │   └── resources.json           # Curated sample learning resource catalogue
│   └── utils/
│       └── logging.py               # PII-sanitizing structured logger
├── fixtures/
│   ├── sample_resumes.json          # Test fixtures for resume texts
│   ├── sample_job_postings.json     # Test fixtures for role requirements
│   └── sample_student_profiles.json # Test fixtures for student evidence portfolios
└── tests/
    ├── conftest.py                  # Pytest fixtures and test clients
    ├── test_health.py               # Health & status endpoint tests
    ├── test_extract.py              # Extraction & disambiguation tests
    ├── test_score.py                # Scoring, recency decay & corroboration tests
    ├── test_match.py                # Matcher, critical penalty & ranking tests
    └── test_gap.py                  # Gap analyzer & sample resource tests
```

---

## 3. Quick Start & Execution

### Option A: Local Python Environment
```bash
# Navigate to service directory
cd ai-service

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
.venv\Scripts\activate          # On Windows

# Install production dependencies
pip install -r requirements.txt

# Run server with default settings
python run.py
```
The server will bind to `http://0.0.0.0:8000`.
- **Interactive Swagger Docs**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`
- **Health Check**: `http://localhost:8000/health`

### Option B: Docker Container
```bash
cd ai-service
docker build -t skillbridge-ai-service:latest .
docker run -d -p 8000:8000 --name skillbridge-ai skillbridge-ai-service:latest
```

### Option C: Running the Test Suite
```bash
cd ai-service
pip install -r requirements-dev.txt
pytest -v
```

---

## 4. Environment Variables & Configuration

Configure using `.env` or system environment variables:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | string | `development` | Runtime mode (`development`, `staging`, `production`) |
| `HOST` | string | `0.0.0.0` | Network interface to bind |
| `PORT` | integer | `8000` | Port number |
| `CORS_ORIGINS` | string / list | `http://localhost:3000,http://localhost:5000` | Allowed CORS origins for Express and UI |
| `LOG_LEVEL` | string | `INFO` | Logger verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `SANITIZE_LOG_PII` | boolean | `true` | Automatically scrubs emails, phones, and auth tokens from logs |
| `DEFAULT_RECENCY_HALF_LIFE_DAYS` | integer | `365` | Days after which evidence weight decays by 50% |
| `DEFAULT_RECENCY_FLOOR` | float | `0.25` | Minimum multiplier floor for historical evidence |
| `CORROBORATION_BONUS_PER_SOURCE` | float | `0.08` | Confidence boost per distinct corroborating source |
| `MAX_CORROBORATION_BONUS` | float | `0.24` | Maximum ceiling for multi-source corroboration boost |

---

## 5. Endpoints & API Contract Reference

All functional API endpoints are versioned under prefix `/api/v1`.

### 5.1 GET `/health` (and `/api/v1/health`)
Provides liveness, uptime, and taxonomy status.

**Response Example (`200 OK`)**:
```json
{
  "status": "ok",
  "service": "SkillBridge Skill Intelligence Service",
  "version": "1.0.0",
  "environment": "development",
  "uptime_seconds": 142.5,
  "active_taxonomy_skills": 36,
  "active_resource_catalogue_skills": 13,
  "timestamp": "2026-10-23T17:35:00.000000Z"
}
```

---

### 5.2 POST `/api/v1/skills/extract`
Extracts canonical technical skills and tools from unstructured text (resumes, job postings, project logs).

**Request Body**:
```json
{
  "text": "Full stack developer with 3 years experience building APIs in Python and FastAPI, frontend in React, and PostgreSQL on AWS.",
  "document_type": "resume",
  "confidence_threshold": 0.40,
  "include_context": true
}
```

**Response (`200 OK`)**:
```json
{
  "skills": [
    {
      "skill_id": "fastapi",
      "canonical_name": "FastAPI",
      "category": "framework",
      "confidence": 0.85,
      "matched_text": "FastAPI",
      "start_char": 67,
      "end_char": 74,
      "context_snippet": "...experience building APIs in Python and FastAPI, frontend in React, and PostgreSQL...",
      "section_header": null
    },
    {
      "skill_id": "python",
      "canonical_name": "Python",
      "category": "programming_language",
      "confidence": 0.85,
      "matched_text": "Python",
      "start_char": 56,
      "end_char": 62,
      "context_snippet": "...experience building APIs in Python and FastAPI...",
      "section_header": null
    }
  ],
  "total_detected": 5,
  "document_type": "resume",
  "metadata": {
    "pipeline": "rule_taxonomy_baseline_v1",
    "version": "1.0.0",
    "execution_time_ms": 3.42,
    "methodology": "Contextual boundary-aware taxonomy matching with section detection and disambiguation.",
    "limitations": "Statistical rule baseline over curated taxonomy. Does not use deep neural text parsing. Pluggable for transformer models."
  }
}
```

---

### 5.3 POST `/api/v1/skills/score`
Computes evidence-weighted proficiency scores (0-100) and confidence estimates (0.0-1.0) from student artifacts.

**Request Body**:
```json
{
  "candidate_id": "student_102",
  "evidence": [
    {
      "skill_id": "python",
      "source_type": "verified_assessment",
      "verification_status": "verified",
      "raw_score": 92.0,
      "days_ago": 30,
      "title": "Backend Engineering Assessment"
    },
    {
      "skill_id": "python",
      "source_type": "capstone_project",
      "verification_status": "verified",
      "raw_score": 88.0,
      "days_ago": 90,
      "title": "Distributed Task Queue Project"
    },
    {
      "skill_id": "docker",
      "source_type": "github_repository",
      "verification_status": "unverified",
      "raw_score": 75.0,
      "days_ago": 15,
      "title": "Multi-stage Container Build Repo"
    }
  ]
}
```

**Response (`200 OK`)**:
```json
{
  "candidate_id": "student_102",
  "overall_skill_index": 84.12,
  "skills": [
    {
      "skill_id": "python",
      "canonical_name": "Python",
      "category": "programming_language",
      "composite_score": 90.15,
      "confidence": 0.95,
      "evidence_count": 2,
      "distinct_sources": ["capstone_project", "verified_assessment"],
      "corroboration_bonus_applied": 0.08,
      "factors": [
        {
          "source_type": "verified_assessment",
          "raw_score": 92.0,
          "source_weight": 1.0,
          "verification_multiplier": 1.15,
          "recency_factor": 0.9442,
          "weighted_contribution": 99.89,
          "is_rejected": false
        }
      ],
      "explanation": "Python scored at 90.2/100 (high proficiency) backed by 2 evidence item(s) across source(s): [capstone_project, verified_assessment]. Confidence level is 95.0%, including a +8.0% independent corroboration boost."
    }
  ],
  "explainability_summary": "Evaluated 3 evidence records across 2 distinct skills. Aggregate skill index: 84.1/100...",
  "scoring_version": "evidence_weighted_v1.0",
  "disclaimer": "Scores and confidence estimates are computed purely from submitted academic and technical evidence factors. No demographic, sensitive, or protected attributes are accepted or processed."
}
```

---

### 5.4 POST `/api/v1/matches/rank`
Ranks multiple candidate portfolios against target job/role criteria.

**Request Body**:
```json
{
  "role": {
    "role_id": "role_backend_jr",
    "role_title": "Junior Python Backend Developer",
    "required_skills": [
      { "skill_id": "python", "minimum_score": 70.0, "importance": "critical" },
      { "skill_id": "fastapi", "minimum_score": 60.0, "importance": "important" },
      { "skill_id": "postgresql", "minimum_score": 60.0, "importance": "important" },
      { "skill_id": "docker", "minimum_score": 50.0, "importance": "nice_to_have" }
    ]
  },
  "candidates": [
    {
      "candidate_id": "alice",
      "skills": [
        { "skill_id": "python", "score": 88.0, "confidence": 0.95 },
        { "skill_id": "fastapi", "score": 80.0, "confidence": 0.85 },
        { "skill_id": "postgresql", "score": 75.0, "confidence": 0.80 },
        { "skill_id": "docker", "score": 65.0, "confidence": 0.70 }
      ]
    },
    {
      "candidate_id": "bob",
      "skills": [
        { "skill_id": "python", "score": 65.0, "confidence": 0.70 },
        { "skill_id": "fastapi", "score": 45.0, "confidence": 0.60 }
      ]
    }
  ],
  "top_k": 5
}
```

**Response (`200 OK`)**:
```json
{
  "role_id": "role_backend_jr",
  "role_title": "Junior Python Backend Developer",
  "total_candidates_evaluated": 2,
  "rankings": [
    {
      "candidate_id": "alice",
      "rank": 1,
      "match_score": 88.42,
      "fit_level": "Strong Fit",
      "matched_skills": [ ... ],
      "weak_skills": [ ... ],
      "missing_skills": [ ... ],
      "strengths": ["Python (88.0/100)", "FastAPI (80.0/100)", "PostgreSQL (75.0/100)"],
      "reasons": ["Satisfies 4 of 4 required competencies."],
      "explainability": "Candidate achieved match score 88.4/100 (Strong Fit) for role 'Junior Python Backend Developer'. Evaluated against 4 requirements. Matched: 4, Weak: 0, Missing: 0."
    }
  ],
  "explainability_notes": "Ranked 2 candidate(s) for role 'Junior Python Backend Developer'...",
  "fairness_statement": "Ranking is computed solely through mathematical evaluation of demonstrated skill proficiencies against documented role specifications. Personal identities and protected attributes are neither solicited nor evaluated."
}
```

---

### 5.5 POST `/api/v1/gaps/analyze`
Identifies deficits against target career goals and maps personalized learning assets.

**Request Body**:
```json
{
  "student_id": "stud_102",
  "target_role_title": "Full Stack Cloud Engineer",
  "target_skills": [
    { "skill_id": "python", "target_score": 75.0, "priority": "high" },
    { "skill_id": "react", "target_score": 70.0, "priority": "high" },
    { "skill_id": "docker", "target_score": 60.0, "priority": "critical" }
  ],
  "current_skills": [
    { "skill_id": "python", "current_score": 80.0, "confidence": 0.90 },
    { "skill_id": "react", "current_score": 40.0, "confidence": 0.75 }
  ],
  "max_recommendations_per_skill": 2
}
```

**Response (`200 OK`)**:
```json
{
  "student_id": "stud_102",
  "target_role_title": "Full Stack Cloud Engineer",
  "total_gaps_identified": 2,
  "critical_gaps_count": 1,
  "readiness_percentage": 61.5,
  "gaps": [
    {
      "skill_id": "docker",
      "canonical_name": "Docker",
      "current_score": 0.0,
      "target_score": 60.0,
      "gap_delta": 60.0,
      "urgency": "critical",
      "recommended_action": "Foundational start: Begin introductory fundamentals and build a guided practice project in Docker.",
      "recommended_resources": [
        {
          "resource_id": "res_docker_01",
          "title": "Docker & Containerization for Cloud Applications",
          "provider": "SkillBridge Interactive Sandbox",
          "resource_type": "hands_on_lab",
          "difficulty": "beginner",
          "estimated_hours": 10.0,
          "url": "https://docs.docker.com/get-started/",
          "is_sample": true,
          "description": "Multi-stage Dockerfiles, volume binding, compose orchestration, and container security."
        }
      ]
    }
  ],
  "total_estimated_learning_hours": 34.0,
  "priority_action_plan": [
    "Step 1 [CRITICAL]: Close Docker gap (-60.0 pts) by engaging with 'Docker & Containerization for Cloud Applications'."
  ],
  "explainability": "Evaluated 3 target competencies against student evidence...",
  "sample_resources_disclaimer": "All recommended resources in this response are seeded catalogue sample assets curated for demonstration and structured learning paths."
}
```

---

## 6. Mathematical Models & Scoring Specifications

### 6.1 Evidence Weighting Model
For each submitted evidence item $i$:
$$w_i = W_{\text{source}} \times M_{\text{verif}} \times R_{\text{recency}}$$
Where:
- $W_{\text{source}}$: Source multiplier (Assessment: $1.0$, Capstone: $0.90$, GitHub: $0.80$, Certificate: $0.75$, Peer Review: $0.70$, Resume Mention: $0.50$, Self-reported: $0.40$).
- $M_{\text{verif}}$: Verification factor (Verified: $1.15$, Pending: $0.95$, Unverified: $0.85$, Rejected: $0.0$).
- $R_{\text{recency}} = \max\left(\text{floor},\ 2^{-\frac{\text{days\_ago}}{T_{1/2}}}\right)$ with half-life $T_{1/2} = 365\text{ days}$ and floor $= 0.25$.

Composite skill score:
$$\text{Score} = \frac{\sum (w_i \times \text{raw\_score}_i)}{\sum w_i}$$

### 6.2 Independent Corroboration Bonus
When a skill is corroborated by $N$ distinct evidence source types ($N > 1$):
$$\text{Bonus} = \min(0.24,\ (N - 1) \times 0.08)$$
Confidence estimate combines source rigor, verification reliability, recency, and the multi-source corroboration boost.

### 6.3 Role Matching & Critical Bottleneck Penalty
Required skills are weighted by criticality (Critical: $1.5\times$, Important: $1.0\times$, Nice-to-have: $0.5\times$). If a candidate lacks evidence for a Critical skill, a $-15\%$ bottleneck penalty is applied to prevent unqualified placements in core disciplines.

---

## 7. Ethics, Fairness & Non-Discrimination Guarantees

In accordance with responsible AI standards and the project charter:
1. **Strict Input Sanitization**: Demographic attributes (race, gender, age, disability, nationality, religion, socioeconomic status) are **strictly forbidden** in incoming request schemas and will fail validation.
2. **Transparent Explainability**: Every evaluation produces human-auditable reasons (`explainability`, `reasons`, `factors`) outlining exactly how scores, match status, and recommendations were calculated.
3. **Deterministic Logic**: Given identical technical evidence, the service returns identical results without stochastic drift or generative hallucination.
4. **Sample Resource Disclosure**: Seeded learning resources carry `is_sample: true` tags to prevent misrepresentation as active enterprise LMS integrations.
