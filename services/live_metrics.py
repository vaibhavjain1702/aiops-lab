"""
Live Metrics Service — Targeted evaluation without rerunning full benchmark
Provides evaluation metrics calculation for live evaluation runs.
"""

import re
import time
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_metrics")


def calculate_correctness(answer: str, reference: str) -> dict:
    """
    Calculate correctness as reference-match score.
    Uses token overlap (F1) as a proxy metric.
    Limitation: Automated proxy — not human semantic truth.
    """
    if not reference or not answer:
        return {"score": 0.0, "method": "token_f1", "is_proxy": True}
    
    answer_tokens = set(answer.lower().split())
    reference_tokens = set(reference.lower().split())
    
    if not answer_tokens or not reference_tokens:
        return {"score": 0.0, "method": "token_f1", "is_proxy": True}
    
    common = answer_tokens & reference_tokens
    precision = len(common) / len(answer_tokens) if answer_tokens else 0
    recall = len(common) / len(reference_tokens) if reference_tokens else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "score": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "method": "token_f1",
        "is_proxy": True,
        "limitation": "Token overlap can miss semantic nuance"
    }


def calculate_relevance(answer: str, question: str) -> dict:
    """
    Calculate relevance as question/answer overlap.
    Limitation: Token overlap can miss nuance.
    """
    if not answer or not question:
        return {"score": 0.0, "method": "keyword_overlap", "is_proxy": True}
    
    question_tokens = set(question.lower().split())
    answer_tokens = set(answer.lower().split())
    
    # Remove common stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "shall", "can",
                  "to", "of", "in", "for", "on", "with", "at", "by", "from",
                  "as", "into", "through", "during", "before", "after", "and",
                  "but", "or", "nor", "not", "so", "yet", "both", "either",
                  "neither", "each", "every", "all", "any", "few", "more",
                  "most", "other", "some", "such", "no", "only", "own", "same",
                  "than", "too", "very", "just", "because", "if", "when", "what",
                  "how", "why", "where", "which", "who", "whom", "this", "that",
                  "these", "those", "i", "me", "my", "we", "our", "you", "your",
                  "he", "him", "his", "she", "her", "it", "its", "they", "them", "their"}
    
    q_keywords = question_tokens - stop_words
    a_keywords = answer_tokens - stop_words
    
    if not q_keywords:
        return {"score": 0.5, "method": "keyword_overlap", "is_proxy": True}
    
    overlap = q_keywords & a_keywords
    score = len(overlap) / len(q_keywords) if q_keywords else 0
    
    return {
        "score": round(min(score, 1.0), 4),
        "method": "keyword_overlap",
        "is_proxy": True,
        "limitation": "Token overlap can miss semantic nuance"
    }


def calculate_hallucination_rate(answer: str, context: Optional[str] = None) -> dict:
    """
    Heuristic unsupported-claim/sentence ratio.
    Checks factual claims in the answer against the provided context.
    MUST be labeled as a heuristic — not a perfect factual verifier.
    """
    if not context or not answer:
        return {
            "rate": 0.0,
            "unsupported_claims": 0,
            "total_claims": 0,
            "method": "heuristic_word_overlap",
            "is_proxy": True,
            "limitation": "Must be labeled heuristic — not a perfect detector"
        }
    
    # Split answer into sentences (claims)
    sentences = re.split(r'[.!?]+', answer)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 15]
    
    if not sentences:
        return {"rate": 0.0, "unsupported_claims": 0, "total_claims": 0,
                "method": "heuristic_word_overlap", "is_proxy": True}
    
    context_lower = context.lower()
    unsupported = 0
    
    for sentence in sentences:
        words = [w for w in sentence.lower().split() if len(w) > 3]
        if not words:
            continue
        matches = sum(1 for w in words if w in context_lower)
        coverage = matches / len(words)
        if coverage < 0.15:
            unsupported += 1
    
    rate = unsupported / len(sentences) if sentences else 0
    
    return {
        "rate": round(rate, 4),
        "unsupported_claims": unsupported,
        "total_claims": len(sentences),
        "method": "heuristic_word_overlap",
        "is_proxy": True,
        "limitation": "Heuristic proxy — not absolute truth. Must be labeled as such."
    }


def calculate_retrieval_quality(results: list) -> dict:
    """
    Calculate retrieval quality from similarity scores.
    Limitation: Similarity is not proof of factual correctness.
    """
    if not results:
        return {
            "avg_similarity": 0.0,
            "top_similarity": 0.0,
            "chunk_count": 0,
            "method": "cosine_similarity",
            "is_proxy": True,
            "limitation": "Similarity is not proof of factual correctness"
        }
    
    similarities = [r.get("similarity", 0) for r in results]
    
    return {
        "avg_similarity": round(sum(similarities) / len(similarities), 4),
        "top_similarity": round(max(similarities), 4),
        "min_similarity": round(min(similarities), 4),
        "chunk_count": len(results),
        "method": "cosine_similarity",
        "is_proxy": True,
        "limitation": "Similarity is not proof of factual correctness"
    }


def calculate_all_metrics(
    answer: str,
    question: str,
    reference: Optional[str] = None,
    context: Optional[str] = None,
    retrieval_results: Optional[list] = None,
    latency: float = 0.0,
    prompt_tokens: int = 0,
    response_tokens: int = 0,
    total_tokens: int = 0,
    gen_tok_per_sec: float = 0.0
) -> dict:
    """Calculate all metrics for a single evaluation run."""
    metrics = {
        "correctness": calculate_correctness(answer, reference) if reference else None,
        "relevance": calculate_relevance(answer, question),
        "hallucination": calculate_hallucination_rate(answer, context),
        "retrieval_quality": calculate_retrieval_quality(retrieval_results or []),
        "latency_seconds": round(latency, 4),
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_tokens": total_tokens,
        "generation_tok_per_sec": gen_tok_per_sec,
        "limitation_notice": "All automated metrics are proxy measures. Human review is needed for semantic truth."
    }
    
    return metrics


def run_code_tests(code: str, tests: list[str]) -> dict:
    """
    Run code tests against generated code.
    Returns pass/fail for each test.
    NOTE: This should be called via the isolated code runner service,
    never in the main application container.
    """
    results = {
        "passed": 0,
        "failed": 0,
        "total": len(tests),
        "pass_rate": 0.0,
        "details": [],
        "limitation": "Depends on test quality"
    }
    
    # This is a placeholder — actual execution happens in code-runner container
    for test in tests:
        results["details"].append({
            "test": test,
            "status": "pending",
            "message": "Must be executed via isolated code runner service"
        })
    
    return results
