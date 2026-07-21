from __future__ import annotations


def levenshtein_distance(a: list[str], b: list[str]) -> int:
    previous = list(range(len(b) + 1))
    for i, item_a in enumerate(a, start=1):
        current = [i]
        for j, item_b in enumerate(b, start=1):
            current.append(
                min(
                    current[j - 1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (item_a != item_b),
                )
            )
        previous = current
    return previous[-1]


def cer(reference: str, hypothesis: str) -> float:
    if not reference:
        return 0.0 if not hypothesis else 1.0
    return levenshtein_distance(list(reference), list(hypothesis)) / len(reference)


def wer(reference: str, hypothesis: str) -> float:
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return levenshtein_distance(ref_words, hyp_words) / len(ref_words)
