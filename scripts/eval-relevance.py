"""Evaluate semantic retrieval floors against explicit query/document labels.

Run with the source-built extension: .venv/bin/python scripts/eval-relevance.py
"""
import argparse
import json
from pathlib import Path

from memori import PyMemori


def evaluate(dataset, thresholds, limit):
    db = PyMemori(":memory:")
    documents = dataset["memories"]
    known_ids = {doc["id"] for doc in documents}
    if len(known_ids) != len(documents):
        raise ValueError("document IDs must be unique")
    for doc in documents:
        db.insert_with_id(doc["id"], doc["content"])
    queries = []
    for case in dataset["queries"]:
        relevant = set(case["relevant"])
        if not relevant <= known_ids:
            raise ValueError("relevance labels reference unknown document IDs")
        queries.append((case, relevant, db.embed(case["text"])))
    reports = []
    for threshold in thresholds:
        tp = fp = fn = correct_abstentions = 0
        details = []
        for case, relevant, vector in queries:
            hits = db.search(vector=vector, limit=limit, min_similarity=threshold)
            retrieved = {hit["id"] for hit in hits}
            tp += len(retrieved & relevant)
            fp += len(retrieved - relevant)
            fn += len(relevant - retrieved)
            correct_abstentions += int(not relevant and not retrieved)
            details.append({"query": case["text"], "expected": sorted(relevant), "retrieved": [hit["id"] for hit in hits]})
        reports.append({
            "min_similarity": threshold, "true_positives": tp, "false_positives": fp,
            "false_negatives": fn, "precision": tp / (tp + fp) if tp + fp else None,
            "recall": tp / (tp + fn) if tp + fn else None,
            "correct_abstentions": correct_abstentions,
            "unanswerable_queries": sum(not relevant for _, relevant, _ in queries),
            "details": details,
        })
    return {"model": "AllMiniLM-L6-V2", "mode": "vector-only", "limit": limit,
            "description": dataset.get("description"), "reports": reports}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parents[1] / "docs/evals/relevance.json")
    parser.add_argument("--thresholds", nargs="+", default=["none", "0.25", "0.4", "0.55", "0.7"])
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    if args.limit < 1:
        parser.error("--limit must be positive")
    thresholds = [None if value.lower() == "none" else float(value) for value in args.thresholds]
    print(json.dumps(evaluate(json.loads(args.dataset.read_text()), thresholds, args.limit), indent=2))


if __name__ == "__main__":
    main()
