"""
requirement_refiner.py — LLM Call 1: Requirement Refinement.

Takes cleaned requirements and:
  1. Rewrites them in IEEE style ("The system shall...")
  2. Replaces vague terms with measurable conditions
  3. Classifies FR/NFR using intent-based logic (not just keyword counting)
  4. Assigns NFR categories (Performance/Security/Usability/Scalability/Reliability)
  5. Generates context-aware Stimulus/Response flows (only when meaningful)
  6. Validates output — no corruption, no duplicates, no vague remnants
  7. Preserves traceability (original_sentence → refined text)

Falls back to a comprehensive rule-based refiner when the LLM is unavailable.
"""

import os
import re
import json

# ─── Lazy Gemini client ──────────────────────────────────────────────────────
_genai_client = None


def _get_client():
    global _genai_client
    if _genai_client is not None:
        return _genai_client
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
        return _genai_client
    except Exception:
        return None


# ─── LLM Prompt ──────────────────────────────────────────────────────────────

_REFINE_PROMPT = """You are a senior IEEE requirements engineer. Your ONLY job is to REFINE raw software requirements.

STRICT RULES:

1. REWRITE every requirement in IEEE format: "The system shall..." or "The system must..."
   - Each requirement = one single testable idea
   - No partial sentences, no ambiguity, no numbering artifacts

2. REPLACE ALL vague terms with measurable, quantified conditions:
   - "fast" → "with a response time not exceeding 2 seconds"
   - "user-friendly" → "with an interface compliant with WCAG 2.1 AA, completing primary tasks in 3 clicks or fewer"
   - "real-time" → "with end-to-end latency not exceeding 1 second"
   - "scalable" → "supporting a minimum of 5,000 concurrent users"
   - "secure" → "using AES-256 encryption for data at rest and TLS 1.2+ for data in transit"
   - "high availability" → "maintaining 99.9% uptime measured monthly"
   - "simple" → "achievable in 3 clicks or fewer"
   - "efficient" → "completing the operation within 500 milliseconds"

3. CLASSIFY using INTENT (not just keywords):
   - Functional (FR): describes what the system DOES — an action, behavior, feature, or capability
   - Non-Functional (NFR): describes a quality constraint — HOW WELL the system must perform
   - If a sentence describes BOTH an action AND a constraint, split into two separate requirements

4. For NFRs, assign exactly one category: Performance, Security, Usability, Scalability, or Reliability

5. REMOVE invalid content: tech notes, deadlines, future ideas, non-requirements

6. For each FR, generate a SPECIFIC Stimulus/Response flow:
   - Must be specific to THAT requirement (not generic)
   - Only include if the FR describes a user-facing action
   - Omit stimulus_response for internal/background operations

7. TRACEABILITY: include the original sentence for each refined requirement

OUTPUT FORMAT — return ONLY a valid JSON array:
[
  {
    "id": "REQ-001",
    "original": "The original raw sentence",
    "text": "The system shall [refined, measurable requirement].",
    "type": "FR",
    "stimulus_response": "Stimulus: [specific trigger]. Response: [specific system behavior]."
  },
  {
    "id": "REQ-002",
    "original": "The original raw sentence",
    "text": "The system shall [refined, measurable requirement].",
    "type": "NFR",
    "category": "Performance"
  }
]

Do NOT include any text outside the JSON array. Do NOT wrap in markdown code fences.
"""


def _build_refine_prompt(requirements: list, meta: dict) -> str:
    project = meta.get("project_name", "<Project>")
    lines = []
    for r in requirements:
        vague = ""
        if r.get("is_vague") and r.get("vague_words"):
            vague = f"  [VAGUE: {', '.join(r['vague_words'])}]"
        lines.append(f"- {r.get('sentence', '')}{vague}")
    reqs_block = "\n".join(lines)
    return f"PROJECT: {project}\n\nRAW REQUIREMENTS:\n{reqs_block}\n\nRefine these into the JSON array format."


def refine_requirements(requirements: list, meta: dict) -> list:
    """
    LLM Call 1: Refine raw requirements into structured, measurable form.
    Returns a list of dicts with keys: id, text, type, original,
    category (if NFR), stimulus_response (if FR and user-facing).
    Falls back to rule-based refinement if the LLM is unavailable.
    """
    client = _get_client()
    if client is None:
        result = _fallback_refine(requirements, meta)
    else:
        prompt = _build_refine_prompt(requirements, meta)
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[{"role": "user", "parts": [{"text": _REFINE_PROMPT + "\n\n" + prompt}]}],
            )
            raw = response.text.strip()
            if raw.startswith("```"):
                lines = raw.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines)
            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) > 0:
                result = parsed
            else:
                result = _fallback_refine(requirements, meta)
        except Exception as e:
            print(f"[requirement_refiner] LLM refinement failed: {e}")
            result = _fallback_refine(requirements, meta)

    # ── QUALITY VALIDATION LAYER ──
    result = _validate_and_fix(result)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY VALIDATION LAYER
# ═══════════════════════════════════════════════════════════════════════════════

_VAGUE_WORDS_CHECK = {
    "fast", "quickly", "slow", "easy", "simple", "user-friendly", "friendly",
    "intuitive", "modern", "beautiful", "nice", "good", "robust", "flexible",
    "scalable", "adequate", "sufficient", "appropriate", "reasonable", "minimal",
    "optimal", "high", "low", "real-time", "near real-time", "efficiently",
    "seamlessly", "enhanced", "advanced", "significant", "critical",
}


def _validate_and_fix(refined: list) -> list:
    """
    Post-refinement quality validation.
    Checks and auto-corrects:
      1. No vague terms remaining
      2. No text corruption (duplicate phrases)
      3. No empty/malformed entries
      4. All requirements start with "The system shall/must"
      5. Correct sequential numbering
      6. All NFRs have valid categories
      7. No duplicate requirements
    """
    valid_categories = {"Performance", "Security", "Usability", "Scalability", "Reliability"}
    seen_texts = set()
    validated = []

    for entry in refined:
        text = entry.get("text", "").strip()
        if not text or len(text) < 10:
            continue

        # Fix corruption: remove duplicate phrases
        text = _remove_duplicate_phrases(text)

        # Fix remaining vague words
        text = _replace_vague_terms(text)

        # Ensure IEEE format
        text = _ensure_ieee_format(text)

        # Skip duplicates
        text_normalized = re.sub(r"\s+", " ", text.lower().strip())
        if text_normalized in seen_texts:
            continue
        seen_texts.add(text_normalized)

        entry["text"] = text

        # Fix NFR category
        if entry.get("type") == "NFR":
            if entry.get("category") not in valid_categories:
                entry["category"] = _categorize_nfr(text)

        # Reclassify if misclassified
        entry["type"] = _intent_classify(text, entry.get("type", "FR"))

        validated.append(entry)

    # Sequential re-numbering
    for i, r in enumerate(validated):
        r["id"] = f"REQ-{i + 1:03d}"

    return validated


def _remove_duplicate_phrases(text: str) -> str:
    """
    Detect and remove duplicated phrases within a sentence.
    e.g. "achievable in 3 clicks or fewer and achievable in 3 clicks or fewer" → single occurrence
    """
    # Split into clauses and deduplicate
    # Strategy: find repeated substrings of 4+ words
    words = text.split()
    if len(words) < 8:
        return text

    # Check for exact duplicate halves connected by "and"/"or"
    for conj in [" and ", " or "]:
        if conj in text.lower():
            parts = text.split(conj, 1)
            if len(parts) == 2:
                # Normalize for comparison
                left = re.sub(r"\s+", " ", parts[0].strip().rstrip(".,")).lower()
                right = re.sub(r"\s+", " ", parts[1].strip().rstrip(".,")).lower()
                if left == right:
                    return parts[0].strip()

    # Check for repeated n-gram sequences (4+ words)
    for n in range(min(8, len(words) // 2), 3, -1):
        for i in range(len(words) - 2 * n + 1):
            chunk = " ".join(words[i:i + n]).lower()
            rest = " ".join(words[i + n:]).lower()
            if chunk in rest:
                # Remove the second occurrence
                idx = rest.find(chunk)
                # Rebuild: keep first part, skip the duplicate
                before_dup = " ".join(words[:i + n])
                after_first = " ".join(words[i + n:])
                after_dup = after_first[:idx] + after_first[idx + len(chunk):]
                result = (before_dup + " " + after_dup).strip()
                result = re.sub(r"\s+", " ", result)
                result = re.sub(r"\s+([.,;])", r"\1", result)
                if len(result) > 10:
                    return result

    return text


# ═══════════════════════════════════════════════════════════════════════════════
# INTENT-BASED CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

# NFR intent patterns — if the CORE MEANING is about quality/constraint
_NFR_INTENT_PATTERNS = [
    re.compile(r"\b(response time|latency|throughput|uptime|downtime|concurrent users|load)\b", re.I),
    re.compile(r"\b(encrypt|decrypt|authentication|authorization|access control|password|token|certificate)\b", re.I),
    re.compile(r"\bwcag\b|accessibility|usability|clicks or fewer|\bux\b|\bui\b.*(guideline|standard)", re.I),
    re.compile(r"\b(scalab|concurrent|capacity|horizontal|vertical|elastic)\b", re.I),
    re.compile(r"\b(reliab|availability|fault.?toleran|recover|backup|redundanc|failover|resilien)\b", re.I),
    re.compile(r"\b(99\.\d+%|percent uptime|maintain.*functionality under)\b", re.I),
    re.compile(r"\b(within \d+ (seconds?|milliseconds?|ms)|not exceeding \d+)\b", re.I),
]

# FR intent patterns — the CORE MEANING is about system behavior/action
_FR_INTENT_PATTERNS = [
    re.compile(r"\b(shall (allow|enable|provide|display|generate|send|receive|process|store|retrieve|create|export|import|upload|download|search|filter|notify|validate|authenticate|delete|update|manage))\b", re.I),
    re.compile(r"\b(must (allow|enable|provide|display|generate|send|receive|process|store|retrieve|create|export|import|upload|download|search|filter|notify|validate|authenticate|delete|update|manage))\b", re.I),
    re.compile(r"\b(the user (can|shall|must|should|will))\b", re.I),
]


def _intent_classify(text: str, current_type: str) -> str:
    """
    Reclassify a requirement based on the INTENT of the sentence.
    Returns 'FR' or 'NFR'.
    """
    nfr_hits = sum(1 for p in _NFR_INTENT_PATTERNS if p.search(text))
    fr_hits = sum(1 for p in _FR_INTENT_PATTERNS if p.search(text))

    if nfr_hits > fr_hits:
        return "NFR"
    elif fr_hits > nfr_hits:
        return "FR"
    # If tied, keep current classification
    return current_type


# ═══════════════════════════════════════════════════════════════════════════════
# VAGUE TERM REPLACEMENT
# ═══════════════════════════════════════════════════════════════════════════════

_VAGUE_REPLACEMENTS = {
    "fast":           "with a response time not exceeding 2 seconds",
    "quickly":        "with a response time not exceeding 2 seconds",
    "quick":          "with a response time not exceeding 2 seconds",
    "rapid":          "with a response time not exceeding 2 seconds",
    "slow":           "exceeding acceptable response thresholds (>5 seconds)",
    "easy":           "achievable in 3 clicks or fewer",
    "simple":         "achievable in 3 clicks or fewer",
    "user-friendly":  "compliant with WCAG 2.1 AA accessibility guidelines",
    "friendly":       "compliant with WCAG 2.1 AA accessibility guidelines",
    "intuitive":      "requiring no external training for basic operations",
    "modern":         "following current UI/UX design standards (Material Design 3 or equivalent)",
    "beautiful":      "following current UI/UX design standards (Material Design 3 or equivalent)",
    "nice":           "meeting defined acceptance criteria",
    "good":           "meeting defined acceptance criteria",
    "robust":         "maintaining functionality under 2x expected peak load",
    "flexible":       "supporting configuration changes without code modification",
    "scalable":       "supporting at least 5,000 concurrent users",
    "adequate":       "meeting the minimum thresholds defined in this SRS",
    "sufficient":     "meeting the minimum thresholds defined in this SRS",
    "appropriate":    "meeting the minimum thresholds defined in this SRS",
    "reasonable":     "within organization-approved limits",
    "minimal":        "using the fewest resources necessary as defined per metric",
    "optimal":        "achieving the best measurable outcome per benchmark",
    "high":           "at or above the 95th percentile of the defined metric",
    "low":            "at or below the 5th percentile of the defined metric",
    "real-time":      "with end-to-end latency not exceeding 1 second",
    "near real-time": "with end-to-end latency not exceeding 3 seconds",
    "efficiently":    "completing the operation within 500 milliseconds",
    "seamlessly":     "without user-visible interruption or error",
    "enhanced":       "improved by at least 20% over the previous baseline",
    "advanced":       "incorporating state-of-the-art processing capabilities",
    "large":          "exceeding 10,000 records or 1 GB of data",
    "small":          "fewer than 100 records or 10 MB of data",
    "significant":    "exceeding 25% of the baseline measurement",
    "important":      "classified as Priority-1 in the project backlog",
    "critical":       "classified as Priority-0 (blocking) in the project backlog",
}


def _replace_vague_terms(text: str) -> str:
    """Replace known vague words with measurable alternatives, preventing duplicates."""
    result = text
    for vague, replacement in _VAGUE_REPLACEMENTS.items():
        # Only replace if the replacement isn't already in the text
        if replacement.lower() in result.lower():
            # Already replaced — just remove the vague word if it's still dangling
            pattern = re.compile(r"\b" + re.escape(vague) + r"\b", re.IGNORECASE)
            # Check if the vague word is separate from its replacement
            if pattern.search(result):
                # Find all matches and only remove ones NOT adjacent to the replacement
                result = pattern.sub("", result)
                result = re.sub(r"\s+", " ", result).strip()
        else:
            pattern = re.compile(r"\b" + re.escape(vague) + r"\b", re.IGNORECASE)
            result = pattern.sub(replacement, result)

    # Clean up any double spaces or weird punctuation from replacements
    result = re.sub(r"\s+", " ", result).strip()
    result = re.sub(r"\s+([.,;:])", r"\1", result)
    return result


def _ensure_ieee_format(text: str) -> str:
    """Ensure the requirement starts with 'The system shall' or 'The system must'."""
    # Already in IEEE format
    if re.match(r"^The system (shall|must)\b", text, re.I):
        return text

    # Starts with "The application/tool/platform shall/must" — normalize
    m = re.match(r"^The (application|tool|platform|software|service)\s+(shall|must)\b", text, re.I)
    if m:
        return "The system " + m.group(2).lower() + text[m.end():]

    # Starts with "The user shall/can/should" — reframe to system perspective
    m = re.match(r"^The user (shall|can|should|must|will)\s+(.+)", text, re.I)
    if m:
        action = m.group(2)
        return f"The system shall allow the user to {action}"

    # Starts with a verb (e.g., "Allow users to...")
    m = re.match(r"^(Allow|Enable|Provide|Display|Generate|Create|Delete|Update|Send|Support)\s+", text, re.I)
    if m:
        return f"The system shall {text[0].lower()}{text[1:]}"

    # Starts with "The <subject> should/shall/must/can" (e.g. "The dashboard should display...")
    m = re.match(r"^The\s+(\w+)\s+(shall|must|should|can|will)\s+(.+)", text, re.I)
    if m:
        subject = m.group(1).lower()
        action = m.group(3)
        # Reframe from "The dashboard should display X" → "The system shall display X via the dashboard"
        if subject not in ("system",):
            return f"The system shall {action.strip()} via the {subject}"

    # Generic: wrap in "The system shall"
    # Remove any existing subject prefix
    text_clean = re.sub(r"^(the|this|a|an)\s+(\w+)\s+(shall|must|should|will|can)\s*",
                        "", text, flags=re.I).strip()
    if text_clean:
        return f"The system shall {text_clean[0].lower()}{text_clean[1:]}"

    return text


# ═══════════════════════════════════════════════════════════════════════════════
# NFR CATEGORIZATION (keyword-based, used for both fallback and validation)
# ═══════════════════════════════════════════════════════════════════════════════

_NFR_CATEGORIES = {
    "Performance":  {"performance", "response time", "latency", "throughput", "uptime",
                     "load", "concurrent", "benchmark", "speed", "millisecond",
                     "within 2 seconds", "within 500 milliseconds", "not exceeding"},
    "Security":     {"security", "encrypt", "auth", "privacy", "compliance", "audit",
                     "certificate", "access control", "vulnerability", "password", "token",
                     "aes-256", "tls", "oauth", "data protection"},
    "Usability":    {"usability", "wcag", "accessible", "accessibility", "clicks or fewer",
                     "user interface", "ux", "ui guideline", "navigation", "training"},
    "Scalability":  {"scalable", "scalability", "horizontal", "vertical", "cluster",
                     "distributed", "elastic", "auto-scaling", "capacity",
                     "concurrent users", "5,000"},
    "Reliability":  {"reliability", "availability", "fault", "recovery", "backup",
                     "redundancy", "failover", "uptime", "downtime", "resilience",
                     "99.9%", "maintainability"},
}


def _categorize_nfr(sentence: str) -> str:
    lo = sentence.lower()
    scores = {}
    for cat, keywords in _NFR_CATEGORIES.items():
        scores[cat] = sum(1 for k in keywords if k in lo)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "Performance"


# ═══════════════════════════════════════════════════════════════════════════════
# STIMULUS/RESPONSE GENERATION (context-aware, not generic)
# ═══════════════════════════════════════════════════════════════════════════════

def _generate_stimulus_response(text: str, original: str) -> str | None:
    """
    Generate a Stimulus/Response flow ONLY when the FR describes
    a user-facing action. Returns None for background/internal operations.
    """
    lo = text.lower()

    # Skip internal/background operations — no user interaction
    internal_patterns = ["shall log", "shall store internally", "shall run a background",
                         "shall monitor", "shall schedule", "shall batch",
                         "shall maintain", "shall cache", "shall index"]
    if any(p in lo for p in internal_patterns):
        return None

    # Context-specific flows based on the action described
    if any(k in lo for k in ["upload", "import"]) and ("file" in lo or "document" in lo):
        return (
            "Stimulus: The user selects one or more files via the upload interface and clicks 'Upload'. "
            "Response: The system validates the file type and size (max 10 MB), saves the file to the server, "
            "stores the submission, and displays a success notification."
        )

    if any(k in lo for k in ["login", "sign in", "authenticate"]) and "user" in lo:
        return (
            "Stimulus: The user enters their email and password on the login page and clicks 'Sign In'. "
            "Response: The system verifies the credentials against the user database, creates an authenticated "
            "session token, and redirects the user to the main landing page or home screen. If credentials are invalid, the system "
            "displays an error message and increments the failed-attempt counter."
        )

    if any(k in lo for k in ["search", "filter", "query"]):
        return (
            "Stimulus: The user enters search keywords or selects filter criteria and submits the query. "
            "Response: The system queries the data store, applies the specified filters, and returns matching "
            "results in a paginated list within 2 seconds. The user can sort results or refine the search."
        )

    if any(k in lo for k in ["generate", "export"]) and any(k in lo for k in ["report", "document"]):
        return (
            "Stimulus: The user selects the output format and requests generation or export. "
            "Response: The system compiles the relevant data according to the user's selection, "
            "generates the output in the requested format, and presents it for download or in-browser preview."
        )

    if any(k in lo for k in ["display", "show", "view", "dashboard"]):
        return (
            "Stimulus: The user navigates to the relevant page or section. "
            "Response: The system retrieves the current data from the backend, renders it in the UI "
            "with proper formatting and visual indicators, and enables interactive elements."
        )

    if any(k in lo for k in ["create", "add", "register"]) and "user" not in lo:
        return (
            "Stimulus: The user fills in the required fields in the creation form and clicks 'Save'. "
            "Response: The system validates all input fields against defined rules, persists the new record "
            "to the data store, and displays a confirmation message with the created entry."
        )

    if any(k in lo for k in ["update", "edit", "modify"]):
        return (
            "Stimulus: The user selects an existing record, modifies the desired fields, and clicks 'Update'. "
            "Response: The system validates the changes, updates the record in the data store, and displays "
            "a confirmation with the updated values."
        )

    if any(k in lo for k in ["delete", "remove"]):
        return (
            "Stimulus: The user selects the record to delete and confirms the action in the dialog. "
            "Response: The system permanently removes the record from the data store, updates the UI "
            "to reflect the deletion, and displays a success notification."
        )

    if any(k in lo for k in ["notify", "alert", "email", "notification"]):
        return (
            "Stimulus: A triggering event occurs (e.g., status change, threshold breach). "
            "Response: The system evaluates notification rules, sends the alert via the configured "
            "channel (email, in-app, or push), and logs the delivery status."
        )

    if any(k in lo for k in ["allow the user", "enable the user", "user to"]):
        return (
            "Stimulus: The user initiates the action through the system interface. "
            "Response: The system processes the request, validates inputs, executes the operation, "
            "and provides visual feedback confirming the outcome."
        )

    # No user-facing action identified — omit stimulus/response
    return None


# ═══════════════════════════════════════════════════════════════════════════════
# RULE-BASED FALLBACK REFINER
# ═══════════════════════════════════════════════════════════════════════════════

def _fallback_refine(requirements: list, meta: dict) -> list:
    """
    Rule-based fallback refinement when the LLM is unavailable.
    Rewrites vague terms, reclassifies FR/NFR with intent, assigns categories,
    generates S/R flows, and preserves traceability.
    """
    refined = []

    for req in requirements:
        original_sentence = req.get("original_sentence", req.get("sentence", ""))
        sentence = req.get("sentence", "")

        # 1. Replace vague terms
        text = _replace_vague_terms(sentence)

        # 2. Remove duplicate phrases caused by replacement
        text = _remove_duplicate_phrases(text)

        # 3. Ensure IEEE format
        text = _ensure_ieee_format(text)

        # 4. Intent-based classification
        req_type = _intent_classify(text, req.get("type", "FR"))

        entry = {
            "original": original_sentence,
            "text": text,
            "type": req_type,
        }

        if req_type == "FR":
            sr = _generate_stimulus_response(text, original_sentence)
            if sr:
                entry["stimulus_response"] = sr
            # If no S/R is generated, we intentionally omit it
        else:
            entry["category"] = _categorize_nfr(text)

        refined.append(entry)

    return refined
