"""Cross-evidence Entity Matching & Disambiguation module using specialized strategies."""

import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
from rapidfuzz import fuzz
import dateutil.parser

from src.intelligence.gliner_extractor import ExtractedEntity


class EntityMention(BaseModel):
    """An exact occurrence of an entity in a specific evidence file."""
    text: str
    evidence_id: str
    filename: str
    confidence: float                       # GLiNER classification confidence
    ocr_confidence: Optional[float] = None  # Source OCR/ASR extraction confidence
    start_char: int
    end_char: int
    source_segment_id: Optional[str] = None
    is_low_confidence: bool = False
    requires_source_verification: bool = False
    quality_flags: List[str] = Field(default_factory=list)


class CandidateMatch(BaseModel):
    """A cross-evidence candidate entity match proposed for human review."""
    match_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    entity_type: str                     # person | organization | location | identifier | date | time
    canonical_name: str                  # Proposed canonical name
    similarity_score: float = 0.0        # RapidFuzz similarity across occurrences (0.0 for single occurrence)
    classification_confidence: float = 1.0 # Average GLiNER classification confidence
    ocr_confidence: Optional[float] = None # Average source OCR confidence
    extraction_confidence: float = 1.0   # Compatibility alias for classification_confidence
    is_single_occurrence: bool = False   # True if entity only appears once
    match_type: str = "single_occurrence"# exact_name | alias_initial_lastname | normalized_date | etc.
    status: str = "pending"              # pending | confirmed | rejected | separate
    is_low_confidence: bool = False      # Questionable / garbled detection
    requires_source_verification: bool = False # Flagged for source-image verification
    verification_reasons: List[str] = Field(default_factory=list)
    related_entities: List[Dict[str, Any]] = Field(default_factory=list) # Candidate organizational relationships
    mentions: List[EntityMention] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


# Corporate suffixes to strip for organization canonicalization
CORP_SUFFIXES = re.compile(
    r"\b(?:inc|incorporated|llc|corp|corporation|ltd|limited|gmbh|ag|pvt\s+ltd|co|company|holdings)\b\.?",
    re.IGNORECASE,
)

# Branch, division, and location keywords: distinct branches/subsidiaries must NOT be merged automatically
BRANCH_LOCATION_MODIFIERS = {
    "branch", "office", "division", "subsidiary", "hq", "headquarters",
    "unit", "group", "holdings", "logistics", "aerospace", "financial",
    "services", "capital", "ventures", "asia", "europe", "emea", "americas",
    "geneva", "singapore", "london", "new york", "tokyo", "bengaluru",
    "dubai", "mumbai", "delhi", "frankfurt", "zurich", "berlin", "paris"
}


def normalize_entity_text(text: str) -> str:
    """Normalizes entity text for fuzzy matching."""
    s = text.lower().strip()
    s = re.sub(r"^(?:mr\.|mrs\.|ms\.|dr\.|prof\.|officer|agent|sgt\.)\s+", "", s)
    s = re.sub(r"[^\w\s@.-]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def parse_person_components(name: str) -> Dict[str, Any]:
    """
    Parses a person's name or handle into structural components:
    first name, last name, initials, and token parts.
    Handles 'Vikram Nair', 'Vikram', 'v.nair', 'V. Nair', 'v_nair'.
    """
    s = re.sub(r"^(?:mr\.|mrs\.|ms\.|dr\.|prof\.|officer|agent|sgt\.)\s+", "", name.strip(), flags=re.IGNORECASE)
    if "@" in s:
        s = s.split("@")[0]

    parts = [p.lower() for p in re.split(r"[\s._]+", s) if p]
    if not parts:
        return {"first": "", "last": "", "initial": "", "tokens": []}

    if len(parts) == 1:
        first = parts[0]
        return {
            "first": first,
            "last": "",
            "initial": first[0] if first else "",
            "tokens": parts,
        }

    first = parts[0]
    last = parts[-1]
    return {
        "first": first,
        "last": last,
        "initial": first[0] if first else "",
        "tokens": parts,
    }


def match_persons(name1: str, name2: str) -> Tuple[bool, float, str]:
    """
    Specialized person alias and identity matching.
    Never merges automatically; generates candidate score and rationale.
    """
    norm1 = normalize_entity_text(name1)
    norm2 = normalize_entity_text(name2)

    if norm1 == norm2:
        return True, 100.0, "exact_name"

    p1 = parse_person_components(name1)
    p2 = parse_person_components(name2)

    # 1. First Name Subset (e.g. 'Vikram Nair' and 'Vikram')
    if (not p1["last"] and p2["last"]) or (not p2["last"] and p1["last"]):
        single = p1 if not p1["last"] else p2
        full = p2 if not p1["last"] else p1
        if len(single["first"]) >= 3 and single["first"] == full["first"]:
            return True, 80.0, "alias_firstname_subset"

    # 2. Initial + Last Name (e.g. 'v.nair' or 'V. Nair' and 'Vikram Nair')
    if p1["last"] and p2["last"] and p1["last"] == p2["last"]:
        # Shared last name, check initials / first names
        if p1["first"] == p2["first"]:
            return True, 95.0, "exact_first_last"

        is_p1_initial = len(p1["first"]) == 1
        is_p2_initial = len(p2["first"]) == 1

        if (is_p1_initial or is_p2_initial) and (p1["initial"] == p2["initial"]):
            return True, 85.0, "alias_initial_lastname"

        # Middle name / initial variant: e.g. 'Vikram K. Nair' and 'Vikram Nair'
        if len(p1["tokens"]) != len(p2["tokens"]) and p1["first"] == p2["first"]:
            return True, 90.0, "alias_middle_name_variant"

    # 3. Initial + Last Name vs Single First Name (e.g. 'v.nair' and 'Vikram')
    if (not p1["last"] and p2["last"]) or (not p2["last"] and p1["last"]):
        single = p1 if not p1["last"] else p2
        with_last = p2 if not p1["last"] else p1
        is_initial_handle = len(with_last["first"]) == 1 or with_last["tokens"][0] == with_last["initial"]
        if is_initial_handle and single["initial"] == with_last["initial"]:
            return True, 75.0, "alias_initial_firstname"

    # 4. High fuzzy score for full names with matching initial & last name
    if p1["last"] and p2["last"] and p1["initial"] == p2["initial"]:
        sim = fuzz.token_sort_ratio(norm1, norm2)
        if sim >= 85.0:
            return True, float(sim), "fuzzy_name"

    # If last names are explicitly different, they are not the same person
    if p1["last"] and p2["last"] and p1["last"] != p2["last"]:
        return False, 0.0, "different_person"

    # If first names are different full names, they are not the same person
    if len(p1["first"]) >= 3 and len(p2["first"]) >= 3 and p1["first"] != p2["first"]:
        return False, 0.0, "different_person"

    return False, 0.0, "no_match"


def persons_contradict(name1: str, name2: str) -> bool:
    """
    Returns True if two person names or handles explicitly contradict each other.
    e.g. 'Vikram Nair' vs 'Vikram Sharma' (different last names).
    e.g. 'Vikram Nair' vs 'Rajesh Nair' (different first names).
    e.g. 'Vikram' vs 'Rajesh' (different initials & first names).
    """
    p1 = parse_person_components(name1)
    p2 = parse_person_components(name2)

    # Different last names contradict
    if p1["last"] and p2["last"] and p1["last"] != p2["last"]:
        return True

    # Different full first names contradict
    if len(p1["first"]) >= 3 and len(p2["first"]) >= 3 and p1["first"] != p2["first"]:
        return True

    # Contradicting initials contradict
    if p1["initial"] and p2["initial"] and p1["initial"] != p2["initial"]:
        return True

    return False


def match_dates(d1: str, d2: str) -> Tuple[bool, float, str]:
    """
    Parses and compares dates. NEVER groups different calendar days.
    """
    norm1 = normalize_entity_text(d1)
    norm2 = normalize_entity_text(d2)

    if norm1 == norm2:
        return True, 100.0, "exact_date_string"

    try:
        ref_year = 2026
        dt1 = dateutil.parser.parse(d1, default=datetime(ref_year, 1, 1), fuzzy=True)
        dt2 = dateutil.parser.parse(d2, default=datetime(ref_year, 1, 1), fuzzy=True)

        if (dt1.year, dt1.month, dt1.day) == (dt2.year, dt2.month, dt2.day):
            return True, 100.0, "normalized_date"
        else:
            return False, 0.0, "different_date"
    except Exception:
        # Fallback to exact string equality only
        return (True, 100.0, "exact_date") if norm1 == norm2 else (False, 0.0, "unparseable_date")


def check_time_ambiguity(t_str: str) -> Tuple[bool, bool]:
    """
    Checks if a time expression lacks explicit AM/PM meridiem or timezone offset.
    e.g. '10:14' is ambiguous because it lacks AM/PM specification and timezone.
    Returns: (is_meridiem_ambiguous, is_timezone_ambiguous)
    """
    s = t_str.strip().lower()
    has_meridiem = bool(re.search(r"(?:^|[\d\s])(?:am|pm|a\.m\.|p\.m\.)(?:[\s\.,;:]|$)", s))
    has_tz = bool(re.search(r"(?:utc|gmt|est|pst|cst|ist|cet|\b[zZ]\b|[+-]\d{2}:?\d{2})", s))

    is_meridiem_ambiguous = False
    try:
        parsed_time = dateutil.parser.parse(s).time()
        # If hour is 1-12 without explicit am/pm, it is ambiguous
        if parsed_time.hour <= 12 and not has_meridiem:
            is_meridiem_ambiguous = True
    except Exception:
        if not has_meridiem:
            is_meridiem_ambiguous = True

    is_tz_ambiguous = not has_tz
    return is_meridiem_ambiguous, is_tz_ambiguous


def match_times(t1: str, t2: str) -> Tuple[bool, float, str]:
    """
    Parses and compares times.
    NEVER groups different timestamps (e.g. 10:23 AM vs 10:30 AM).
    Handles ambiguous time expressions like '10:14' without assuming AM/PM or timezone.
    """
    norm1 = normalize_entity_text(t1)
    norm2 = normalize_entity_text(t2)

    amb1, _ = check_time_ambiguity(t1)
    amb2, _ = check_time_ambiguity(t2)

    if norm1 == norm2:
        if amb1:
            return True, 100.0, "exact_time_unspecified_meridiem"
        return True, 100.0, "exact_time_string"

    # If one time expression is ambiguous (e.g. '10:14') and the other has explicit AM/PM (e.g. '10:14 AM' or '10:14 PM'):
    # Do NOT assume AM/PM or timezone! They must remain separate candidate clusters
    if amb1 != amb2:
        return False, 0.0, "ambiguous_time_meridiem"

    try:
        time1 = dateutil.parser.parse(t1).time()
        time2 = dateutil.parser.parse(t2).time()

        if (time1.hour, time1.minute, time1.second) == (time2.hour, time2.minute, time2.second):
            if amb1 and amb2:
                return True, 100.0, "normalized_time_unspecified_meridiem"
            return True, 100.0, "normalized_time"
        else:
            return False, 0.0, "different_time"
    except Exception:
        # Fallback to exact string equality only
        return (True, 100.0, "exact_time") if norm1 == norm2 else (False, 0.0, "unparseable_time")


def match_identifiers(id1: str, id2: str) -> Tuple[bool, float, str]:
    """
    Compares identifiers (emails, phone numbers, alphanumeric IDs) using exact normalized matching.
    """
    norm1 = id1.strip().lower()
    norm2 = id2.strip().lower()

    if norm1 == norm2:
        return True, 100.0, "exact_identifier"

    # Email comparison
    if "@" in norm1 and "@" in norm2:
        clean_email1 = re.sub(r"^mailto:", "", norm1)
        clean_email2 = re.sub(r"^mailto:", "", norm2)
        return (True, 100.0, "exact_email") if clean_email1 == clean_email2 else (False, 0.0, "different_email")

    # Phone number comparison (digits only)
    digits1 = re.sub(r"\D", "", norm1)
    digits2 = re.sub(r"\D", "", norm2)
    if digits1 and digits2 and len(digits1) >= 7 and len(digits2) >= 7:
        # Match if digits match or last 10 digits match
        if digits1 == digits2 or digits1[-10:] == digits2[-10:]:
            return True, 100.0, "exact_phone"
        return False, 0.0, "different_phone"

    # Other identifiers: strip leading '#' or symbols
    clean_id1 = re.sub(r"^[#:\-\s]+", "", norm1)
    clean_id2 = re.sub(r"^[#:\-\s]+", "", norm2)
    if clean_id1 == clean_id2:
        return True, 100.0, "exact_code"

    return False, 0.0, "different_identifier"


def find_organization_relationship(org1: str, org2: str) -> Optional[Dict[str, str]]:
    """
    Detects organizational relationships (e.g. branch vs parent, operational division)
    without merging separate legal entities or locations into one persona.
    """
    norm1 = normalize_entity_text(org1)
    norm2 = normalize_entity_text(org2)
    if norm1 == norm2:
        return None

    base1 = CORP_SUFFIXES.sub("", norm1).strip()
    base2 = CORP_SUFFIXES.sub("", norm2).strip()

    tokens1 = set(base1.split())
    tokens2 = set(base2.split())
    shared = tokens1 & tokens2

    diff1 = tokens1 - tokens2
    diff2 = tokens2 - tokens1

    # Check for branch / location modifier relationship
    has_branch_mod = bool(diff1 & BRANCH_LOCATION_MODIFIERS or diff2 & BRANCH_LOCATION_MODIFIERS)
    if shared and (len(shared) >= 2 or (len(shared) == 1 and len(list(shared)[0]) >= 4)):
        shared_str = " ".join(sorted(shared))
        if has_branch_mod:
            return {
                "relationship_type": "branch_or_division",
                "rationale": f"Shares brand '{shared_str}' with distinct branch or division modifier",
            }
        elif fuzz.token_sort_ratio(base1, base2) >= 70.0:
            return {
                "relationship_type": "affiliated_entity",
                "rationale": f"Shares brand '{shared_str}' as a distinct operating entity",
            }

    return None


def match_organizations(org1: str, org2: str) -> Tuple[bool, float, str]:
    """
    Compares organizations using RapidFuzz and context-aware Python rules:
    - Normalizes corporate suffixes (Corp, Inc, Ltd, LLC)
    - Maps domains to brand names (zurichcredit.ch <-> Zurich Credit)
    - Detects acronym aliases (ZCB <-> Zurich Credit Bank)
    - Strictly prevents merging distinct branches, divisions, and locations.
    """
    norm1 = normalize_entity_text(org1)
    norm2 = normalize_entity_text(org2)

    if norm1 == norm2:
        return True, 100.0, "exact_org"

    # Strip corporate suffixes (e.g. 'Acme Corp' vs 'Acme Corporation')
    base1 = CORP_SUFFIXES.sub("", norm1).strip()
    base2 = CORP_SUFFIXES.sub("", norm2).strip()

    if len(base1) >= 3 and base1 == base2:
        return True, 95.0, "alias_corp_suffix"

    # 1. Domain to organization mapping (e.g. 'zurichcredit.ch' and 'Zurich Credit')
    clean_d1 = re.sub(r"\.(?:com|org|net|ch|io|co|in|de|fr|uk|ai|gov)$", "", norm1)
    clean_d2 = re.sub(r"\.(?:com|org|net|ch|io|co|in|de|fr|uk|ai|gov)$", "", norm2)
    nospace1 = re.sub(r"\s+", "", base1)
    nospace2 = re.sub(r"\s+", "", base2)
    if (clean_d1 == nospace2 or clean_d2 == nospace1) and min(len(clean_d1), len(clean_d2)) >= 4:
        return True, 92.0, "alias_domain_mapping"

    # 2. Acronym matching (e.g. 'Zurich Credit Bank' and 'ZCB')
    words1 = [w for w in base1.split() if w]
    words2 = [w for w in base2.split() if w]
    acronym1 = "".join(w[0] for w in words1)
    acronym2 = "".join(w[0] for w in words2)
    if (len(words1) >= 2 and acronym1 == base2 and len(base2) >= 2) or (len(words2) >= 2 and acronym2 == base1 and len(base1) >= 2):
        return True, 90.0, "alias_acronym"

    # 3. Branch / division / location conflict check
    tokens1 = set(base1.split())
    tokens2 = set(base2.split())
    diff1 = tokens1 - tokens2
    diff2 = tokens2 - tokens1
    if (diff1 & BRANCH_LOCATION_MODIFIERS) or (diff2 & BRANCH_LOCATION_MODIFIERS):
        # Do NOT merge distinct branches or locations automatically!
        return False, 0.0, "distinct_branch_or_division"

    # 4. RapidFuzz token sort ratio
    sim = fuzz.token_sort_ratio(base1, base2)
    if sim >= 88.0:
        return True, float(sim), "fuzzy_organization"

    return False, 0.0, "different_organization"


def match_locations(loc1: str, loc2: str) -> Tuple[bool, float, str]:
    """
    Compares locations. Strict matching to avoid grouping facilities with parent cities.
    """
    norm1 = normalize_entity_text(loc1)
    norm2 = normalize_entity_text(loc2)

    if norm1 == norm2:
        return True, 100.0, "exact_location"

    sim = fuzz.token_sort_ratio(norm1, norm2)
    if sim >= 90.0:
        return True, float(sim), "fuzzy_location"

    return False, 0.0, "different_location"


def compare_entities(e1: ExtractedEntity, e2: ExtractedEntity) -> Tuple[bool, float, str]:
    """
    Dispatches to the appropriate entity-type-specific matching strategy.
    """
    if e1.label != e2.label:
        return False, 0.0, "type_mismatch"

    label = e1.label

    if label == "date":
        return match_dates(e1.text, e2.text)
    elif label == "time":
        return match_times(e1.text, e2.text)
    elif label == "identifier":
        return match_identifiers(e1.text, e2.text)
    elif label == "person":
        return match_persons(e1.text, e2.text)
    elif label == "organization":
        return match_organizations(e1.text, e2.text)
    elif label == "location":
        return match_locations(e1.text, e2.text)
    else:
        # Generic strict fallback
        norm1 = normalize_entity_text(e1.text)
        norm2 = normalize_entity_text(e2.text)
        if norm1 == norm2:
            return True, 100.0, "exact_match"
        sim = fuzz.token_sort_ratio(norm1, norm2)
        return (True, float(sim), "fuzzy_fallback") if sim >= 85.0 else (False, 0.0, "no_match")


def select_canonical_name(cluster: List[ExtractedEntity], entity_type: str) -> str:
    """
    Selects the most informative canonical name for an entity cluster.
    For persons, prefers full names (e.g. 'Vikram Nair' over 'Vikram' or 'v.nair').
    """
    if not cluster:
        return ""

    if entity_type == "person":
        # Prioritize mentions with both first and last name
        full_names = []
        for e in cluster:
            parsed = parse_person_components(e.text)
            if parsed["last"] and len(parsed["first"]) > 1:
                # Proper full name (title-cased)
                full_names.append(e.text)
        if full_names:
            return max(full_names, key=lambda n: (cluster.count(n), len(n)))

    # Default to most frequent, then longest mention
    name_counts: Dict[str, int] = {}
    for e in cluster:
        name_counts[e.text] = name_counts.get(e.text, 0) + 1

    return max(name_counts.keys(), key=lambda k: (name_counts[k], len(k)))


def generate_candidate_matches(
    entities: List[ExtractedEntity],
    case_id: str,
) -> List[CandidateMatch]:
    """
    Groups entities into candidate clusters using entity-type-specific strategies.
    Never merges ambiguous person identities automatically.
    Displays 'is_single_occurrence=True' and similarity_score=0.0 for single mentions.
    """
    if not entities:
        return []

    # Group entities by category
    by_type: Dict[str, List[ExtractedEntity]] = {}
    for ent in entities:
        if not ent.text or len(ent.text.strip()) < 2:
            continue
        by_type.setdefault(ent.label, []).append(ent)

    candidate_matches: List[CandidateMatch] = []

    for entity_type, type_entities in by_type.items():
        clusters: List[List[ExtractedEntity]] = []
        cluster_match_types: List[str] = []
        cluster_scores: List[List[float]] = []

        for ent in type_entities:
            matched_cluster_idx = None
            best_score = 0.0
            best_match_type = "single_occurrence"

            for c_idx, cluster in enumerate(clusters):
                if entity_type == "person":
                    # Check for explicit contradiction with any member
                    if any(persons_contradict(ent.text, member.text) for member in cluster):
                        continue

                    # Check for alias / partial / exact matches with cluster members
                    member_scores = []
                    member_match_types = []
                    for member in cluster:
                        is_match, score, m_type = compare_entities(ent, member)
                        if is_match:
                            member_scores.append(score)
                            member_match_types.append(m_type)

                    if member_scores:
                        avg_score = sum(member_scores) / len(member_scores)
                        if avg_score > best_score:
                            best_score = avg_score
                            matched_cluster_idx = c_idx
                            best_match_type = member_match_types[0]
                else:
                    # For non-person entities: all members must match (e.g. same date, same time, same identifier)
                    member_scores = []
                    member_match_types = []
                    all_match = True

                    for member in cluster:
                        is_match, score, m_type = compare_entities(ent, member)
                        if not is_match:
                            all_match = False
                            break
                        member_scores.append(score)
                        member_match_types.append(m_type)

                    if all_match and member_scores:
                        avg_score = sum(member_scores) / len(member_scores)
                        if avg_score > best_score:
                            best_score = avg_score
                            matched_cluster_idx = c_idx
                            best_match_type = member_match_types[0]

            if matched_cluster_idx is not None:
                clusters[matched_cluster_idx].append(ent)
                cluster_scores[matched_cluster_idx].append(best_score)
                cluster_match_types[matched_cluster_idx] = best_match_type
            else:
                clusters.append([ent])
                cluster_scores.append([])
                cluster_match_types.append("single_occurrence")

        # Convert clusters to CandidateMatch objects
        for c_idx, cluster in enumerate(clusters):
            if not cluster:
                continue

            canonical_name = select_canonical_name(cluster, entity_type)
            is_single = len(cluster) == 1

            if is_single:
                sim_score = 0.0
                match_type_label = "single_occurrence"
            else:
                scores_list = cluster_scores[c_idx]
                sim_score = round(sum(scores_list) / len(scores_list), 1) if scores_list else 100.0
                match_type_label = cluster_match_types[c_idx]

            # Average classification confidence of the entity detector
            avg_classification_conf = round(sum(e.confidence for e in cluster) / len(cluster), 4)

            # Average source OCR confidence (if present from image OCR)
            ocr_confs = [e.ocr_confidence for e in cluster if getattr(e, "ocr_confidence", None) is not None]
            avg_ocr_conf = round(sum(ocr_confs) / len(ocr_confs), 4) if ocr_confs else None

            # Collect verification flags across mentions
            cluster_is_low_conf = any(getattr(e, "is_low_confidence", False) for e in cluster)
            cluster_req_verify = any(getattr(e, "requires_source_verification", False) for e in cluster)
            reasons = set()

            for e in cluster:
                for qf in getattr(e, "quality_flags", []):
                    reasons.add(qf)

            # Check for ambiguous time expressions (e.g. '10:14' lacking AM/PM and timezone)
            if entity_type == "time":
                for e in cluster:
                    amb_meridiem, amb_tz = check_time_ambiguity(e.text)
                    if amb_meridiem or amb_tz:
                        cluster_is_low_conf = True
                        cluster_req_verify = True
                        if amb_meridiem:
                            reasons.add("ambiguous_time_missing_meridiem")
                        if amb_tz:
                            reasons.add("unspecified_timezone")

            # Check for forensic identifiers requiring source verification (e.g. KL-8842)
            if entity_type == "identifier":
                for e in cluster:
                    if getattr(e, "requires_source_verification", False) or bool(re.search(r"^[A-Z]{2}[-\s]?\d{3,5}$", e.text.strip(), re.IGNORECASE)):
                        cluster_req_verify = True
                        reasons.add("identifier_source_image_verification_needed")

            mentions = [
                EntityMention(
                    text=e.text,
                    evidence_id=e.evidence_id or "unknown",
                    filename=e.filename or "unknown",
                    confidence=e.confidence,
                    ocr_confidence=getattr(e, "ocr_confidence", None),
                    start_char=e.start_char,
                    end_char=e.end_char,
                    source_segment_id=getattr(e, "source_segment_id", None),
                    is_low_confidence=getattr(e, "is_low_confidence", False),
                    requires_source_verification=getattr(e, "requires_source_verification", False),
                    quality_flags=getattr(e, "quality_flags", []),
                )
                for e in cluster
            ]

            candidate_matches.append(
                CandidateMatch(
                    case_id=case_id,
                    entity_type=entity_type,
                    canonical_name=canonical_name,
                    similarity_score=sim_score,
                    classification_confidence=avg_classification_conf,
                    ocr_confidence=avg_ocr_conf,
                    extraction_confidence=avg_classification_conf,
                    is_single_occurrence=is_single,
                    match_type=match_type_label,
                    status="pending",
                    is_low_confidence=cluster_is_low_conf,
                    requires_source_verification=cluster_req_verify,
                    verification_reasons=sorted(list(reasons)),
                    related_entities=[],
                    mentions=mentions,
                )
            )

    # Cross-reference candidate organizational relationships (branches, divisions, affiliates)
    org_candidates = [c for c in candidate_matches if c.entity_type == "organization"]
    for i in range(len(org_candidates)):
        for j in range(i + 1, len(org_candidates)):
            c1 = org_candidates[i]
            c2 = org_candidates[j]
            rel = find_organization_relationship(c1.canonical_name, c2.canonical_name)
            if rel:
                c1.related_entities.append({
                    "target_canonical_name": c2.canonical_name,
                    "target_match_id": c2.match_id,
                    "relationship_type": rel["relationship_type"],
                    "rationale": rel["rationale"],
                })
                c2.related_entities.append({
                    "target_canonical_name": c1.canonical_name,
                    "target_match_id": c1.match_id,
                    "relationship_type": rel["relationship_type"],
                    "rationale": rel["rationale"],
                })

    # Sort candidates: multi-mention clusters first, then by extraction confidence
    candidate_matches.sort(
        key=lambda c: (not c.is_single_occurrence, len(c.mentions), c.similarity_score),
        reverse=True,
    )
    return candidate_matches
