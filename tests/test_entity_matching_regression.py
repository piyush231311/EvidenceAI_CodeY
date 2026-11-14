"""
Regression test suite for Evidence AI entity recognition and entity matching pipeline.
Verifies all fixes for:
1. Strict date & time normalization (no fuzzy similarity grouping across different calendar dates/times).
2. Elimination of false positive identifiers ('Inbox', 'OFFICIAL work email').
3. Suppression of generic words ('portal') and job titles ('Managing Partner', 'Director') from organizations.
4. Preservation of questionable or garbled OCR detections in low-confidence review category with quality flags.
5. Distinct tracking of OCR recognition confidence, GLiNER classification confidence, and RapidFuzz similarity.
6. Prioritization of low-confidence identifiers (such as KL-8842) for source-image verification.
7. Handling ambiguous time expressions ('10:14') without assuming AM/PM or timezone.
8. Suggesting related organizations as candidate relationships without merging branches/locations automatically.
9. Organizational aliases using RapidFuzz and context-aware rules (acronyms, domain mapping, corp suffixes).
10. Preservation of source text, IDs, offsets, and evidence references.
"""

import pytest
from src.intelligence.gliner_extractor import (
    ExtractedEntity,
    extract_entities_from_text,
    validate_and_filter_entity,
    is_valid_identifier,
    is_noise_or_job_title,
    JOB_TITLES,
    GENERIC_NOISE_WORDS,
)
from src.intelligence.entity_matcher import (
    generate_candidate_matches,
    match_dates,
    match_times,
    match_identifiers,
    match_persons,
    match_organizations,
    find_organization_relationship,
    persons_contradict,
    check_time_ambiguity,
)


def test_time_matching_no_fuzzy_grouping():
    """Different times (10:23 AM, 10:30 AM, 10:37 AM) must NEVER be grouped together."""
    times = [
        ExtractedEntity(text="10:23 AM", label="time", start_char=0, end_char=8, confidence=0.95),
        ExtractedEntity(text="10:30 AM", label="time", start_char=0, end_char=8, confidence=0.95),
        ExtractedEntity(text="10:37 AM", label="time", start_char=0, end_char=8, confidence=0.95),
        ExtractedEntity(text="10:30am", label="time", start_char=0, end_char=7, confidence=0.95),
    ]

    candidates = generate_candidate_matches(times, case_id="case-times")
    assert len(candidates) == 3

    multi_cluster = [c for c in candidates if not c.is_single_occurrence]
    assert len(multi_cluster) == 1
    assert len(multi_cluster[0].mentions) == 2
    assert multi_cluster[0].similarity_score == 100.0
    assert multi_cluster[0].match_type == "normalized_time"
    mention_texts = {m.text for m in multi_cluster[0].mentions}
    assert mention_texts == {"10:30 AM", "10:30am"}

    single_clusters = [c for c in candidates if c.is_single_occurrence]
    assert len(single_clusters) == 2
    for sc in single_clusters:
        assert sc.similarity_score == 0.0
        assert sc.match_type == "single_occurrence"

    m_diff, score_diff, _ = match_times("10:23 AM", "10:30 AM")
    assert not m_diff
    assert score_diff == 0.0

    m_same, score_same, _ = match_times("10:30 AM", "10:30am")
    assert m_same
    assert score_same == 100.0


def test_date_matching_no_fuzzy_grouping():
    """Different dates (November 12 vs November 13) must NEVER be grouped together."""
    dates = [
        ExtractedEntity(text="November 12", label="date", start_char=0, end_char=11, confidence=0.95),
        ExtractedEntity(text="November 13", label="date", start_char=0, end_char=11, confidence=0.95),
        ExtractedEntity(text="Nov 12, 2026", label="date", start_char=0, end_char=12, confidence=0.95),
    ]

    candidates = generate_candidate_matches(dates, case_id="case-dates")
    assert len(candidates) == 2

    multi_cluster = [c for c in candidates if not c.is_single_occurrence]
    assert len(multi_cluster) == 1
    assert len(multi_cluster[0].mentions) == 2
    assert multi_cluster[0].similarity_score == 100.0
    assert multi_cluster[0].match_type == "normalized_date"

    single_clusters = [c for c in candidates if c.is_single_occurrence]
    assert len(single_clusters) == 1
    assert single_clusters[0].canonical_name == "November 13"
    assert single_clusters[0].similarity_score == 0.0


def test_identifier_noise_filtering():
    """Generic noise words like 'Inbox' or 'OFFICIAL work email' are rejected as identifiers."""
    assert not is_valid_identifier("Inbox")
    assert not is_valid_identifier("OFFICIAL work email")
    assert not is_valid_identifier("Drafts")
    assert not is_valid_identifier("Sent")
    assert not is_valid_identifier("Subject")

    assert is_valid_identifier("john.doe@domain.com")
    assert is_valid_identifier("+1-555-0199")
    assert is_valid_identifier("TXN-90234")
    assert is_valid_identifier("SHA256:e3b0c442")


def test_generic_portal_and_managing_partner_organization_suppression():
    """Generic words like 'portal' and job titles like 'Managing Partner' are NOT organizations."""
    assert is_noise_or_job_title("portal", "organization")
    assert is_noise_or_job_title("managing partner", "organization")
    assert is_noise_or_job_title("senior partner", "organization")
    assert is_noise_or_job_title("general counsel", "organization")
    assert is_noise_or_job_title("director", "organization")
    assert is_noise_or_job_title("dashboard", "organization")
    assert is_noise_or_job_title("website", "organization")

    valid_portal, _, _, _, _ = validate_and_filter_entity("portal", "organization", 0.85)
    assert not valid_portal

    valid_partner, _, _, _, _ = validate_and_filter_entity("Managing Partner", "organization", 0.90)
    assert not valid_partner

    sample_text = "The Managing Partner logged into the customer portal to review Acme Corp records."
    ents = extract_entities_from_text(sample_text)
    orgs = [e.text for e in ents if e.label == "organization"]
    assert "Managing Partner" not in orgs
    assert "portal" not in orgs
    assert "Acme Corp" in orgs


def test_garbled_ocr_preserved_in_low_confidence():
    """Questionable or garbled OCR text is preserved in low-confidence review category with quality flags."""
    is_valid, norm_label, is_low_conf, req_verify, flags = validate_and_filter_entity(
        text="Forrvard ,, anders",
        label="organization",
        confidence=0.42,
        ocr_confidence=0.61,
    )
    # Must be preserved rather than silently dropped
    assert is_valid
    assert is_low_conf is True
    assert req_verify is True
    assert "garbled_ocr_artifacts" in flags
    assert "low_classification_confidence" in flags

    garbled_ent = ExtractedEntity(
        text="Forrvard ,, anders",
        label="organization",
        confidence=0.42,
        ocr_confidence=0.61,
        start_char=10,
        end_char=28,
        is_low_confidence=is_low_conf,
        requires_source_verification=req_verify,
        quality_flags=flags,
    )
    cands = generate_candidate_matches([garbled_ent], case_id="case-garbled")
    assert len(cands) == 1
    assert cands[0].is_low_confidence is True
    assert cands[0].requires_source_verification is True
    assert "garbled_ocr_artifacts" in cands[0].verification_reasons


def test_distinct_confidence_fields():
    """Keeps OCR confidence, GLiNER classification confidence, and RapidFuzz similarity distinct."""
    e1 = ExtractedEntity(
        text="Indiranagar",
        label="location",
        confidence=0.91,        # GLiNER confidence
        ocr_confidence=0.84,    # PaddleOCR confidence
        start_char=0,
        end_char=11,
    )
    e2 = ExtractedEntity(
        text="Indiranagar",
        label="location",
        confidence=0.95,
        ocr_confidence=0.88,
        start_char=20,
        end_char=31,
    )

    cands = generate_candidate_matches([e1, e2], case_id="case-conf")
    assert len(cands) == 1
    c = cands[0]
    # RapidFuzz similarity is 100.0%
    assert c.similarity_score == 100.0
    # Average GLiNER classification confidence is (0.91 + 0.95) / 2 = 0.93
    assert c.classification_confidence == 0.93
    # Average OCR recognition confidence is (0.84 + 0.88) / 2 = 0.86
    assert c.ocr_confidence == 0.86
    # Each mention preserves its own OCR and classification confidence
    assert c.mentions[0].confidence == 0.91
    assert c.mentions[0].ocr_confidence == 0.84
    assert c.mentions[1].confidence == 0.95
    assert c.mentions[1].ocr_confidence == 0.88


def test_low_confidence_identifier_source_image_priority():
    """Prioritizes forensic identifiers like KL-8842 for source-image verification."""
    is_valid, norm_label, is_low_conf, req_verify, flags = validate_and_filter_entity(
        text="KL-8842",
        label="identifier",
        confidence=0.78,
        ocr_confidence=0.72,
    )
    assert is_valid
    assert req_verify is True
    assert "identifier_source_verification_priority" in flags

    ent = ExtractedEntity(
        text="KL-8842",
        label="identifier",
        confidence=0.78,
        ocr_confidence=0.72,
        start_char=0,
        end_char=7,
        is_low_confidence=is_low_conf,
        requires_source_verification=req_verify,
        quality_flags=flags,
    )
    cands = generate_candidate_matches([ent], case_id="case-plate")
    assert len(cands) == 1
    assert cands[0].requires_source_verification is True
    assert "identifier_source_image_verification_needed" in cands[0].verification_reasons


def test_ambiguous_time_expression_10_14():
    """Handles ambiguous time '10:14' without assuming AM/PM or timezone."""
    is_amb_meridiem, is_amb_tz = check_time_ambiguity("10:14")
    assert is_amb_meridiem is True
    assert is_amb_tz is True

    # Ambiguous '10:14' must NOT match explicit '10:14 AM'
    m_diff, score_diff, reason = match_times("10:14", "10:14 AM")
    assert not m_diff
    assert score_diff == 0.0
    assert reason == "ambiguous_time_meridiem"

    # Ambiguous '10:14' must NOT match explicit '10:14 PM'
    m_diff2, score_diff2, reason2 = match_times("10:14", "10:14 PM")
    assert not m_diff2
    assert score_diff2 == 0.0

    # Cluster containing ambiguous '10:14' must be flagged with warning
    ent = ExtractedEntity(text="10:14", label="time", confidence=0.92, start_char=0, end_char=5)
    cands = generate_candidate_matches([ent], case_id="case-amb-time")
    assert len(cands) == 1
    assert cands[0].requires_source_verification is True
    assert "ambiguous_time_missing_meridiem" in cands[0].verification_reasons


def test_related_organizations_not_merged_but_suggested_as_relationships():
    """Suggests related organizations as relationships, but does NOT merge branches/divisions."""
    # 1. Distinct branches: Zurich Credit vs Zurich Credit Geneva
    is_match, score, match_type = match_organizations("Zurich Credit", "Zurich Credit Geneva")
    assert not is_match
    assert score == 0.0
    assert match_type == "distinct_branch_or_division"

    rel = find_organization_relationship("Zurich Credit", "Zurich Credit Geneva")
    assert rel is not None
    assert rel["relationship_type"] == "branch_or_division"

    # 2. Distinct subsidiaries: Acme Corp vs Acme Logistics
    is_match2, score2, match_type2 = match_organizations("Acme Corp", "Acme Logistics")
    assert not is_match2
    assert score2 == 0.0

    # 3. Test generate_candidate_matches generates separate clusters and cross-links them
    orgs = [
        ExtractedEntity(text="Zurich Credit", label="organization", confidence=0.95, start_char=0, end_char=13),
        ExtractedEntity(text="Zurich Credit Geneva", label="organization", confidence=0.93, start_char=0, end_char=20),
    ]
    cands = generate_candidate_matches(orgs, case_id="case-org-rel")
    # Must remain 2 separate candidate clusters
    assert len(cands) == 2
    canonical_names = {c.canonical_name for c in cands}
    assert "Zurich Credit" in canonical_names
    assert "Zurich Credit Geneva" in canonical_names

    # But each cluster must list the other as a related entity
    c_parent = next(c for c in cands if c.canonical_name == "Zurich Credit")
    c_branch = next(c for c in cands if c.canonical_name == "Zurich Credit Geneva")
    assert len(c_parent.related_entities) == 1
    assert c_parent.related_entities[0]["target_canonical_name"] == "Zurich Credit Geneva"
    assert c_parent.related_entities[0]["relationship_type"] == "branch_or_division"
    assert len(c_branch.related_entities) == 1
    assert c_branch.related_entities[0]["target_canonical_name"] == "Zurich Credit"


def test_organizational_aliases():
    """Candidate organizational aliases using RapidFuzz, acronyms, and domain rules."""
    # 1. Corporate suffix alias
    m_corp, score_corp, type_corp = match_organizations("Acme Corp", "Acme Corporation")
    assert m_corp is True
    assert score_corp == 95.0
    assert type_corp == "alias_corp_suffix"

    # 2. Acronym alias
    m_acr, score_acr, type_acr = match_organizations("Zurich Credit Bank", "ZCB")
    assert m_acr is True
    assert score_acr == 90.0
    assert type_acr == "alias_acronym"

    # 3. Domain mapping alias
    m_dom, score_dom, type_dom = match_organizations("zurichcredit.ch", "Zurich Credit")
    assert m_dom is True
    assert score_dom == 92.0
    assert type_dom == "alias_domain_mapping"


def test_preservation_of_source_metadata():
    """Preserves all original source text, source IDs, extraction offsets, and evidence references."""
    ent = ExtractedEntity(
        text="Alpha-99",
        label="identifier",
        confidence=0.91,
        ocr_confidence=0.88,
        start_char=142,
        end_char=150,
        evidence_id="ev-uuid-1234",
        filename="scanner_img_01.png",
        source_segment_id="seg-page-2",
        is_low_confidence=False,
    )
    cands = generate_candidate_matches([ent], case_id="case-meta")
    assert len(cands) == 1
    mention = cands[0].mentions[0]
    assert mention.text == "Alpha-99"
    assert mention.evidence_id == "ev-uuid-1234"
    assert mention.filename == "scanner_img_01.png"
    assert mention.start_char == 142
    assert mention.end_char == 150
    assert mention.source_segment_id == "seg-page-2"
    assert mention.confidence == 0.91
    assert mention.ocr_confidence == 0.88
