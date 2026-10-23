"""Skill Gap Analysis and Learning Path Recommendation Service.

Methodology:
1. Target Deficit Computation:
   gap_delta = max(0.0, target_score - current_score)

2. Urgency Stratification:
   - CRITICAL: Complete missing skill with HIGH or CRITICAL requirement.
   - HIGH: Large deficit (> 30 points) on a required skill.
   - MEDIUM: Moderate deficit (10-30 points).
   - LOW: Minor refinement needed (< 10 points).

3. Learning Resource Recommendation:
   - Configurable catalogue mapping canonical skill IDs to educational assets.
   - Seeded resources are explicitly flagged with `is_sample: True` to transparently
     distinguish baseline fixtures from live LMS/enterprise integrations.
   - Difficulty level matches the learner's current proficiency tier.

4. Action Plan Synthesis:
   - Generates sequenced steps prioritized by urgency and estimated hours.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models.gap import (
    AnalyzeGapsRequest,
    AnalyzeGapsResponse,
    CurrentSkillStatus,
    GapUrgency,
    LearningResource,
    ResourceType,
    SkillGapItem,
    TargetSkillDemand,
)
from app.services.extractor import extractor_service
from app.utils.logging import logger


class SkillGapRecommender:
    """Analyzes student skill gaps and recommends tailored learning resources."""

    def __init__(self, resources_path: Optional[str] = None):
        self.resources_path = resources_path or settings.RESOURCES_PATH
        self.catalogue: Dict[str, List[LearningResource]] = {}
        self._load_catalogue()

    def _load_catalogue(self) -> None:
        path = Path(self.resources_path)
        if not path.exists():
            logger.warning(f"Resources catalogue not found at {path}. Initializing empty.")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in data.get("resources", []):
            skill_id = item["skill_id"].strip().lower()
            res = LearningResource(
                resource_id=item["resource_id"],
                title=item["title"],
                provider=item.get("provider", "SkillBridge Curated Baseline"),
                resource_type=ResourceType(item.get("resource_type", "course")),
                difficulty=item.get("difficulty", "intermediate"),
                estimated_hours=float(item.get("estimated_hours", 10.0)),
                url=item.get("url"),
                is_sample=item.get("is_sample", True),  # Enforce sample transparency
                description=item.get("description"),
            )
            if skill_id not in self.catalogue:
                self.catalogue[skill_id] = []
            self.catalogue[skill_id].append(res)
            count += 1

        logger.info(f"Loaded {count} learning resources for {len(self.catalogue)} skills from catalogue.")

    def _determine_urgency(self, current: float, target: float, priority: GapUrgency) -> GapUrgency:
        delta = target - current
        if current <= 0 and priority in (GapUrgency.CRITICAL, GapUrgency.HIGH):
            return GapUrgency.CRITICAL
        elif delta >= 35.0 or priority == GapUrgency.CRITICAL:
            return GapUrgency.HIGH
        elif delta >= 15.0:
            return GapUrgency.MEDIUM
        return GapUrgency.LOW

    def _determine_recommended_action(self, current: float, target: float, canonical_name: str) -> str:
        delta = target - current
        if current <= 0:
            return f"Foundational start: Begin introductory fundamentals and build a guided practice project in {canonical_name}."
        elif delta >= 35.0:
            return f"Substantial gap: Complete comprehensive hands-on labs and intermediate capstone assignments in {canonical_name}."
        elif delta >= 15.0:
            return f"Refinement: Strengthen edge-case handling, system design, and advanced patterns in {canonical_name}."
        else:
            return f"Minor polishing: Complete targeted problem sets or review reference documentation in {canonical_name}."

    def _filter_resources_for_skill(
        self,
        skill_id: str,
        current_score: float,
        limit: int = 3
    ) -> List[LearningResource]:
        available = self.catalogue.get(skill_id, [])
        if not available:
            # Fallback sample resource when not present in catalogue
            tax_entry = extractor_service.taxonomy.get(skill_id)
            name = tax_entry["canonical_name"] if tax_entry else skill_id.title()
            return [
                LearningResource(
                    resource_id=f"sample_{skill_id}_ref",
                    title=f"{name} Core Documentation & Practical Exercises",
                    provider="SkillBridge Curated Baseline",
                    resource_type=ResourceType.DOCUMENTATION,
                    difficulty="beginner" if current_score < 40 else "intermediate",
                    estimated_hours=12.0,
                    url=f"https://devdocs.io/{skill_id}",
                    is_sample=True,
                    description=f"Sample resource placeholder for {name} curriculum."
                )
            ]

        # Prioritize resources by appropriate difficulty
        target_diff = "beginner" if current_score < 40.0 else ("intermediate" if current_score < 75.0 else "advanced")
        sorted_res = sorted(
            available,
            key=lambda r: (0 if r.difficulty == target_diff else 1, r.estimated_hours)
        )
        return sorted_res[:limit]

    def analyze(self, request: AnalyzeGapsRequest) -> AnalyzeGapsResponse:
        current_lookup = {
            s.skill_id.strip().lower(): s
            for s in request.current_skills
        }

        gaps: List[SkillGapItem] = []
        total_estimated_hours = 0.0
        critical_count = 0

        readiness_weighted_sum = 0.0
        readiness_total_weight = 0.0

        for target in request.target_skills:
            skill_id = target.skill_id.strip().lower()
            tax_entry = extractor_service.taxonomy.get(skill_id)
            canonical_name = tax_entry["canonical_name"] if tax_entry else skill_id.title()

            curr = current_lookup.get(skill_id)
            current_score = curr.current_score if curr else 0.0

            # Weight by target priority
            weight = 1.5 if target.priority == GapUrgency.CRITICAL else (1.0 if target.priority == GapUrgency.HIGH else 0.7)
            readiness_total_weight += weight
            readiness_weighted_sum += min(1.0, current_score / max(1.0, target.target_score)) * weight

            if current_score < target.target_score:
                gap_delta = round(target.target_score - current_score, 1)
                urgency = self._determine_urgency(current_score, target.target_score, target.priority)
                if urgency == GapUrgency.CRITICAL:
                    critical_count += 1

                action = self._determine_recommended_action(current_score, target.target_score, canonical_name)
                resources = self._filter_resources_for_skill(
                    skill_id=skill_id,
                    current_score=current_score,
                    limit=request.max_recommendations_per_skill
                )

                hours_for_skill = sum(r.estimated_hours for r in resources)
                total_estimated_hours += hours_for_skill

                gaps.append(
                    SkillGapItem(
                        skill_id=skill_id,
                        canonical_name=canonical_name,
                        current_score=round(current_score, 1),
                        target_score=round(target.target_score, 1),
                        gap_delta=gap_delta,
                        urgency=urgency,
                        recommended_action=action,
                        recommended_resources=resources,
                    )
                )

        # Sort gaps by urgency (CRITICAL -> HIGH -> MEDIUM -> LOW) then descending gap_delta
        urgency_order = {
            GapUrgency.CRITICAL: 0,
            GapUrgency.HIGH: 1,
            GapUrgency.MEDIUM: 2,
            GapUrgency.LOW: 3,
        }
        gaps.sort(key=lambda g: (urgency_order.get(g.urgency, 4), -g.gap_delta))

        # Overall readiness score (0 - 100%)
        readiness_pct = (
            round((readiness_weighted_sum / readiness_total_weight) * 100.0, 1)
            if readiness_total_weight > 0
            else 100.0
        )

        # Synthesize priority action plan
        action_plan: List[str] = []
        for idx, gap in enumerate(gaps[:4], start=1):
            top_res = gap.recommended_resources[0].title if gap.recommended_resources else "curated labs"
            action_plan.append(
                f"Step {idx} [{gap.urgency.value.upper()}]: Close {gap.canonical_name} gap (-{gap.gap_delta} pts) by engaging with '{top_res}'."
            )

        if not action_plan:
            action_plan.append("All targeted skill benchmarks are currently fulfilled! Consider advancing to expert-tier certifications.")

        explainability = (
            f"Evaluated {len(request.target_skills)} target competencies against student evidence. "
            f"Current profile fulfills {readiness_pct}% of the role benchmark. Identified {len(gaps)} actionable gap(s) "
            f"({critical_count} critical), requiring an estimated {total_estimated_hours:.1f} hours of structured learning."
        )

        return AnalyzeGapsResponse(
            student_id=request.student_id or "anonymous_student",
            target_role_title=request.target_role_title,
            total_gaps_identified=len(gaps),
            critical_gaps_count=critical_count,
            readiness_percentage=readiness_pct,
            gaps=gaps,
            total_estimated_learning_hours=round(total_estimated_hours, 1),
            priority_action_plan=action_plan,
            explainability=explainability,
            sample_resources_disclaimer=(
                "All recommended resources in this response are seeded catalogue sample assets "
                "curated for demonstration and structured learning paths."
            ),
        )


recommender_service = SkillGapRecommender()
