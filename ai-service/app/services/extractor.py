"""Skill Extraction Pipeline.

Methodology:
- Curated canonical taxonomy with multi-alias dictionary matching.
- Token boundary and punctuation-aware regular expressions.
- Section header detection (e.g., 'SKILLS', 'EXPERIENCE', 'PROJECTS') for contextual confidence boosting.
- Disambiguation rules for short tokens (e.g. 'go', 'c', 'r') to prevent false positives.
- Deduplication by canonical skill ID with span recording and snippet extraction.

Technical Limitation Disclosure:
- This is a high-precision, interpretable taxonomy and rule-based baseline extractor.
- It does not use generative hallucinations or an unverified black-box model.
- Only skills mapped within the canonical taxonomy can be extracted.
- Pluggable interface allows future expansion to fine-tuned transformer NER pipelines without altering the API contract.
"""

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.models.common import SkillCategory
from app.models.extract import (
    ExtractSkillsRequest,
    ExtractSkillsResponse,
    ExtractedSkillItem,
    ExtractionMetadata,
)
from app.utils.logging import logger

# Section boundary detection regexes
SECTION_PATTERNS = [
    (re.compile(r"(?:^|\n)\s*(?:technical\s+)?skills?\s*(?::|\n)", re.IGNORECASE), "SKILLS"),
    (re.compile(r"(?:^|\n)\s*(?:work\s+)?experience\s*(?::|\n)", re.IGNORECASE), "EXPERIENCE"),
    (re.compile(r"(?:^|\n)\s*projects?\s*(?::|\n)", re.IGNORECASE), "PROJECTS"),
    (re.compile(r"(?:^|\n)\s*education\s*(?::|\n)", re.IGNORECASE), "EDUCATION"),
    (re.compile(r"(?:^|\n)\s*certifications?\s*(?::|\n)", re.IGNORECASE), "CERTIFICATIONS"),
]

# Sensitive ambiguous tokens that require strict contextual validation
AMBIGUOUS_SHORT_TOKENS: Dict[str, re.Pattern] = {
    "go": re.compile(r"\b(?:golang|go\s+programming|go\s+developer|go\s+language|backend\s+go)\b", re.IGNORECASE),
    "c": re.compile(r"\b(?:c\s+programming|c\s+language|ansi\s+c|c\/c\+\+)\b", re.IGNORECASE),
    "r": re.compile(r"\b(?:r\s+programming|r\s+language|r\s+statistical|r\s+studio)\b", re.IGNORECASE),
    "net": re.compile(r"\b(?:\.net|dotnet|asp\.net)\b", re.IGNORECASE),
}


class SkillExtractor:
    """Extracts verified technical and domain skills from raw text using taxonomy rules."""

    def __init__(self, taxonomy_path: Optional[str] = None):
        self.taxonomy_path = taxonomy_path or settings.TAXONOMY_PATH
        self.taxonomy: Dict[str, Dict[str, Any]] = {}
        self.alias_to_id: Dict[str, str] = {}
        self._load_taxonomy()

    def _load_taxonomy(self) -> None:
        path = Path(self.taxonomy_path)
        if not path.exists():
            logger.warning(f"Taxonomy file not found at {path}. Initializing empty.")
            return

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        for item in data.get("skills", []):
            skill_id = item["id"]
            self.taxonomy[skill_id] = {
                "id": skill_id,
                "canonical_name": item["canonical_name"],
                "category": SkillCategory(item.get("category", "other")),
                "description": item.get("description", ""),
                "aliases": item.get("aliases", []),
                "related_skills": item.get("related_skills", []),
            }
            # Map canonical name and aliases (case-normalized)
            self.alias_to_id[item["canonical_name"].lower()] = skill_id
            for alias in item.get("aliases", []):
                self.alias_to_id[alias.lower()] = skill_id

        logger.info(f"Loaded taxonomy with {len(self.taxonomy)} skills and {len(self.alias_to_id)} alias mappings.")

    def _detect_sections(self, text: str) -> List[Tuple[int, str]]:
        """Finds character offsets for standard document sections."""
        sections: List[Tuple[int, str]] = []
        for pattern, section_name in SECTION_PATTERNS:
            for match in pattern.finditer(text):
                sections.append((match.start(), section_name))
        sections.sort(key=lambda x: x[0])
        return sections

    def _get_section_for_offset(self, offset: int, sections: List[Tuple[int, str]]) -> Optional[str]:
        current_section = None
        for sec_offset, sec_name in sections:
            if offset >= sec_offset:
                current_section = sec_name
            else:
                break
        return current_section

    def _extract_context_snippet(self, text: str, start: int, end: int, window: int = 50) -> str:
        s = max(0, start - window)
        e = min(len(text), end + window)
        prefix = "..." if s > 0 else ""
        suffix = "..." if e < len(text) else ""
        snippet = text[s:e].replace("\n", " ").strip()
        return f"{prefix}{snippet}{suffix}"

    def extract(self, request: ExtractSkillsRequest) -> ExtractSkillsResponse:
        start_time = time.perf_counter()
        text = request.text
        doc_type = request.document_type
        sections = self._detect_sections(text)

        # Dictionary to store highest-confidence detection per canonical skill_id
        detected: Dict[str, ExtractedSkillItem] = {}

        # Scan each alias in taxonomy
        for alias, skill_id in self.alias_to_id.items():
            skill_meta = self.taxonomy[skill_id]

            # Check if this alias has strict contextual pattern
            if alias in AMBIGUOUS_SHORT_TOKENS:
                pattern = AMBIGUOUS_SHORT_TOKENS[alias]
            else:
                # If alias is alphanumeric or multi-word, \b word boundaries match cleanly and respect punctuation like '.' or ','
                if re.match(r"^[a-zA-Z0-9_\s]+$", alias):
                    pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
                else:
                    # Aliases containing punctuation like c++, c#, .net, next.js
                    prefix_bound = r"(?:(?<=\s)|(?<=^)|(?<=[(\[{,;:/]))"
                    suffix_bound = r"(?=(?:[\s)\]},;:.!?]|$))"
                    pattern = re.compile(prefix_bound + re.escape(alias) + suffix_bound, re.IGNORECASE)

            for match in pattern.finditer(text):
                start_char, end_char = match.span()
                matched_text = match.group(0)
                section = self._get_section_for_offset(start_char, sections)

                # Confidence calculation heuristic
                base_confidence = 0.75
                if section == "SKILLS":
                    base_confidence = 0.95
                elif section in ("PROJECTS", "EXPERIENCE"):
                    base_confidence = 0.90
                elif section == "CERTIFICATIONS":
                    base_confidence = 0.92

                # Slight penalty if matching non-canonical alias
                if matched_text.lower() != skill_meta["canonical_name"].lower():
                    base_confidence *= 0.95

                # Boost for exact casing match on title/acronyms
                if matched_text == skill_meta["canonical_name"]:
                    base_confidence = min(1.0, base_confidence + 0.05)

                confidence = round(min(1.0, max(0.1, base_confidence)), 2)

                if confidence < request.confidence_threshold:
                    continue

                snippet = None
                if request.include_context:
                    snippet = self._extract_context_snippet(text, start_char, end_char)

                item = ExtractedSkillItem(
                    skill_id=skill_id,
                    canonical_name=skill_meta["canonical_name"],
                    category=skill_meta["category"],
                    confidence=confidence,
                    matched_text=matched_text,
                    start_char=start_char,
                    end_char=end_char,
                    context_snippet=snippet,
                    section_header=section,
                )

                # Keep occurrence with highest confidence or earliest appearance
                if skill_id not in detected or item.confidence > detected[skill_id].confidence:
                    detected[skill_id] = item

        elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        extracted_skills = sorted(detected.values(), key=lambda x: (-x.confidence, x.canonical_name))

        metadata = ExtractionMetadata(
            pipeline="rule_taxonomy_baseline_v1",
            version="1.0.0",
            execution_time_ms=elapsed_ms,
            methodology="Contextual boundary-aware taxonomy matching with section detection and disambiguation.",
            limitations="Statistical rule baseline over curated taxonomy. Does not use deep neural text parsing. Pluggable for transformer models."
        )

        return ExtractSkillsResponse(
            skills=extracted_skills,
            total_detected=len(extracted_skills),
            document_type=doc_type,
            metadata=metadata,
        )


extractor_service = SkillExtractor()
