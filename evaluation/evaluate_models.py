"""
Evaluation Runner — Run the full 105-evaluation benchmark
35 questions × 3 models = 105 evaluations

Usage:
    python evaluation/evaluate_models.py

This script should only be run AFTER the application is stable.
Do NOT rerun for cosmetic changes.
"""

import json
import time
import sys
import os
import httpx

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APP_URL = os.getenv("APP_URL", "http://localhost:8000")
MODELS = ["qwen2.5:3b", "starcoder2:3b", "codellama:latest", "mistral:latest"]
EVAL_DIR = os.path.dirname(os.path.abspath(__file__))


def load_dataset():
    """Load the evaluation dataset."""
    dataset_path = os.path.join(EVAL_DIR, "dataset.json")
    with open(dataset_path) as f:
        return json.load(f)


def run_single_evaluation(question_data, model, rag_enabled=True, top_k=5):
    """Run a single evaluation via the app's /ask endpoint."""
    try:
        with httpx.Client(timeout=180.0) as client:
            response = client.post(
                f"{APP_URL}/ask",
                json={
                    "question": question_data["question"],
                    "model": model,
                    "rag_enabled": rag_enabled,
                    "top_k": top_k,
                    "temperature": 0.1,
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Calculate metrics
            from services.live_metrics import calculate_all_metrics
            metrics = calculate_all_metrics(
                answer=result.get("answer", ""),
                question=question_data["question"],
                reference=question_data.get("reference_answer"),
                context="\n".join([s.get("text_preview", "") for s in result.get("sources", [])]),
                retrieval_results=result.get("sources", []),
                latency=result.get("telemetry", {}).get("latency_seconds", 0),
                prompt_tokens=result.get("telemetry", {}).get("prompt_tokens", 0),
                response_tokens=result.get("telemetry", {}).get("response_tokens", 0),
                total_tokens=result.get("telemetry", {}).get("total_tokens", 0),
                gen_tok_per_sec=result.get("telemetry", {}).get("generation_tok_per_sec", 0),
            )
            
            return {
                "question_id": question_data["id"],
                "category": question_data["category"],
                "question": question_data["question"],
                "reference_answer": question_data.get("reference_answer", ""),
                "model": model,
                "rag_enabled": rag_enabled,
                "answer": result.get("answer", ""),
                "sources": result.get("sources", []),
                "telemetry": result.get("telemetry", {}),
                "metrics": metrics,
                "guardrail": result.get("guardrail", {}),
                "status": result.get("status", "unknown"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
    except Exception as e:
        return {
            "question_id": question_data["id"],
            "category": question_data["category"],
            "question": question_data["question"],
            "model": model,
            "rag_enabled": rag_enabled,
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


def run_full_benchmark():
    """Run the complete 105-evaluation benchmark."""
    dataset = load_dataset()
    questions = dataset["questions"]
    
    print(f"=== AI DevOps Assistant — Full Benchmark ===")
    print(f"Questions: {len(questions)}")
    print(f"Models: {MODELS}")
    print(f"Total evaluations: {len(questions) * len(MODELS)}")
    print(f"{'='*50}")
    
    all_results = []
    rag_results = []
    no_rag_results = []
    
    for i, q in enumerate(questions):
        for j, model in enumerate(MODELS):
            eval_num = i * len(MODELS) + j + 1
            total = len(questions) * len(MODELS)
            print(f"\n[{eval_num}/{total}] Category: {q['category']} | Model: {model}")
            print(f"  Question: {q['question'][:80]}...")
            
            # RAG evaluation
            result = run_single_evaluation(q, model, rag_enabled=True)
            all_results.append(result)
            rag_results.append(result)
            
            status = result.get("status", "unknown")
            latency = result.get("telemetry", {}).get("latency_seconds", 0)
            correctness = (result.get("metrics", {}).get("correctness") or {}).get("score", "N/A")
            print(f"  RAG Result: status={status}, latency={latency:.2f}s, correctness={correctness}")
            
            # No-RAG evaluation (same question, same model)
            no_rag_result = run_single_evaluation(q, model, rag_enabled=False)
            no_rag_results.append(no_rag_result)
            
            no_rag_latency = no_rag_result.get("telemetry", {}).get("latency_seconds", 0)
            print(f"  No-RAG Result: latency={no_rag_latency:.2f}s")
            
            # Brief pause to avoid overwhelming Ollama
            time.sleep(1)
    
    # Save results
    save_results(all_results, rag_results, no_rag_results)
    generate_summary(all_results)
    
    print(f"\n{'='*50}")
    print(f"Benchmark complete! {len(all_results)} RAG + {len(no_rag_results)} No-RAG evaluations")
    print(f"Results saved to {EVAL_DIR}/")


def save_results(all_results, rag_results, no_rag_results):
    """Save all evaluation results as immutable JSON."""
    # Category results (all RAG results)
    with open(os.path.join(EVAL_DIR, "category_evaluation_results.json"), "w") as f:
        json.dump(all_results, f, indent=2)
    
    # RAG results
    with open(os.path.join(EVAL_DIR, "evaluation_results_rag.json"), "w") as f:
        json.dump(rag_results, f, indent=2)
    
    # No-RAG results
    with open(os.path.join(EVAL_DIR, "evaluation_results_no_rag.json"), "w") as f:
        json.dump(no_rag_results, f, indent=2)
    
    print(f"\nResults saved:")
    print(f"  - category_evaluation_results.json ({len(all_results)} results)")
    print(f"  - evaluation_results_rag.json ({len(rag_results)} results)")
    print(f"  - evaluation_results_no_rag.json ({len(no_rag_results)} results)")


def generate_summary(results):
    """Generate category summary from evaluation results."""
    categories = {}
    
    for r in results:
        cat = r.get("category", "Unknown")
        model = r.get("model", "Unknown")
        
        if cat not in categories:
            categories[cat] = {}
        if model not in categories[cat]:
            categories[cat][model] = {
                "count": 0,
                "total_latency": 0,
                "latencies": [],
                "total_correctness": 0,
                "total_relevance": 0,
                "total_hallucination": 0,
                "total_tokens": 0,
                "total_retrieval_similarity": 0,
                "retrieval_count": 0,
            }
        
        m = categories[cat][model]
        m["count"] += 1
        
        latency = r.get("telemetry", {}).get("latency_seconds", 0)
        m["total_latency"] += latency
        m["latencies"].append(latency)
        
        metrics = r.get("metrics", {})
        if metrics.get("correctness"):
            m["total_correctness"] += metrics["correctness"].get("score", 0)
        if metrics.get("relevance"):
            m["total_relevance"] += metrics["relevance"].get("score", 0)
        if metrics.get("hallucination"):
            m["total_hallucination"] += metrics["hallucination"].get("rate", 0)
        
        m["total_tokens"] += r.get("telemetry", {}).get("total_tokens", 0)
        
        if metrics.get("retrieval_quality", {}).get("avg_similarity", 0) > 0:
            m["total_retrieval_similarity"] += metrics["retrieval_quality"]["avg_similarity"]
            m["retrieval_count"] += 1
    
    # Calculate averages and P95
    summary = {}
    for cat, models in categories.items():
        summary[cat] = {}
        for model, data in models.items():
            n = data["count"]
            latencies = sorted(data["latencies"])
            p95_idx = int(len(latencies) * 0.95)
            
            summary[cat][model] = {
                "evaluations": n,
                "avg_correctness": round(data["total_correctness"] / n, 4) if n > 0 else 0,
                "avg_relevance": round(data["total_relevance"] / n, 4) if n > 0 else 0,
                "avg_hallucination_rate": round(data["total_hallucination"] / n, 4) if n > 0 else 0,
                "avg_latency": round(data["total_latency"] / n, 4) if n > 0 else 0,
                "p95_latency": round(latencies[p95_idx] if latencies else 0, 4),
                "avg_tokens": round(data["total_tokens"] / n) if n > 0 else 0,
                "avg_retrieval_similarity": round(
                    data["total_retrieval_similarity"] / data["retrieval_count"], 4
                ) if data["retrieval_count"] > 0 else 0,
            }
    
    # Save summary
    with open(os.path.join(EVAL_DIR, "category_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    
    # Generate CSV
    generate_csv(summary)
    
    # Print summary table
    print(f"\n{'='*80}")
    print("CATEGORY-WISE SUMMARY")
    print(f"{'='*80}")
    for cat, models in summary.items():
        print(f"\n📂 {cat}:")
        for model, data in models.items():
            print(f"  🤖 {model}:")
            print(f"     Correctness: {data['avg_correctness']:.2f} | Relevance: {data['avg_relevance']:.2f}")
            print(f"     Hallucination: {data['avg_hallucination_rate']:.2f} | Latency: {data['avg_latency']:.2f}s")
            print(f"     P95 Latency: {data['p95_latency']:.2f}s | Tokens: {data['avg_tokens']}")
    
    return summary


def generate_csv(summary):
    """Generate CSV from summary data."""
    csv_path = os.path.join(EVAL_DIR, "category_summary.csv")
    with open(csv_path, "w") as f:
        f.write("Category,Model,Evaluations,Avg_Correctness,Avg_Relevance,Avg_Hallucination,Avg_Latency,P95_Latency,Avg_Tokens,Avg_Retrieval_Similarity\n")
        for cat, models in summary.items():
            for model, data in models.items():
                f.write(f"{cat},{model},{data['evaluations']},{data['avg_correctness']},{data['avg_relevance']},{data['avg_hallucination_rate']},{data['avg_latency']},{data['p95_latency']},{data['avg_tokens']},{data['avg_retrieval_similarity']}\n")
    print(f"  - category_summary.csv saved")


if __name__ == "__main__":
    run_full_benchmark()
