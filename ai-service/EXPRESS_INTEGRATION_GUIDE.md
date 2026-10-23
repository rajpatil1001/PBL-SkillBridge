# Express API Integration Guide (For Person 1 & Person 2)

This document provides complete instructions, architecture contracts, and production-ready Node.js/Express code snippets for communicating with Person 3's Python FastAPI AI/ML Skill Intelligence Service.

---

## 1. Architectural Roles & Contract Boundary

| Responsibility | Express API (Person 1 / 2) | Python AI/ML Service (Person 3) |
| :--- | :--- | :--- |
| **User Authentication & RBAC** | ✅ Owns JWTs, sessions, role permissions | ❌ Stateless; does not inspect user tokens |
| **Data Persistence (MongoDB)** | ✅ Owns collections, schemas, migrations | ❌ No direct database connection |
| **Ingestion & File Parsing** | ✅ Reads PDF resumes, pulls GitHub webhooks | ❌ Receives pre-extracted raw text / evidence |
| **Skill Extraction & Disambiguation** | ❌ Delegates to Python service | ✅ Runs contextual taxonomy parser |
| **Evidence Scoring & Corroboration** | ❌ Delegates to Python service | ✅ Runs mathematical weighting & recency decay |
| **Role Matching & Candidate Ranking** | ❌ Delegates to Python service | ✅ Deterministic ranking with bottleneck penalty |
| **Gap Analysis & Recommendations** | ❌ Delegates to Python service | ✅ Computes gap deltas & learning catalog matches |

---

## 2. Configuration & Environment Variables in Express

Add the following to your Express `.env` configuration:

```env
# AI/ML Service Connection
AI_SERVICE_URL=http://localhost:8000
AI_SERVICE_TIMEOUT_MS=6000
AI_SERVICE_MAX_RETRIES=2
```

---

## 3. Production Node.js Client Implementation

Below is a complete, copy-paste ready TypeScript/ES6 service class utilizing `axios` with configured timeouts, retry logic with exponential backoff, and standardized fallback responses.

```typescript
// src/services/aiIntelligenceClient.ts
import axios, { AxiosInstance, AxiosError } from 'axios';

export interface ExtractSkillsPayload {
  text: string;
  document_type?: 'resume' | 'project' | 'job_description' | 'syllabus' | 'general';
  confidence_threshold?: number;
  include_context?: boolean;
}

export interface ScoreSkillsPayload {
  candidate_id: string;
  evidence: Array<{
    skill_id: string;
    source_type: 'verified_assessment' | 'course_certificate' | 'capstone_project' | 'github_repository' | 'resume_mention' | 'interview_evaluation' | 'peer_review' | 'self_reported';
    verification_status?: 'verified' | 'pending_verification' | 'unverified' | 'rejected';
    raw_score: number;
    days_ago?: number;
    title?: string;
  }>;
}

export interface RankMatchesPayload {
  role: {
    role_id: string;
    role_title: string;
    required_skills: Array<{
      skill_id: string;
      minimum_score?: number;
      importance?: 'critical' | 'important' | 'nice_to_have';
    }>;
  };
  candidates: Array<{
    candidate_id: string;
    skills: Array<{
      skill_id: string;
      score: number;
      confidence?: number;
    }>;
  }>;
  top_k?: number;
}

export interface AnalyzeGapsPayload {
  student_id: string;
  target_role_title?: string;
  target_skills: Array<{
    skill_id: string;
    target_score?: number;
    priority?: 'critical' | 'high' | 'medium' | 'low';
  }>;
  current_skills?: Array<{
    skill_id: string;
    current_score: number;
    confidence?: number;
  }>;
  max_recommendations_per_skill?: number;
}

export class AIIntelligenceClient {
  private client: AxiosInstance;
  private readonly maxRetries: number;

  constructor(baseURL: string = process.env.AI_SERVICE_URL || 'http://localhost:8000') {
    this.maxRetries = parseInt(process.env.AI_SERVICE_MAX_RETRIES || '2', 10);
    this.client = axios.create({
      baseURL,
      timeout: parseInt(process.env.AI_SERVICE_TIMEOUT_MS || '6000', 10),
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    });
  }

  /**
   * Internal request executor with exponential backoff retry.
   */
  private async executeWithRetry<T>(fn: () => Promise<T>, retriesLeft = this.maxRetries): Promise<T> {
    try {
      return await fn();
    } catch (err: any) {
      const isNetworkOrTimeout = err.code === 'ECONNABORTED' || !err.response || err.response.status >= 500;
      if (retriesLeft > 0 && isNetworkOrTimeout) {
        const delayMs = (this.maxRetries - retriesLeft + 1) * 300;
        await new Promise((resolve) => setTimeout(resolve, delayMs));
        return this.executeWithRetry(fn, retriesLeft - 1);
      }
      throw err;
    }
  }

  /**
   * Health Check
   */
  async checkHealth(): Promise<{ status: string; version: string; active_taxonomy_skills: number }> {
    const res = await this.client.get('/health');
    return res.data;
  }

  /**
   * Extract skills from unstructured text
   */
  async extractSkills(payload: ExtractSkillsPayload) {
    return this.executeWithRetry(async () => {
      const res = await this.client.post('/api/v1/skills/extract', payload);
      return res.data;
    });
  }

  /**
   * Score candidate skill evidence with multi-source corroboration and recency decay
   */
  async scoreSkills(payload: ScoreSkillsPayload) {
    return this.executeWithRetry(async () => {
      const res = await this.client.post('/api/v1/skills/score', payload);
      return res.data;
    });
  }

  /**
   * Rank candidates against job requirements
   */
  async rankCandidates(payload: RankMatchesPayload) {
    return this.executeWithRetry(async () => {
      const res = await this.client.post('/api/v1/matches/rank', payload);
      return res.data;
    });
  }

  /**
   * Analyze student curriculum gaps and fetch sample learning recommendations
   */
  async analyzeGaps(payload: AnalyzeGapsPayload) {
    return this.executeWithRetry(async () => {
      const res = await this.client.post('/api/v1/gaps/analyze', payload);
      return res.data;
    });
  }
}

export const aiClient = new AIIntelligenceClient();
```

---

## 4. Failure Handling & Circuit Breaker / Graceful Fallbacks

In the event that the Python microservice is temporarily starting up, recovering, or experiencing network latency, the Express layer should never crash or return raw 500 errors to end users.

### Express Route Handler with Fallback Pattern:
```javascript
// src/routes/matches.js (Express Route)
import express from 'express';
import { aiClient } from '../services/aiIntelligenceClient.js';

const router = express.Router();

router.post('/role/:roleId/rank-candidates', async (req, res) => {
  try {
    const { roleId } = req.params;
    // 1. Fetch role requirements from MongoDB
    const roleDoc = await RoleModel.findById(roleId);
    
    // 2. Fetch candidate evidence profiles from MongoDB
    const candidates = await StudentModel.find({ active: true }).limit(50);

    // 3. Format payload according to contract
    const payload = {
      role: {
        role_id: roleDoc._id.toString(),
        role_title: roleDoc.title,
        required_skills: roleDoc.requiredSkills.map(s => ({
          skill_id: s.skillId,
          minimum_score: s.minScore,
          importance: s.importance
        }))
      },
      candidates: candidates.map(c => ({
        candidate_id: c._id.toString(),
        skills: c.evaluatedSkills.map(es => ({
          skill_id: es.skillId,
          score: es.score,
          confidence: es.confidence
        }))
      }))
    };

    // 4. Call AI Intelligence Service
    const aiResponse = await aiClient.rankCandidates(payload);
    return res.status(200).json({ success: true, data: aiResponse });

  } catch (error) {
    console.error('AI Service Rank Failure:', error.message);

    // Graceful Degradation Fallback:
    // Return basic heuristic sort based on average skill score so UI remains functional
    return res.status(200).json({
      success: true,
      degraded: true,
      warning: 'AI ranking service temporarily unavailable. Displaying basic heuristic fallback.',
      data: {
        role_id: req.params.roleId,
        rankings: fallbackBasicSort(candidates, roleDoc)
      }
    });
  }
});
```

---

## 5. Security & Privacy Safeguards

1. **No Demographic PII**: Do **not** send student names, phone numbers, email addresses, race, gender, or age in payloads to the AI service. Only send synthetic candidate identifiers (e.g. `c._id.toString()`) and skill evidence attributes.
2. **Network Isolation**: In staging and production, bind the Python service to internal VPC addresses (`http://10.x.x.x:8000` or Docker network alias `http://ai-service:8000`), never exposing port 8000 directly to the public internet. Express acts as the single authenticated gateway.
