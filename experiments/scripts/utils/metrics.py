import math
from typing import List, Sequence


def recall_at_k(relevant: Sequence[str], retrieved: Sequence[str], k: int) -> float:
    if k <= 0:
        return 0.0
    rel_set = set(relevant)
    top_k = retrieved[:k]
    if not rel_set:
        return 0.0
    hits = len(rel_set.intersection(top_k))
    return hits / len(rel_set)


def mrr(relevant: Sequence[str], retrieved: Sequence[str]) -> float:
    rel_set = set(relevant)
    for idx, doc_id in enumerate(retrieved, start=1):
        if doc_id in rel_set:
            return 1.0 / idx
    return 0.0


def ndcg_at_k(relevance: Sequence[int], k: int) -> float:
    """relevance: list of binary gains aligned with retrieved items."""
    if k <= 0 or not relevance:
        return 0.0
    gains = relevance[:k]
    dcg = sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(gains))
    ideal = sorted(gains, reverse=True)
    idcg = sum((2**g - 1) / math.log2(i + 2) for i, g in enumerate(ideal))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def gini_coefficient(values: List[float]) -> float:
    """0 = perfect equality, 1 = perfect inequality."""
    n = len(values)
    if n == 0:
        return 0.0
    sorted_vals = sorted(values)
    cumvals = [sum(sorted_vals[: i + 1]) for i in range(n)]
    total = cumvals[-1]
    if total == 0:
        return 0.0
    gini = (n + 1 - 2 * sum(cumvals) / total) / n
    return gini
