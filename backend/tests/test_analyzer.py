"""
tests/test_analyzer.py - Unit tests for analyzer.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from analyzer import is_requirement, classify_requirement, detect_vague_words, compute_quality_score, analyze_document


def test_is_requirement_with_shall():
    assert is_requirement("The system shall allow users to log in.") is True

def test_is_requirement_rejects_plain_sentence():
    assert is_requirement("This document explains the project scope.") is False

def test_classify_fr():
    assert classify_requirement("The system shall allow users to upload files.") == "FR"

def test_classify_nfr():
    assert classify_requirement("The system shall maintain 99.9% uptime and ensure security compliance.") == "NFR"

def test_detect_vague_words():
    found = detect_vague_words("The UI must be user-friendly and very fast.")
    assert "user-friendly" in found
    assert "fast" in found

def test_no_vague_words():
    found = detect_vague_words("The system shall process transactions within 2 seconds.")
    assert len(found) == 0

def test_quality_score_with_no_vague():
    reqs = [
        {"type": "FR", "vague_words": [], "is_vague": False, "sentence": "...", "id": 1},
        {"type": "NFR", "vague_words": [], "is_vague": False, "sentence": "...", "id": 2},
    ]
    metrics = compute_quality_score(reqs)
    assert metrics["quality_score"] == 100

def test_quality_score_deduction_for_vague():
    reqs = [
        {"type": "FR", "vague_words": ["fast"], "is_vague": True, "sentence": "...", "id": 1},
        {"type": "NFR", "vague_words": [], "is_vague": False, "sentence": "...", "id": 2},
    ]
    metrics = compute_quality_score(reqs)
    assert metrics["quality_score"] == 95

def test_analyze_document_full():
    text = (
        "The system shall allow users to register and log in securely.\n"
        "The application must be user-friendly and fast.\n"
        "The system shall maintain 99.9% uptime.\n"
        "This is a general statement about the project."
    )
    result = analyze_document(text)
    assert result["metrics"]["total_requirements"] >= 2
    assert result["metrics"]["fr_count"] >= 1
    assert result["metrics"]["nfr_count"] >= 0
