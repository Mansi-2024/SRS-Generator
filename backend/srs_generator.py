"""
srs_generator.py — LLM Call 2: SRS Section Prose Generation.

Takes ALREADY-REFINED requirements + project metadata and generates
professional prose for each IEEE 830 SRS section.

This module does NOT refine requirements — that's handled by
requirement_refiner.py (LLM Call 1).

Falls back to heuristic text generation if the API key is not set.
"""

import os
import json

# ─── Lazy import for google-genai ──────────────────────────────────────────────
_genai_client = None

_TOOL_ONLY_KEYWORDS = {
    "nlp", "natural language processing", "requirement extraction", "extract requirement",
    "quality scoring", "quality assessment", "ambiguity detection", "analysis dashboard",
    "srs generation", "generate srs", "analyzes documents", "analyze documents",
}


def _mentions_tool_capability(text: str) -> bool:
    lo = (text or "").lower()
    return any(k in lo for k in _TOOL_ONLY_KEYWORDS)


def _get_client():
    """Return a google.genai Client, creating it lazily on first use."""
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


# ─── LLM Call 2 Prompt ───────────────────────────────────────────────────────

_SRS_PROSE_PROMPT = """You are a senior technical writer generating IEEE 830 SRS section prose.

You are given ALREADY REFINED requirements (they are clean, measurable, testable).
Your job is to generate ONLY the section prose — NOT to refine requirements.

SYSTEM BOUNDARY (MANDATORY):
- The SRS describes the TARGET system from the requirements (e.g., SmartStudy, a CRM, etc.).
- Describe ONLY features explicitly present in the requirements.
- Do NOT add: NLP processing, requirement extraction, SRS generation, quality scoring, analysis dashboards, or any analysis-tool capabilities.
- Assume the analysis tool that produced this SRS does not exist in the described system.

Generate a JSON object with these keys (all values are strings of professional prose):
{
  "product_scope": "Context-aware description of what the TARGET system does. Be specific about the actual features in the requirements. Do NOT use generic descriptions.",
  "product_perspective": "How this system fits in the broader landscape.",
  "product_functions": "Bullet-point summary of major system capabilities from the requirements. Summarize — do NOT copy requirements.",
  "user_classes": "Description of user types (Students, Administrators, etc.) with characteristics.",
  "operating_environment": "Web browser, mobile, backend server, database details.",
  "design_constraints": "Technical and regulatory constraints.",
  "user_documentation": "Documentation deliverables.",
  "assumptions_dependencies": "Assumptions and external dependencies.",
  "user_interfaces": "UI description with accessibility standards. Describe interfaces implied by the requirements — NOT analysis-tool UI.",
  "hardware_interfaces": "Client and server hardware requirements.",
  "software_interfaces": "External software integrations mentioned in or implied by the requirements.",
  "communications_interfaces": "Protocols and data transfer standards.",
  "other_requirements": "Any additional requirements not covered above."
}

RULES:
- Be specific to THIS project — use the project name and actual features from the requirements.
- No placeholder text like "<Describe...>" is allowed.
- No vague language. Everything must be concrete.
- Write in professional IEEE SRS tone.
- Return ONLY valid JSON, no markdown fences.
"""


def _build_prose_prompt(refined_reqs: list, meta: dict) -> str:
    project = meta.get("project_name", "<Project>")
    author = meta.get("author", "<author>")
    org = meta.get("organization", "<organization>")

    frs = [r for r in refined_reqs if r.get("type") == "FR"]
    nfrs = [r for r in refined_reqs if r.get("type") == "NFR"]

    fr_summary = "\n".join(f"  {r['id']}: {r['text']}" for r in frs)
    nfr_summary = "\n".join(f"  {r['id']} [{r.get('category', 'General')}]: {r['text']}" for r in nfrs)

    return (
        f"PROJECT: {project}\n"
        f"AUTHOR: {author}\n"
        f"ORGANIZATION: {org}\n"
        f"TOTAL: {len(refined_reqs)} requirements ({len(frs)} FR, {len(nfrs)} NFR)\n\n"
        f"FUNCTIONAL REQUIREMENTS:\n{fr_summary or '  (none)'}\n\n"
        f"NON-FUNCTIONAL REQUIREMENTS:\n{nfr_summary or '  (none)'}\n\n"
        f"Generate the SRS section prose as JSON."
    )


def generate_srs_content(refined_reqs: list, meta: dict) -> dict:
    """
    LLM Call 2: Generate section prose for the SRS.

    Input: already-refined requirements from requirement_refiner.
    Returns a dict of section keys → prose strings.
    Returns None on failure (caller should use fallback).
    """
    client = _get_client()
    if client is None:
        return None

    prompt = _build_prose_prompt(refined_reqs, meta)

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": [{"text": _SRS_PROSE_PROMPT + "\n\n" + prompt}]}],
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            raw = "\n".join(lines)
        result = json.loads(raw)
        return result
    except Exception as e:
        print(f"[srs_generator] LLM prose generation failed: {e}")
        return None


# ─── Fallback Heuristic Generation ───────────────────────────────────────────

def _build_software_interfaces(project: str, all_text: str) -> str:
    """Build requirements-driven software interfaces; no ARAQAT-specific integrations."""
    parts = [f"The {project} system interacts with the following software components:"]
    if any(k in all_text for k in ["database", "db", "sql", "store", "record"]):
        parts.append("  - Database engine (e.g., PostgreSQL, MySQL, or MongoDB) for persistent storage.")
    if any(k in all_text for k in ["email", "smtp", "notification", "alert"]):
        parts.append("  - Email service provider (e.g., SendGrid, AWS SES) for outbound notifications.")
    if any(k in all_text for k in ["api", "rest", "integration", "third-party", "external"]):
        parts.append("  - External REST APIs for third-party data or service integration.")
    if any(k in all_text for k in ["payment", "billing", "transaction"]):
        parts.append("  - Payment gateway (e.g., Stripe, PayPal) for financial transactions.")
    if len(parts) == 1:
        parts.append("  - Standard OS libraries and runtime environment.")
    return "\n".join(parts)


def generate_fallback_content(refined_reqs: list, meta: dict) -> dict:
    """
    Generate section prose heuristically when the LLM is unavailable.
    Input: already-refined requirements from requirement_refiner.
    """
    project = meta.get("project_name", "<Project>")
    frs = [r for r in refined_reqs if r.get("type") == "FR"]
    nfrs = [r for r in refined_reqs if r.get("type") == "NFR"]
    cleaned_texts = [r.get("text", "") for r in refined_reqs if not _mentions_tool_capability(r.get("text", ""))]
    all_text = " ".join(t.lower() for t in cleaned_texts)

    # Theme detection
    themes = []
    theme_map = [
        (["user", "login", "register", "account", "authentication"], "user account management"),
        (["report", "dashboard", "analytics", "chart"], "data reporting and analytics"),
        (["payment", "invoice", "billing", "transaction"], "payment processing"),
        (["search", "filter", "query", "browse"], "search and discovery"),
        (["notification", "alert", "email", "message"], "user notifications"),
        (["upload", "download", "file", "document", "export"], "file and document management"),
        (["admin", "manage", "configure", "role", "permission"], "administration and configuration"),
        (["database", "store", "record", "save"], "data storage and retrieval"),
        (["api", "integration", "service", "third-party"], "external system integration"),
        (["security", "encrypt", "access control"], "security and access control"),
    ]
    for keywords, label in theme_map:
        if any(k in all_text for k in keywords):
            themes.append(label)

    theme_str = ", ".join(themes[:4]) if themes else "core operational capabilities"

    # Product functions — derive from actual FR text only (no ARAQAT-specific features)
    func_bullets = []
    if any(k in all_text for k in ["login", "auth", "user", "account", "register"]):
        func_bullets.append("User authentication and account management")
    if any(k in all_text for k in ["upload", "import", "file"]):
        func_bullets.append("File and document management")
    if any(k in all_text for k in ["search", "filter", "query", "browse"]):
        func_bullets.append("Search and discovery")
    if any(k in all_text for k in ["report", "analytics", "chart"]):
        func_bullets.append("Data reporting and analytics")
    if any(k in all_text for k in ["payment", "invoice", "billing", "transaction"]):
        func_bullets.append("Payment processing")
    if any(k in all_text for k in ["notification", "alert", "email", "message"]):
        func_bullets.append("User notifications")
    if any(k in all_text for k in ["admin", "manage", "configure", "role", "permission"]):
        func_bullets.append("Administration and configuration")
    if not func_bullets:
        for r in frs[:5]:
            txt = r.get("text", "")
            if not _mentions_tool_capability(txt):
                func_bullets.append(txt[:80])
    if not func_bullets:
        func_bullets.append("Core capabilities explicitly specified in the requirements")
    functions_str = "\n".join(f"  - {b}" for b in func_bullets)

    # User classes
    user_parts = ["End Users: Primary users who interact with the system's core features through the web interface."]
    if any(k in all_text for k in ["admin", "administrator", "manage", "role", "permission"]):
        user_parts.append("Administrators: System administrators responsible for managing users, configuration, and access control.")
    if any(k in all_text for k in ["student", "learner"]):
        user_parts.append("Students: Primary end-users who engage with the system for academic purposes.")

    # Environment
    env_parts = ["Web Browser: Chrome 110+, Firefox 110+, Safari 16+, Edge 110+."]
    if any(k in all_text for k in ["mobile", "ios", "android"]):
        env_parts.append("Mobile: iOS 14+ and Android 10+.")
    env_parts.append("Server: Backend application server (RESTful API) in cloud or on-premise.")
    if any(k in all_text for k in ["database", "db", "store", "sql", "data"]):
        env_parts.append("Database: Relational or document-oriented database for persistent storage.")
    env_parts.append("Network: Stable internet connectivity required (minimum 5 Mbps).")

    return {
        "product_scope": (
            f"{project} is an intelligent software system designed to support {theme_str}. "
            f"The system provides {len(frs)} refined functional capabilities and enforces "
            f"{len(nfrs)} non-functional quality attributes as specified in this document."
        ),
        "product_perspective": (
            f"{project} operates as a standalone web-based application. "
            f"This SRS covers {len(refined_reqs)} refined requirements "
            f"({len(frs)} FR, {len(nfrs)} NFR). See Sections 4 and 5 for details."
        ),
        "product_functions": f"Key capabilities of {project}:\n{functions_str}",
        "user_classes": "\n".join(user_parts),
        "operating_environment": "\n".join(f"  - {p}" for p in env_parts),
        "design_constraints": (
            "- The system must comply with IEEE 830-1998 specification structure.\n"
            "- All inter-system communication must use HTTPS with TLS 1.2 or higher.\n"
            "- All requirements must be testable and measurable before implementation."
        ),
        "user_documentation": (
            f"- {project} User Manual\n"
            f"- System Administrator Guide\n"
            f"- API Reference Documentation\n"
            f"- Release Notes"
        ),
        "assumptions_dependencies": (
            "- The target deployment environment meets the specifications in Section 2.4.\n"
            "- All requirements have been refined and validated before SRS generation."
        ),
        "user_interfaces": (
            f"The {project} system shall provide a responsive graphical user interface "
            f"accessible via web browser, compliant with WCAG 2.1 AA accessibility guidelines. "
            f"The interface includes navigation, forms for data entry, and displays for viewing data "
            f"as specified in the requirements."
        ),
        "hardware_interfaces": (
            "Client hardware requires a device with a modern web browser and minimum 2 GB RAM. "
            "Server hardware shall support at least 100 concurrent user sessions."
        ),
        "software_interfaces": _build_software_interfaces(project, all_text),
        "communications_interfaces": (
            "- HTTPS / TLS 1.2+ for all client-server data transfer.\n"
            "- RESTful JSON APIs for frontend-backend communication.\n"
            "- API rate limiting: maximum 60 requests per minute per user."
        ),
        "other_requirements": (
            "Database: Data persistence requirements are detailed in Section 3.3.\n"
            "Legal: The system shall comply with applicable data protection laws."
        ),
    }
