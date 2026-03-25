"""
requirement_cleaner.py — Pre-processing stage for raw extracted requirements.

Cleans raw requirement sentences BEFORE sending them to the LLM:
  - Strips leading numbering artifacts (1., 2), a., etc.)
  - Routes non-requirements INTELLIGENTLY instead of discarding:
      • Project descriptions → routed to Product Scope
      • Future features → routed to Assumptions / Future Scope
      • Deadlines → ignored
      • Incomplete inputs → flagged as "Needs User Input"
  - Normalizes whitespace and sentence structure
"""

import re

# ─── Patterns for classifying non-requirements into routes ────────────────────

_TECH_TOKENS = {
    "react", "angular", "vue", "next.js", "nextjs", "vite",
    "flask", "django", "fastapi", "express", "node.js", "nodejs",
    "mongodb", "postgresql", "mysql", "sqlite", "redis", "firebase",
    "docker", "kubernetes", "aws", "azure", "gcp", "heroku",
    "tailwind", "bootstrap", "material-ui", "typescript", "javascript",
    "python", "java", "c#", "c++", "golang", "rust", "swift", "kotlin",
    "html", "css", "sass", "less", "webpack", "babel",
    "git", "github", "gitlab", "bitbucket", "jira", "trello",
    "ci/cd", "jenkins", "terraform", "nginx", "apache",
}

# Deadline patterns (→ discard entirely)
_DEADLINE_PATTERNS = [
    re.compile(r"\b(by\s+(january|february|march|april|may|june|july|august|september|october|november|december))", re.I),
    re.compile(r"\b(Q[1-4]\s*20\d{2}|deadline|timeline|schedule|milestone)\b", re.I),
]

# Future-idea phrases (→ route to assumptions/future scope)
_FUTURE_PATTERNS = [
    re.compile(r"\b(would be nice|could also|maybe|in the future|later phase|nice to have|optional feature|could add|future version|planned for)\b", re.I),
]

# Project description phrases (→ route to product scope)
_DESCRIPTION_PATTERNS = [
    re.compile(r"\b(the project is|this (application|system|tool|platform) (is|will be)|project (title|name|overview|description|goal))\b", re.I),
    re.compile(r"\b(main (purpose|goal|objective)|aims to|designed to)\b", re.I),
]

# Tech-stack explanation phrases (→ route to product scope / operating environment)
_TECH_STACK_PATTERNS = [
    re.compile(r"\b(we will use|tech stack|technology|framework|library|built with|built using|implemented in|written in|powered by|using .+ for)\b", re.I),
]

# Notes/disclaimers (→ discard)
_NOTE_PATTERNS = [
    re.compile(r"\b(note:|disclaimer:|fyi:|reminder:)", re.I),
]

# Leading numbering
_NUMBERING_RE = re.compile(r"^\s*(\d{1,3}[\.)\-]\s*|[a-zA-Z][\.)\-]\s*|[ivxIVX]+[\.)\-]\s*)")
_MULTISPACE_RE = re.compile(r"\s+")


def _strip_numbering(sentence: str) -> str:
    """Remove leading numbering artifacts like '1.', '2)', 'a.', etc."""
    return _NUMBERING_RE.sub("", sentence).strip()


def _normalize(sentence: str) -> str:
    """Normalize whitespace and ensure proper sentence ending."""
    s = _MULTISPACE_RE.sub(" ", sentence).strip()
    if s and s[-1] not in ".!?":
        s += "."
    return s


def _classify_non_requirement(sentence: str) -> str | None:
    """
    Classify a sentence as a non-requirement type, or return None if it IS a requirement.

    Returns one of:
      "deadline"      → discard entirely
      "note"          → discard entirely
      "description"   → route to product scope
      "future"        → route to assumptions / future scope
      "tech_stack"    → route to operating environment
      "incomplete"    → flag as needing user input
      None            → this IS a valid requirement, keep it
    """
    lower = sentence.lower()

    # Deadlines → discard
    for p in _DEADLINE_PATTERNS:
        if p.search(lower):
            return "deadline"

    # Notes → discard
    for p in _NOTE_PATTERNS:
        if p.search(lower):
            return "note"

    # Future ideas → route to assumptions
    for p in _FUTURE_PATTERNS:
        if p.search(lower):
            return "future"

    # Project descriptions → route to scope
    for p in _DESCRIPTION_PATTERNS:
        if p.search(lower):
            return "description"

    # Tech stack mentions → route to operating environment
    for p in _TECH_STACK_PATTERNS:
        if p.search(lower):
            return "tech_stack"

    # Pure tech-token sentences (>40% tech words)
    words = set(re.findall(r"[\w\.\-\+#]+", lower))
    tech_overlap = words & _TECH_TOKENS
    non_stop = {w for w in words if len(w) > 2}
    if non_stop and len(tech_overlap) / max(len(non_stop), 1) > 0.4:
        return "tech_stack"

    # Incomplete/malformed (less than 4 words, or no verb-like word)
    word_list = sentence.split()
    if len(word_list) < 4:
        return "incomplete"

    return None


def clean_requirements(requirements: list) -> dict:
    """
    Clean and route raw requirement dicts from the analyzer.

    Returns a dict with:
      "requirements": list of cleaned requirement dicts (valid requirements)
      "routed": dict with keys "scope_hints", "future_scope", "environment_hints", "incomplete"
                containing sentences routed from non-requirements
    """
    cleaned = []
    routed = {
        "scope_hints": [],        # project descriptions → Product Scope
        "future_scope": [],       # future ideas → Assumptions / TBD List
        "environment_hints": [],  # tech stack mentions → Operating Environment
        "incomplete": [],         # malformed/too-short → flagged
    }

    for req in requirements:
        raw_sentence = req.get("sentence", "").strip()
        if not raw_sentence:
            continue

        # Step 1: Strip numbering
        sentence = _strip_numbering(raw_sentence)

        if not sentence:
            continue

        # Step 2: Classify
        route = _classify_non_requirement(sentence)

        if route == "deadline" or route == "note":
            # Silently discard deadlines and notes
            continue
        elif route == "description":
            routed["scope_hints"].append(_normalize(sentence))
            continue
        elif route == "future":
            routed["future_scope"].append(_normalize(sentence))
            continue
        elif route == "tech_stack":
            routed["environment_hints"].append(_normalize(sentence))
            continue
        elif route == "incomplete":
            routed["incomplete"].append({
                "original_id": req.get("id"),
                "sentence": _normalize(sentence),
                "flag": "Incomplete Requirement – Needs User Input",
            })
            continue

        # Step 3: Valid requirement — normalize and keep
        sentence = _normalize(sentence)
        cleaned.append({
            **req,
            "sentence": sentence,
            "original_sentence": raw_sentence,   # preserve for traceability
        })

    return {
        "requirements": cleaned,
        "routed": routed,
    }
