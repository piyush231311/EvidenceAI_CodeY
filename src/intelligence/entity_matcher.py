"""Cross-evidence Entity Matching & Disambiguation module using RapidFuzz."""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from src.intelligence.gliner_extractor import ExtractedEntity


class EntityMention(BaseModel):
    """An exact occurrence of an entity in a specific evidence file."""
    text: str
    evidence_id: str
    filename: str
    confidence: float
    start_char: int
    end_char: int


class CandidateMatch(BaseModel):
    """A cross-evidence candidate entity match proposed for human review."""
    match_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    entity_type: str                     # person | organization | location | identifier | date | time
    canonical_name: str                  # Proposed canonical name
    similarity_score: float              # 0.0 to 100.0 from RapidFuzz
    status: str = "pending"              # pending | confirmed | rejected | separate
    mentions: List[EntityMention] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


def normalize_entity_text(text: str) -> str:
    """Normalizes entity text for fuzzy matching."""
    s = text.lower().strip()
    # Strip common titles / prefixes
    s = re.sub(r"^(?:mr\.|mrs\.|ms\.|dr\.|prof\.|officer|agent|sgt\.)\s+", "", s)
    # Strip excess punctuation and whitespace
    s = re.sub(r"[^\w\s@.-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def generate_candidate_matches(
    entities: List[ExtractedEntity],
    case_id: str,
    threshold: float = 75.0,
) -> List[CandidateMatch]:
    """
    Compares entities across evidence files and groups high-similarity mentions
    into candidate matches for human review. Never merges automatically.
    """
    if not entities:
        return []

    # Group entities by type
    by_type: Dict[str, List[ExtractedEntity]] = {}
    for ent in entities:
        if not ent.text or len(ent.text.strip()) < 2:
            continue
        by_type.setdefault(ent.label, []).append(ent)

    candidate_matches: List[CandidateMatch] = []

    for entity_type, type_entities in by_type.items():
        # Cluster entities into candidate groups
        clusters: List[List[ExtractedEntity]] = []

        for ent in type_entities:
            norm_ent = normalize_entity_text(ent.text)
            matched_cluster = None
            best_score = 0.0

            for cluster in clusters:
                # Compare against all members in cluster
                cluster_scores = []
                for member in cluster:
                    norm_member = normalize_entity_text(member.text)

                    if entity_type == "identifier":
                        # Identifiers (emails, phones) require exact normalized match
                        score = 100.0 if norm_ent == norm_member else 0.0
                    else:
                        # Names, orgs, locations use token_sort_ratio
                        score = fuzz.token_sort_ratio(norm_ent, norm_member)

                    cluster_scores.append(score)

                avg_score = sum(cluster_scores) / len(cluster_scores) if cluster_scores else 0.0
                if avg_score >= threshold and avg_score > best_score:
                    best_score = avg_score
                    matched_cluster = cluster

            if matched_cluster is not None:
                matched_cluster.append(ent)
            else:
                clusters.append([ent])

        # Convert clusters to CandidateMatches
        for cluster in clusters:
            if not cluster:
                continue

            # Check if cluster spans multiple distinct evidence files or mentions
            distinct_evidence = {e.evidence_id for e in cluster if e.evidence_id}
            
            # Select canonical name: most frequent or longest mention
            name_counts: Dict[str, int] = {}
            for e in cluster:
                name_counts[e.text] = name_counts.get(e.text, 0) + 1
            canonical_name = max(name_counts.keys(), key=lambda k: (name_counts[k], len(k)))

            mentions = [
                EntityMention(
                    text=e.text,
                    evidence_id=e.evidence_id or "unknown",
                    filename=e.filename or "unknown",
                    confidence=e.confidence,
                    start_char=e.start_char,
                    end_char=e.end_char,
                )
                for e in cluster
            ]

            # Compute internal similarity score
            if len(cluster) == 1:
                sim_score = 100.0
            else:
                sim_score = min(
                    100.0,
                    round(
                        sum(
                            fuzz.token_sort_ratio(
                                normalize_entity_text(cluster[0].text),
                                normalize_entity_text(other.text)
                            )
                            for other in cluster[1:]
                        ) / (len(cluster) - 1),
                        1,
                    )
                )

            candidate_matches.append(
                CandidateMatch(
                    case_id=case_id,
                    entity_type=entity_type,
                    canonical_name=canonical_name,
                    similarity_score=sim_score,
                    status="pending",
                    mentions=mentions,
                )
            )

    # Sort candidates by similarity score and mention count
    candidate_matches.sort(key=lambda c: (len(c.mentions) > 1, c.similarity_score), reverse=True)
    return candidate_matches
