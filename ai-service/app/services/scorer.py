"""Evidence-Aware Skill Scoring and Confidence Estimation Service.

Mathematical Model:
1. Per-Evidence Weighted Contribution:
   w_i = (custom_weight or source_weight) * verification_multiplier * recency_factor
   where recency_factor = max(recency_floor, 2 ** (-days_ago / half_life_days))
   contributed_score_i = raw_score_i * w_i

2. Skill Composite Score:
   composite_score = sum(contributed_score_i) / sum(w_i)  [if sum(w_i) > 0 else 0]

3. Corroboration Bonus:
   bonus = min(max_bonus, (num_distinct_sources - 1) * bonus_per_source)

4. Skill Confidence Estimate:
   confidence = min(1.0, (mean_source_reliability * mean_verification * mean_recency) + bonus)

5. Transparency & Non-Discrimination:
   Demographic or protected attributes are strictly forbidden and not used.
"""

import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.models.common import EvidenceSourceType, SkillCategory, VerificationStatus
from app.models.score import (
    EvidenceFactorBreakdown,
    EvidenceItem,
    ScoreSkillsRequest,
    ScoreSkillsResponse,
    ScoringWeightConfig,
    SkillScoreResult,
)
from app.services.extractor import extractor_service
from app.utils.logging import logger


class SkillScorer:
    """Computes evidence-weighted proficiency scores and confidence metrics."""

    def __init__(self):
        self.default_weights = ScoringWeightConfig()

    def _calculate_days_ago(self, item: EvidenceItem) -> int:
        if item.days_ago is not None and item.days_ago >= 0:
            return item.days_ago
        if item.date_recorded:
            try:
                rec_date = datetime.strptime(item.date_recorded, "%Y-%m-%d").date()
                delta = (datetime.now(timezone.utc).date() - rec_date).days
                return max(0, delta)
            except ValueError:
                pass
        return 0

    def _compute_recency_factor(self, days_ago: int, half_life_days: int, floor: float) -> float:
        if days_ago <= 0:
            return 1.0
        # Exponential half-life decay: 2^(-t / T)
        decay = math.pow(2.0, -days_ago / float(half_life_days))
        return round(max(floor, decay), 4)

    def score(self, request: ScoreSkillsRequest) -> ScoreSkillsResponse:
        cfg = request.weight_config or self.default_weights
        grouped_evidence: Dict[str, List[EvidenceItem]] = {}

        for ev in request.evidence:
            skill_id = ev.skill_id.strip().lower()
            if skill_id not in grouped_evidence:
                grouped_evidence[skill_id] = []
            grouped_evidence[skill_id].append(ev)

        scored_skills: List[SkillScoreResult] = []

        for skill_id, ev_list in grouped_evidence.items():
            factors: List[EvidenceFactorBreakdown] = []
            distinct_sources = set()

            total_weighted_score = 0.0
            total_weight = 0.0

            source_reliabilities: List[float] = []
            verification_factors: List[float] = []
            recency_factors: List[float] = []

            for ev in ev_list:
                is_rejected = (ev.verification_status == VerificationStatus.REJECTED)
                src_val = ev.source_type.value
                ver_val = ev.verification_status.value

                source_weight = ev.custom_weight if ev.custom_weight is not None else cfg.source_weights.get(src_val, 0.5)
                ver_mult = cfg.verification_multipliers.get(ver_val, 0.85)

                days_ago = self._calculate_days_ago(ev)
                rec_factor = self._compute_recency_factor(days_ago, cfg.recency_half_life_days, cfg.recency_floor)

                if is_rejected:
                    w = 0.0
                    contribution = 0.0
                else:
                    w = source_weight * ver_mult * rec_factor
                    contribution = ev.raw_score * w
                    distinct_sources.add(src_val)
                    source_reliabilities.append(source_weight)
                    verification_factors.append(ver_mult)
                    recency_factors.append(rec_factor)

                total_weighted_score += contribution
                total_weight += w

                factors.append(
                    EvidenceFactorBreakdown(
                        source_type=src_val,
                        raw_score=round(ev.raw_score, 2),
                        source_weight=round(source_weight, 2),
                        verification_multiplier=round(ver_mult, 2),
                        recency_factor=round(rec_factor, 2),
                        weighted_contribution=round(contribution, 2),
                        is_rejected=is_rejected,
                    )
                )

            # Composite score calculation
            if total_weight > 0:
                composite_score = round(total_weighted_score / total_weight, 2)
            else:
                composite_score = 0.0

            # Corroboration bonus calculation
            num_sources = len(distinct_sources)
            if num_sources > 1:
                corroboration_bonus = min(
                    cfg.max_corroboration_bonus,
                    (num_sources - 1) * cfg.corroboration_bonus_per_source
                )
            else:
                corroboration_bonus = 0.0

            # Confidence calculation
            if source_reliabilities:
                avg_src = sum(source_reliabilities) / len(source_reliabilities)
                avg_ver = sum(verification_factors) / len(verification_factors)
                avg_rec = sum(recency_factors) / len(recency_factors)
                base_confidence = (avg_src * 0.40) + (avg_ver * 0.35) + (avg_rec * 0.25)
                final_confidence = min(1.0, max(0.1, base_confidence + corroboration_bonus))
            else:
                final_confidence = 0.0

            # Get canonical taxonomy metadata if known
            tax_entry = extractor_service.taxonomy.get(skill_id)
            canonical_name = tax_entry["canonical_name"] if tax_entry else skill_id.title()
            category = tax_entry["category"] if tax_entry else SkillCategory.OTHER

            # Construct human-readable explanation
            if composite_score >= 80:
                qualifier = "high proficiency"
            elif composite_score >= 60:
                qualifier = "solid working competence"
            else:
                qualifier = "foundational or developing skill"

            src_summary = ", ".join(distinct_sources) if distinct_sources else "none"
            explanation = (
                f"{canonical_name} scored at {composite_score:.1f}/100 ({qualifier}) backed by "
                f"{len(ev_list)} evidence item(s) across source(s): [{src_summary}]. "
                f"Confidence level is {final_confidence * 100:.1f}%, including a "
                f"+{corroboration_bonus * 100:.1f}% independent corroboration boost."
            )

            scored_skills.append(
                SkillScoreResult(
                    skill_id=skill_id,
                    canonical_name=canonical_name,
                    category=category,
                    composite_score=composite_score,
                    confidence=round(final_confidence, 2),
                    evidence_count=len(ev_list),
                    distinct_sources=sorted(list(distinct_sources)),
                    corroboration_bonus_applied=round(corroboration_bonus, 2),
                    factors=factors,
                    explanation=explanation,
                )
            )

        scored_skills.sort(key=lambda x: (-x.composite_score, -x.confidence))
        overall_index = (
            round(sum(s.composite_score for s in scored_skills) / len(scored_skills), 2)
            if scored_skills
            else 0.0
        )

        explainability_summary = (
            f"Evaluated {len(request.evidence)} evidence records across {len(scored_skills)} distinct skills. "
            f"Aggregate skill index: {overall_index:.1f}/100. Evidence weighting applied source credibility, "
            f"verification audits, exponential recency decay (half-life: {cfg.recency_half_life_days}d), "
            f"and multi-source corroboration adjustments."
        )

        return ScoreSkillsResponse(
            candidate_id=request.candidate_id,
            overall_skill_index=overall_index,
            skills=scored_skills,
            explainability_summary=explainability_summary,
            scoring_version="evidence_weighted_v1.0",
        )


scorer_service = SkillScorer()
