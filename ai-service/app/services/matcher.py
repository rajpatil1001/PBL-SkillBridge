"""Role Matching and Multi-Candidate Ranking Service.

Mathematical Model:
1. Requirement Weights:
   - CRITICAL: 1.5x
   - IMPORTANT: 1.0x
   - NICE_TO_HAVE: 0.5x
   (or explicit numerical weight override)

2. Skill Fulfillment Ratio:
   ratio_i = min(1.20, candidate_score_i / required_score_i) if skill present else 0.0
   confidence_adjusted_ratio_i = ratio_i * (0.60 + 0.40 * candidate_confidence_i)

3. Composite Role Match Score:
   raw_match = (sum(weight_i * confidence_adjusted_ratio_i) / sum(weight_i)) * 100.0
   critical_penalty: if any CRITICAL skill is completely MISSING or below 50% target,
                     score is tempered by 15% to safeguard production quality.

4. Multi-Candidate Ranking:
   Deterministic ordering by match_score desc, candidate_confidence desc.
   No demographic, personal, or non-technical factors permitted.
"""

from typing import Dict, List, Optional, Tuple

from app.models.match import (
    CandidateProfile,
    MatchResult,
    RankMatchesRequest,
    RankMatchesResponse,
    RoleRequirement,
    SkillImportance,
    SkillMatchEvaluation,
    SkillMatchStatus,
)
from app.services.extractor import extractor_service
from app.utils.logging import logger

IMPORTANCE_WEIGHTS: Dict[SkillImportance, float] = {
    SkillImportance.CRITICAL: 1.5,
    SkillImportance.IMPORTANT: 1.0,
    SkillImportance.NICE_TO_HAVE: 0.5,
}


class RoleMatcher:
    """Matches candidate skill portfolios against job/role specifications and ranks them."""

    def evaluate_candidate(
        self,
        candidate: CandidateProfile,
        role: RoleRequirement
    ) -> MatchResult:
        # Build lookup for candidate's evidenced skills
        candidate_skills = {
            s.skill_id.strip().lower(): s
            for s in candidate.skills
        }

        matched_evals: List[SkillMatchEvaluation] = []
        weak_evals: List[SkillMatchEvaluation] = []
        missing_evals: List[SkillMatchEvaluation] = []

        total_weighted_points = 0.0
        total_max_points = 0.0
        critical_deficits = 0

        for req in role.required_skills:
            req_id = req.skill_id.strip().lower()
            weight = req.weight if req.weight is not None else IMPORTANCE_WEIGHTS.get(req.importance, 1.0)
            total_max_points += (weight * 100.0)

            tax_entry = extractor_service.taxonomy.get(req_id)
            canonical_name = tax_entry["canonical_name"] if tax_entry else req_id.title()

            cand_ev = candidate_skills.get(req_id)

            if cand_ev is None:
                # Skill is missing
                status = SkillMatchStatus.MISSING
                cand_score = 0.0
                cand_conf = 0.0
                impact = 0.0
                note = f"Missing required skill: no verified evidence found for {canonical_name}."
                if req.importance == SkillImportance.CRITICAL:
                    critical_deficits += 1

                evaluation = SkillMatchEvaluation(
                    skill_id=req_id,
                    canonical_name=canonical_name,
                    status=status,
                    importance=req.importance,
                    required_score=req.minimum_score,
                    candidate_score=cand_score,
                    candidate_confidence=cand_conf,
                    impact_score=round(impact, 2),
                    note=note,
                )
                missing_evals.append(evaluation)

            else:
                cand_score = cand_ev.score
                cand_conf = cand_ev.confidence
                ratio = min(1.20, cand_score / max(1.0, req.minimum_score))
                conf_factor = 0.60 + (0.40 * cand_conf)
                effective_score = min(100.0, (cand_score * conf_factor))
                impact = effective_score * weight

                total_weighted_points += impact

                if cand_score >= req.minimum_score:
                    status = SkillMatchStatus.MATCHED
                    diff = cand_score - req.minimum_score
                    note = (
                        f"Target met: {cand_score:.1f} vs {req.minimum_score:.1f} required "
                        f"(+{diff:.1f} margin, {cand_conf * 100:.0f}% confidence)."
                    )
                    evaluation = SkillMatchEvaluation(
                        skill_id=req_id,
                        canonical_name=canonical_name,
                        status=status,
                        importance=req.importance,
                        required_score=req.minimum_score,
                        candidate_score=cand_score,
                        candidate_confidence=cand_conf,
                        impact_score=round(impact, 2),
                        note=note,
                    )
                    matched_evals.append(evaluation)
                else:
                    status = SkillMatchStatus.WEAK
                    diff = req.minimum_score - cand_score
                    if req.importance == SkillImportance.CRITICAL and (cand_score < req.minimum_score * 0.5):
                        critical_deficits += 1

                    note = (
                        f"Deficit: {cand_score:.1f} vs {req.minimum_score:.1f} target "
                        f"(-{diff:.1f} gap)."
                    )
                    evaluation = SkillMatchEvaluation(
                        skill_id=req_id,
                        canonical_name=canonical_name,
                        status=status,
                        importance=req.importance,
                        required_score=req.minimum_score,
                        candidate_score=cand_score,
                        candidate_confidence=cand_conf,
                        impact_score=round(impact, 2),
                        note=note,
                    )
                    weak_evals.append(evaluation)

        # Base match score computation
        raw_score = (total_weighted_points / total_max_points * 100.0) if total_max_points > 0 else 0.0

        # Critical skill deficit tempering
        if critical_deficits > 0:
            penalty_multiplier = max(0.60, 1.0 - (0.15 * critical_deficits))
            final_score = round(raw_score * penalty_multiplier, 2)
            penalty_note = f" (Tempered by {int((1.0 - penalty_multiplier) * 100)}% due to {critical_deficits} critical skill deficit(s))"
        else:
            final_score = round(raw_score, 2)
            penalty_note = ""

        # Categorize fit level
        if final_score >= 85.0:
            fit_level = "Strong Fit"
        elif final_score >= 70.0:
            fit_level = "Moderate Fit"
        elif final_score >= 50.0:
            fit_level = "Potential with Gaps"
        else:
            fit_level = "Low Fit"

        # Candidate strengths
        strengths = [
            f"{m.canonical_name} ({m.candidate_score:.1f}/100)"
            for m in sorted(matched_evals, key=lambda x: -x.candidate_score)
        ]

        # Rationale reasons
        reasons: List[str] = []
        if matched_evals:
            reasons.append(f"Satisfies {len(matched_evals)} of {len(role.required_skills)} required competencies.")
        if weak_evals:
            weak_names = ", ".join(w.canonical_name for w in weak_evals)
            reasons.append(f"Identified growth gaps in: {weak_names}.")
        if missing_evals:
            missing_names = ", ".join(m.canonical_name for m in missing_evals)
            reasons.append(f"Lacks verified evidence for: {missing_names}.")

        explainability = (
            f"Candidate achieved match score {final_score:.1f}/100 ({fit_level}) for role '{role.role_title}'{penalty_note}. "
            f"Evaluated against {len(role.required_skills)} requirements. "
            f"Matched: {len(matched_evals)}, Weak: {len(weak_evals)}, Missing: {len(missing_evals)}."
        )

        return MatchResult(
            candidate_id=candidate.candidate_id,
            match_score=final_score,
            fit_level=fit_level,
            matched_skills=matched_evals,
            weak_skills=weak_evals,
            missing_skills=missing_evals,
            strengths=strengths,
            reasons=reasons,
            explainability=explainability,
        )

    def rank(self, request: RankMatchesRequest) -> RankMatchesResponse:
        results: List[MatchResult] = []

        for candidate in request.candidates:
            res = self.evaluate_candidate(candidate, request.role)
            results.append(res)

        # Deterministic ranking sort: descending match_score, then candidate_id tie-break
        results.sort(key=lambda x: (-x.match_score, x.candidate_id))

        # Assign ordinal rank
        for idx, item in enumerate(results, start=1):
            item.rank = idx

        total_evaluated = len(results)
        if request.top_k and request.top_k < total_evaluated:
            results = results[: request.top_k]

        summary_note = (
            f"Ranked {total_evaluated} candidate(s) for role '{request.role.role_title}' (ID: {request.role.role_id}). "
            f"Top match scored {results[0].match_score:.1f}/100 ({results[0].fit_level})."
            if results
            else "No candidates to evaluate."
        )

        return RankMatchesResponse(
            role_id=request.role.role_id,
            role_title=request.role.role_title,
            total_candidates_evaluated=total_evaluated,
            rankings=results,
            explainability_notes=summary_note,
        )


matcher_service = RoleMatcher()
