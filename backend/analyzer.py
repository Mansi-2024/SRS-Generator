"""
analyzer.py
Core NLP module for Automated Requirements Analysis.

Pipeline:
  1. PREPROCESS raw text (merge broken numbered lines, normalize)
  2. EXTRACT requirements (regex-first for numbered docs, spaCy fallback)
  3. VALIDATE extracted sentences (reject fragments, standalone numbers)
  4. CLASSIFY (FR/NFR) and detect vagueness
  5. SCORE quality
"""

import re
import spacy

# Load the spaCy English model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None

# -----------------------------------------------------------------------
# Keyword lexicons
# -----------------------------------------------------------------------

FR_KEYWORDS = {
    "shall", "must", "should", "will", "can", "allow", "enable", "provide",
    "support", "display", "calculate", "process", "store", "retrieve",
    "generate", "send", "receive", "authenticate", "authorize", "validate",
    "upload", "download", "export", "import", "search", "filter", "sort",
    "create", "update", "delete", "read", "login", "logout", "register",
    "notify", "report", "manage", "handle", "execute",
}

NFR_KEYWORDS = {
    "performance", "security", "reliability", "availability", "scalability",
    "maintainability", "usability", "accessibility", "portability",
    "compatibility", "efficiency", "robustness", "recoverability",
    "response time", "throughput", "latency", "uptime", "downtime",
    "concurrent", "encrypt", "backup", "audit", "compliance", "standard",
    "protocol", "platform", "browser", "device", "resolution", "load",
    "stress", "test", "deploy", "monitor", "log", "alert",
}

VAGUE_WORDS = {
    "fast", "quickly", "slow", "easy", "simple", "user-friendly", "friendly",
    "intuitive", "modern", "beautiful", "nice", "good", "bad", "efficiently",
    "seamlessly", "robust", "flexible", "scalable", "adequate", "sufficient",
    "appropriate", "reasonable", "minimal", "maximum", "optimal", "better",
    "improve", "enhanced", "advanced", "high", "low", "quick", "rapid",
    "real-time", "near real-time", "soon", "often", "sometimes", "usually",
    "generally", "typically", "normally", "complex", "simple", "large",
    "small", "significant", "important", "critical", "various", "several",
    "some", "many", "few", "numerous", "multiple",
}

# Patterns that strongly indicate a requirement statement
REQUIREMENT_PATTERNS = [
    re.compile(r"\b(shall|must|should|will|can)\b", re.IGNORECASE),
    re.compile(r"\b(the system|the application|the tool|the platform|the user|the admin)\b", re.IGNORECASE),
    re.compile(r"\b(is able to|is required to|needs to|has to|be able to)\b", re.IGNORECASE),
]


# -----------------------------------------------------------------------
# STEP 1: TEXT PREPROCESSING
# -----------------------------------------------------------------------

# Matches a standalone number like "1." or "2)" or "3-" on its own line
_STANDALONE_NUM_RE = re.compile(r"^\s*(\d{1,3})\s*[.)\-]\s*$", re.MULTILINE)

# Matches a numbered line with content: "1. The system shall..."
_NUMBERED_LINE_RE = re.compile(r"^\s*\d{1,3}\s*[.)\-]\s+\S", re.MULTILINE)

# Matches "1.\n" followed by text on the next line (broken numbered requirement)
_BROKEN_NUM_RE = re.compile(r"(\d{1,3})\s*[.)\-]\s*\n\s*(\S)", re.MULTILINE)


def preprocess_text(text: str) -> str:
    """
    PREPROCESSING LAYER - runs BEFORE any NLP processing.

    Fixes:
    1. Merges broken numbered lines: "1.\nThe system..." -> "1. The system..."
    2. Removes standalone empty numbered entries that have no following content
    3. Normalizes whitespace and line endings
    """
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # LINE-BY-LINE MERGE STRATEGY:
    # Walk through lines. If a line is just a number (e.g. "1."), peek ahead:
    #   - If the next non-empty line has actual content -> merge them
    #   - If the next line is also just a number or empty -> drop the standalone number
    lines = text.split("\n")
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Check if this line is a standalone number: "1.", "2)", "3-", etc.
        if re.match(r"^\d{1,3}\s*[.)\-]\s*$", line):
            # Look ahead for the next non-empty line
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines):
                next_line = lines[j].strip()
                # Is the next non-empty line also just a number? -> drop current
                if re.match(r"^\d{1,3}\s*[.)\-]\s*$", next_line):
                    i += 1
                    continue
                # Next line has real content -> merge
                num = re.match(r"^(\d{1,3})\s*[.)\-]\s*$", line).group(1)
                merged.append(f"{num}. {next_line}")
                i = j + 1
                continue
            else:
                # No more lines after this standalone number -> drop it
                i += 1
                continue

        merged.append(lines[i])
        i += 1

    text = "\n".join(merged)

    # Normalize multiple blank lines to single
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize multiple spaces
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


# -----------------------------------------------------------------------
# STEP 2: REQUIREMENT EXTRACTION (regex-first, spaCy fallback)
# -----------------------------------------------------------------------

# Regex to extract numbered requirements: "1. content here"
_EXTRACT_NUMBERED_RE = re.compile(
    r"^\s*(\d{1,3})\s*[.)\-]\s+(.+?)(?=\n\s*\d{1,3}\s*[.)\-]\s+|\n\s*\n|\Z)",
    re.MULTILINE | re.DOTALL
)

# Lettered: "a. content" or "a) content"
_EXTRACT_LETTERED_RE = re.compile(
    r"^\s*[a-zA-Z]\s*[.)\-]\s+(.+?)(?=\n\s*[a-zA-Z]\s*[.)\-]\s+|\n\s*\n|\Z)",
    re.MULTILINE | re.DOTALL
)


def extract_sentences(text: str) -> list[str]:
    """
    EXTRACTION LAYER - uses regex-first strategy.

    Strategy:
    1. Try regex extraction for numbered requirements (most common format)
    2. Try regex extraction for lettered requirements
    3. Fall back to spaCy/NLP sentence splitting if no numbered format detected

    This prevents spaCy from splitting "1. The system shall..." incorrectly.
    """
    preprocessed = preprocess_text(text)

    # Strategy 1: Try numbered requirement extraction
    numbered_matches = _EXTRACT_NUMBERED_RE.findall(preprocessed)
    if numbered_matches:
        sentences = []
        for num, content in numbered_matches:
            # Clean up multi-line content within a single requirement
            clean = re.sub(r"\s+", " ", content).strip()
            if clean:
                sentences.append(clean)
        if sentences:
            return sentences

    # Strategy 2: Try lettered requirement extraction
    lettered_matches = _EXTRACT_LETTERED_RE.findall(preprocessed)
    if lettered_matches:
        sentences = []
        for content in lettered_matches:
            clean = re.sub(r"\s+", " ", content).strip()
            if clean:
                sentences.append(clean)
        if sentences:
            return sentences

    # Strategy 3: Fallback to NLP-based sentence splitting
    return _nlp_split_sentences(preprocessed)


def _nlp_split_sentences(text: str) -> list[str]:
    """Fallback: use spaCy or regex to split text into sentences."""
    if nlp:
        doc = nlp(text)
        sentences = []
        for sent in doc.sents:
            s = sent.text.strip()
            if s:
                # Post-process: if spaCy produced a standalone number, skip it
                if re.match(r"^\d{1,3}\s*[.)\-]?\s*$", s):
                    continue
                sentences.append(s)
        return sentences
    else:
        # Rudimentary splitter as fallback
        raw = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in raw if s.strip()]


# -----------------------------------------------------------------------
# STEP 3: VALIDATION FILTER
# -----------------------------------------------------------------------

def validate_sentence(sentence: str) -> str | None:
    """
    Validate a sentence before classification.

    Returns:
      None        - valid sentence, proceed
      str         - reason for rejection (flag message)
    """
    stripped = sentence.strip()

    # Reject empty strings
    if not stripped:
        return "Empty input"

    # Reject standalone numbers: "1.", "2)", "3", etc.
    if re.match(r"^\d{1,3}\s*[.)\-]?\s*$", stripped):
        return "Standalone number - not a requirement"

    # Reject very short fragments (< 5 characters)
    if len(stripped) < 5:
        return "Fragment too short (< 5 characters)"

    # Reject lone punctuation or symbols
    if re.match(r"^[^a-zA-Z]*$", stripped):
        return "No alphabetic content"

    return None


# -----------------------------------------------------------------------
# STEP 4: CLASSIFICATION + VAGUE DETECTION
# -----------------------------------------------------------------------

def is_requirement(sentence: str) -> bool:
    """Heuristic: determine if a sentence is a software requirement."""
    # Strip leading numbering for pattern matching
    clean = re.sub(r"^\d{1,3}\s*[.)\-]\s*", "", sentence).strip()
    if not clean:
        return False

    for pattern in REQUIREMENT_PATTERNS:
        if pattern.search(clean):
            return True

    # Check if it mentions system behaviour (for sentences without modal verbs)
    lower = clean.lower()
    if any(kw in lower for kw in ("system", "user", "application", "shall", "must", "should", "will")):
        return True

    return False


def classify_requirement(sentence: str) -> str:
    """
    Classify a requirement sentence as 'FR' or 'NFR'.

    Uses INTENT-BASED classification instead of raw keyword counting.
    The old approach failed because modal verbs (shall, must, should)
    are in FR_KEYWORDS and appear in EVERY requirement, so FR always won.

    New approach:
    1. Strip out modal verbs so they don't bias the score
    2. Check for NFR-indicator patterns (quality/constraint language)
    3. Check for FR-indicator patterns (action/behavior language)
    4. Default to FR only if no NFR signal is found
    """
    lower = sentence.lower()
    words = re.findall(r"[\w\-]+", lower)
    word_set = set(words)
    bigrams = {" ".join(words[i:i+2]) for i in range(len(words) - 1)}
    all_tokens = word_set | bigrams

    # Modal verbs that appear in BOTH FR and NFR — exclude from scoring
    MODAL_VERBS = {"shall", "must", "should", "will", "can", "may"}

    # NFR-specific indicators (quality attributes and constraints)
    NFR_INDICATORS = {
        "performance", "security", "reliability", "availability", "scalability",
        "maintainability", "usability", "accessibility", "portability",
        "compatibility", "efficiency", "robustness", "recoverability",
        "response time", "throughput", "latency", "uptime", "downtime",
        "concurrent", "encrypt", "encryption", "encrypted", "backup", "audit",
        "compliance", "standard", "protocol", "load", "stress",
        "monitor", "log", "alert", "fault", "tolerance", "failover",
        "redundancy", "resilience", "recovery", "password", "hash",
        "tls", "ssl", "https", "aes", "auth", "authentication", "authorization",
        "wcag", "accessible", "user-friendly", "intuitive",
        "scalable", "scale", "capacity", "peak load",
        "99.9%", "sla", "mttr", "mttf", "mtbf",
        "millisecond", "milliseconds", "seconds", "minutes",
    }

    # FR-specific indicators (system actions and behaviors) — excluding modal verbs
    FR_INDICATORS = {
        "allow", "enable", "provide", "support", "display", "calculate",
        "process", "store", "retrieve", "generate", "send", "receive",
        "validate", "upload", "download", "export", "import", "search",
        "filter", "sort", "create", "update", "delete", "read",
        "login", "logout", "register", "notify", "report", "manage",
        "handle", "execute", "authenticate", "authorize",
    }

    # Score without modal verbs
    nfr_score = len(all_tokens & NFR_INDICATORS)
    fr_score = len((all_tokens & FR_INDICATORS) - MODAL_VERBS)

    # Additional NFR pattern checks (regex-based for phrases)
    nfr_patterns = [
        r"\b\d+\s*(users?|connections?|requests?)\b",      # "5000 users"
        r"\b(response time|latency).*(second|millisecond|ms)\b",
        r"\b(encrypt|decrypt|hash)\b",
        r"\b(99\.\d+%|uptime|availability)\b",
        r"\bwithin\s+\d+\s*(second|millisecond|ms|minute)\b",
        r"\b(concurrent|simultaneous)\b",
        r"\b(scalab|reliab|usab|accessib|portab|maintainab)\w*\b",
        r"\b(backup|recover|failover|redundanc)\b",
        r"\b(wcag|ada compliance|accessibility)\b",
        r"\b(tls|ssl|aes|oauth|jwt|certificate)\b",
    ]
    for pat in nfr_patterns:
        if re.search(pat, lower):
            nfr_score += 1

    return "NFR" if nfr_score > fr_score else "FR"


def detect_vague_words(sentence: str) -> list[str]:
    """Return list of vague/ambiguous words found in the sentence."""
    lower = sentence.lower()
    words = re.findall(r"[\w\-]+", lower)
    bigrams = [" ".join(words[i:i+2]) for i in range(len(words) - 1)]
    all_tokens = words + bigrams
    found = [token for token in all_tokens if token in VAGUE_WORDS]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for w in found:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    return unique


# -----------------------------------------------------------------------
# STEP 5: QUALITY SCORING
# -----------------------------------------------------------------------

def compute_quality_score(requirements: list[dict]) -> dict:
    """
    Compute overall quality metrics and a score out of 100.
    """
    if not requirements:
        return {
            "total_requirements": 0,
            "fr_count": 0,
            "nfr_count": 0,
            "vague_count": 0,
            "fr_percentage": 0,
            "nfr_percentage": 0,
            "vague_percentage": 0,
            "quality_score": 0,
        }

    total = len(requirements)
    fr_count = sum(1 for r in requirements if r["type"] == "FR")
    nfr_count = sum(1 for r in requirements if r["type"] == "NFR")
    vague_count = sum(1 for r in requirements if r["vague_words"])

    score = 100
    score -= min(vague_count * 5, 50)
    if fr_count == 0:
        score -= 10
    if nfr_count == 0:
        score -= 10
    score = max(0, score)

    return {
        "total_requirements": total,
        "fr_count": fr_count,
        "nfr_count": nfr_count,
        "vague_count": vague_count,
        "fr_percentage": round(fr_count / total * 100, 1),
        "nfr_percentage": round(nfr_count / total * 100, 1),
        "vague_percentage": round(vague_count / total * 100, 1),
        "quality_score": score,
    }


# -----------------------------------------------------------------------
# FULL PIPELINE
# -----------------------------------------------------------------------

def analyze_document(text: str) -> dict:
    """
    Full analysis pipeline:
    Raw Text -> Preprocess -> Extract -> Validate -> Classify -> Score

    Returns a structured dict ready for JSON serialization.
    """
    # STEP 1+2: Preprocess and extract sentences
    sentences = extract_sentences(text)
    total_sentences = len(sentences)

    requirements = []
    non_requirements = []
    flagged = []

    for idx, sentence in enumerate(sentences):
        # STEP 3: Validate
        rejection = validate_sentence(sentence)
        if rejection:
            flagged.append({
                "id": idx + 1,
                "sentence": sentence,
                "flag": rejection,
            })
            continue

        # STEP 4: Classify
        if is_requirement(sentence):
            req_type = classify_requirement(sentence)
            vague = detect_vague_words(sentence)
            requirements.append({
                "id": idx + 1,
                "sentence": sentence,
                "type": req_type,
                "vague_words": vague,
                "is_vague": len(vague) > 0,
            })
        else:
            non_requirements.append({
                "id": idx + 1,
                "sentence": sentence,
            })

    # STEP 5: Score
    metrics = compute_quality_score(requirements)

    return {
        "total_sentences": total_sentences,
        "metrics": metrics,
        "requirements": requirements,
        "non_requirements": non_requirements,
        "flagged": flagged,
    }
