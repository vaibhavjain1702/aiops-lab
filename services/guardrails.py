"""
Guardrails Service — Input and Output validation pipeline
Provides centralized guardrail logic for the AI DevOps Assistant.

Input Guards:
  - Empty question rejection
  - Length limit (>2000 chars)
  - Prompt injection detection
  - Out-of-scope detection

Output Guards:
  - Empty output rejection
  - Internal error string detection
  - Groundedness check (unsupported claims when RAG is active)
"""

import re
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("guardrails")

# --- Configuration ---
MAX_INPUT_LENGTH = 2000

# Prompt injection patterns
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"ignore\s+(all\s+)?above\s+instructions",
    r"disregard\s+(all\s+)?previous",
    r"forget\s+(all\s+)?previous",
    r"you\s+are\s+now\s+(?:a|an)\s+(?:evil|malicious|unrestricted)",
    r"act\s+as\s+(?:a|an)\s+(?:evil|malicious|unrestricted|jailbroken)",
    r"system\s*prompt",
    r"reveal\s+(?:your|the)\s+(?:system|internal|hidden)\s+(?:prompt|instructions)",
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode\s+enabled",
    r"bypass\s+(?:all\s+)?(?:safety|security|restrictions|filters)",
    r"pretend\s+(?:you\s+)?(?:are|have)\s+no\s+(?:rules|restrictions|limits)",
    r"override\s+(?:safety|security|content)\s+(?:policy|filter|restrictions)",
    r"(?:print|show|display|output)\s+(?:your|the)\s+(?:system|initial|original)\s+(?:prompt|message|instructions)",
]

# Internal error patterns that should never reach the user
ERROR_PATTERNS = [
    r"traceback\s*\(most\s+recent\s+call\s+last\)",
    r"internal\s+server\s+error",
    r"NoneType\s+object",
    r"KeyError\s*:",
    r"IndexError\s*:",
    r"AttributeError\s*:",
    r"TypeError\s*:",
    r"ValueError\s*:",
    r"ModuleNotFoundError\s*:",
    r"ImportError\s*:",
    r"ConnectionRefusedError",
    r"ConnectionError",
    r"FileNotFoundError",
    r"Exception\s*:",
]

# DevOps-related scope keywords
SCOPE_KEYWORDS = [
    "docker", "kubernetes", "k8s", "devops", "ci/cd", "pipeline",
    "deployment", "container", "microservice", "monitoring", "prometheus",
    "grafana", "jenkins", "git", "ansible", "terraform", "helm",
    "api", "fastapi", "flask", "rest", "endpoint", "service",
    "database", "redis", "nginx", "load balancer", "proxy",
    "linux", "ubuntu", "server", "cloud", "aws", "azure", "gcp",
    "python", "code", "function", "class", "module", "import",
    "bug", "error", "debug", "fix", "test", "unit test",
    "rag", "retrieval", "embedding", "vector", "chromadb", "ollama",
    "llm", "model", "inference", "generation", "token",
    "security", "ssl", "tls", "authentication", "authorization",
    "log", "logging", "trace", "metric", "alert",
    "yaml", "json", "config", "environment", "variable",
    "network", "port", "dns", "http", "https",
    "refactor", "optimize", "performance", "latency", "throughput",
    "orchestration", "compose", "dockerfile", "image", "registry",
    "ingestion", "chunking", "similarity", "cosine",
]


class GuardrailResult:
    """Result of a guardrail check."""
    def __init__(self, passed: bool, rule: str, message: str, stage: str = "input"):
        self.passed = passed
        self.rule = rule
        self.message = message
        self.stage = stage
    
    def to_dict(self):
        return {
            "passed": self.passed,
            "rule": self.rule,
            "message": self.message,
            "stage": self.stage
        }


# ========================
#  INPUT GUARDRAILS
# ========================

def check_empty_input(question: str) -> GuardrailResult:
    """Reject empty or whitespace-only questions."""
    if not question or not question.strip():
        return GuardrailResult(
            passed=False,
            rule="empty_input",
            message="Question cannot be empty. Please provide a valid question.",
            stage="input"
        )
    return GuardrailResult(passed=True, rule="empty_input", message="OK", stage="input")


def check_input_length(question: str, max_length: int = MAX_INPUT_LENGTH) -> GuardrailResult:
    """Reject questions exceeding maximum length."""
    if len(question) > max_length:
        return GuardrailResult(
            passed=False,
            rule="input_length",
            message=f"Question exceeds maximum length of {max_length} characters (received {len(question)}). Please shorten your question.",
            stage="input"
        )
    return GuardrailResult(passed=True, rule="input_length", message="OK", stage="input")


def check_prompt_injection(question: str) -> GuardrailResult:
    """Detect prompt injection attempts."""
    lower_q = question.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower_q):
            return GuardrailResult(
                passed=False,
                rule="prompt_injection",
                message="Your request appears to contain a prompt injection attempt. This type of request is not allowed.",
                stage="input"
            )
    return GuardrailResult(passed=True, rule="prompt_injection", message="OK", stage="input")


def check_scope(question: str) -> GuardrailResult:
    """Check if the question is within the application's intended scope."""
    lower_q = question.lower()
    # Check if any scope keyword appears in the question
    is_in_scope = any(keyword in lower_q for keyword in SCOPE_KEYWORDS)
    
    # Also allow general technical questions (short questions, how-to, what-is)
    general_patterns = [
        r"^(what|how|why|when|where|which|can|does|is|are|explain|describe|list|show|compare|difference)",
        r"(help|tutorial|guide|example|best practice)",
    ]
    is_general_tech = any(re.search(p, lower_q) for p in general_patterns)
    
    if not is_in_scope and not is_general_tech:
        return GuardrailResult(
            passed=False,
            rule="scope",
            message="This question appears to be outside the scope of the DevOps Technical Support Assistant. Please ask questions related to DevOps, Docker, APIs, RAG, LLMs, or software engineering.",
            stage="input"
        )
    return GuardrailResult(passed=True, rule="scope", message="OK", stage="input")


def validate_input(question: str) -> GuardrailResult:
    """Run all input guardrails. Returns first failure, or a pass result."""
    checks = [
        check_empty_input(question),
        check_input_length(question),
        check_prompt_injection(question),
        check_scope(question),
    ]
    
    for check in checks:
        if not check.passed:
            logger.warning(f"Input guardrail triggered: {check.rule} — {check.message}")
            return check
    
    return GuardrailResult(passed=True, rule="all_input", message="All input checks passed", stage="input")


# ========================
#  OUTPUT GUARDRAILS
# ========================

def check_empty_output(answer: str) -> GuardrailResult:
    """Reject empty or whitespace-only outputs."""
    if not answer or not answer.strip():
        return GuardrailResult(
            passed=False,
            rule="empty_output",
            message="The model produced an empty response. Please try again or rephrase your question.",
            stage="output"
        )
    return GuardrailResult(passed=True, rule="empty_output", message="OK", stage="output")


def check_error_leakage(answer: str) -> GuardrailResult:
    """Detect leaked internal error strings in the output."""
    for pattern in ERROR_PATTERNS:
        if re.search(pattern, answer, re.IGNORECASE):
            return GuardrailResult(
                passed=False,
                rule="error_leakage",
                message="The response contains internal error information that should not be exposed. The response has been blocked.",
                stage="output"
            )
    return GuardrailResult(passed=True, rule="error_leakage", message="OK", stage="output")


def check_groundedness(answer: str, context: Optional[str] = None, rag_enabled: bool = False) -> GuardrailResult:
    """
    Basic groundedness check: when RAG is enabled, flag responses
    that make strong claims without referencing the provided context.
    This is a heuristic proxy, NOT a perfect factual verifier.
    """
    if not rag_enabled or not context:
        return GuardrailResult(passed=True, rule="groundedness", message="RAG not active, skipping groundedness check", stage="output")
    
    # Split answer into sentences
    sentences = re.split(r'[.!?]+', answer)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    
    if not sentences:
        return GuardrailResult(passed=True, rule="groundedness", message="OK", stage="output")
    
    context_lower = context.lower()
    unsupported_count = 0
    total_claims = len(sentences)
    
    for sentence in sentences:
        sentence_lower = sentence.lower()
        # Check if key words from the sentence appear in the context
        words = [w for w in sentence_lower.split() if len(w) > 4]
        if words:
            matching_words = sum(1 for w in words if w in context_lower)
            coverage = matching_words / len(words) if words else 0
            if coverage < 0.2:  # Less than 20% word overlap
                unsupported_count += 1
    
    unsupported_rate = unsupported_count / total_claims if total_claims > 0 else 0
    
    if unsupported_rate > 0.7:  # More than 70% of claims are unsupported
        return GuardrailResult(
            passed=False,
            rule="groundedness",
            message=f"The response appears to contain a high rate of unsupported claims ({unsupported_rate:.0%}). The answer may not be grounded in the retrieved context. (Note: this is a heuristic check.)",
            stage="output"
        )
    
    return GuardrailResult(
        passed=True,
        rule="groundedness",
        message=f"Groundedness check passed (unsupported rate: {unsupported_rate:.0%}). Note: this is a heuristic proxy metric.",
        stage="output"
    )


def validate_output(answer: str, context: Optional[str] = None, rag_enabled: bool = False) -> GuardrailResult:
    """Run all output guardrails. Returns first failure, or a pass result."""
    checks = [
        check_empty_output(answer),
        check_error_leakage(answer),
        check_groundedness(answer, context, rag_enabled),
    ]
    
    for check in checks:
        if not check.passed:
            logger.warning(f"Output guardrail triggered: {check.rule} — {check.message}")
            return check
    
    return GuardrailResult(passed=True, rule="all_output", message="All output checks passed", stage="output")


# ========================
#  GUARDRAIL SUMMARY
# ========================

def get_guardrail_info() -> dict:
    """Return information about all available guardrails."""
    return {
        "input_guardrails": [
            {"rule": "empty_input", "description": "Rejects empty or whitespace-only questions"},
            {"rule": "input_length", "description": f"Rejects questions exceeding {MAX_INPUT_LENGTH} characters"},
            {"rule": "prompt_injection", "description": "Detects prompt injection attempts (ignore-previous, system-prompt, jailbreak, etc.)"},
            {"rule": "scope", "description": "Checks if the question is within the DevOps/technical scope"},
        ],
        "output_guardrails": [
            {"rule": "empty_output", "description": "Rejects empty model responses"},
            {"rule": "error_leakage", "description": "Detects leaked internal error strings (tracebacks, exceptions)"},
            {"rule": "groundedness", "description": "Heuristic check for unsupported claims when RAG is active (proxy metric)"},
        ],
        "total_guards": 7,
        "max_input_length": MAX_INPUT_LENGTH,
        "injection_patterns_count": len(INJECTION_PATTERNS),
        "scope_keywords_count": len(SCOPE_KEYWORDS),
    }
