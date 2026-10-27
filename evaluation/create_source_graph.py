"""
Source Graph Generator — Create evaluation graphs from benchmark results

Generates:
  - category_latency.png
  - category_latency_p95.png
  - category_tokens.png
  - category_retrieval_similarity.png
  - source_retrieval_frequency.png (RAG source frequency, NOT code dependency)

Usage: python evaluation/create_source_graph.py
"""

import json
import os
import sys

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
GRAPH_DIR = os.path.join(os.path.dirname(EVAL_DIR), "docs", "evaluation_graphs")


def load_json(filename):
    path = os.path.join(EVAL_DIR, filename)
    if not os.path.exists(path):
        print(f"Warning: {filename} not found")
        return None
    with open(path) as f:
        return json.load(f)


def create_graphs():
    """Generate all evaluation graphs using matplotlib."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("matplotlib not installed. Install with: pip install matplotlib")
        print("Generating graph data as JSON instead...")
        create_graph_data_json()
        return

    os.makedirs(GRAPH_DIR, exist_ok=True)

    summary = load_json("category_summary.json")
    results = load_json("category_evaluation_results.json")
    rag_results = load_json("evaluation_results_rag.json")

    if not summary:
        print("No summary data found. Run evaluate_models.py first.")
        return

    categories = list(summary.keys())
    models = set()
    for cat_data in summary.values():
        models.update(cat_data.keys())
    models = sorted(models)

    colors = ['#6366f1', '#10b981', '#f59e0b', '#ef4444', '#ec4899']

    # 1. Category Latency
    fig, ax = plt.subplots(figsize=(12, 6))
    x_pos = range(len(categories))
    bar_width = 0.25
    for i, model in enumerate(models):
        values = [summary.get(cat, {}).get(model, {}).get("avg_latency", 0) for cat in categories]
        offset = (i - len(models)/2 + 0.5) * bar_width
        ax.bar([x + offset for x in x_pos], values, bar_width, label=model, color=colors[i % len(colors)])
    ax.set_xlabel('Category')
    ax.set_ylabel('Average Latency (seconds)')
    ax.set_title('Average Latency by Category and Model')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPH_DIR, "category_latency.png"), dpi=150)
    plt.close()
    print("✓ category_latency.png")

    # 2. P95 Latency
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, model in enumerate(models):
        values = [summary.get(cat, {}).get(model, {}).get("p95_latency", 0) for cat in categories]
        offset = (i - len(models)/2 + 0.5) * bar_width
        ax.bar([x + offset for x in x_pos], values, bar_width, label=model, color=colors[i % len(colors)])
    ax.set_xlabel('Category')
    ax.set_ylabel('P95 Latency (seconds)')
    ax.set_title('P95 Latency by Category and Model')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPH_DIR, "category_latency_p95.png"), dpi=150)
    plt.close()
    print("✓ category_latency_p95.png")

    # 3. Token Usage
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, model in enumerate(models):
        values = [summary.get(cat, {}).get(model, {}).get("avg_tokens", 0) for cat in categories]
        offset = (i - len(models)/2 + 0.5) * bar_width
        ax.bar([x + offset for x in x_pos], values, bar_width, label=model, color=colors[i % len(colors)])
    ax.set_xlabel('Category')
    ax.set_ylabel('Average Token Usage')
    ax.set_title('Token Usage by Category and Model')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPH_DIR, "category_tokens.png"), dpi=150)
    plt.close()
    print("✓ category_tokens.png")

    # 4. Retrieval Similarity
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, model in enumerate(models):
        values = [summary.get(cat, {}).get(model, {}).get("avg_retrieval_similarity", 0) for cat in categories]
        offset = (i - len(models)/2 + 0.5) * bar_width
        ax.bar([x + offset for x in x_pos], values, bar_width, label=model, color=colors[i % len(colors)])
    ax.set_xlabel('Category')
    ax.set_ylabel('Average Retrieval Similarity')
    ax.set_title('Retrieval Similarity by Category and Model')
    ax.set_xticks(x_pos)
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=8)
    ax.legend()
    ax.set_ylim(0, 1.0)
    plt.tight_layout()
    plt.savefig(os.path.join(GRAPH_DIR, "category_retrieval_similarity.png"), dpi=150)
    plt.close()
    print("✓ category_retrieval_similarity.png")

    # 5. Source Retrieval Frequency (RAG source frequency — NOT code dependency)
    if rag_results:
        source_counts = {}
        for r in rag_results:
            for src in r.get("sources", []):
                doc = src.get("document", "unknown")
                source_counts[doc] = source_counts.get(doc, 0) + 1

        if source_counts:
            sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:15]
            names = [s[0][:30] for s in sorted_sources]
            counts = [s[1] for s in sorted_sources]

            fig, ax = plt.subplots(figsize=(12, 6))
            ax.barh(range(len(names)), counts, color='#6366f1')
            ax.set_yticks(range(len(names)))
            ax.set_yticklabels(names, fontsize=8)
            ax.set_xlabel('Retrieval Frequency')
            ax.set_title('RAG Source Retrieval Frequency\n(How often each source document is retrieved)')
            ax.invert_yaxis()
            plt.tight_layout()
            plt.savefig(os.path.join(GRAPH_DIR, "source_retrieval_frequency.png"), dpi=150)
            plt.close()
            print("✓ source_retrieval_frequency.png")

    print(f"\nAll graphs saved to {GRAPH_DIR}/")


def create_graph_data_json():
    """Fallback: save graph data as JSON when matplotlib is unavailable."""
    summary = load_json("category_summary.json")
    if not summary:
        print("No summary data found.")
        return
    
    os.makedirs(GRAPH_DIR, exist_ok=True)
    graph_data = {"summary": summary, "note": "Install matplotlib for PNG graphs"}
    with open(os.path.join(GRAPH_DIR, "graph_data.json"), "w") as f:
        json.dump(graph_data, f, indent=2)
    print(f"Graph data saved to {GRAPH_DIR}/graph_data.json")


if __name__ == "__main__":
    create_graphs()
