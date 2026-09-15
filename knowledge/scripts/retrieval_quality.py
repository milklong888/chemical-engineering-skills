"""Small, deterministic display-quality helpers for the offline query adapters.

The source records and the numeric matrix remain authoritative.  This module
only expands ordinary Chinese query fragments, qualifies a natural-language
hit, ranks an already-scored result with a bounded layer preference, hides a
pure chapter heading from natural answers, and groups byte-identical text for
display.  It never changes admission, scope, authority, or record identity.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Iterable, Mapping


_CJK_RUN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]{2,}")
_CJK_STOP_FRAGMENTS = frozenset({
    "为什么", "为何", "怎么", "如何", "是否", "能否", "可以", "直接", "比较",
    "哪些", "哪个", "以及", "因为", "所以", "有时", "有何", "会不会", "如何",
    "这个", "那个", "这种", "一种", "然后", "之后", "先后", "其中", "以及",
})
# These phrases are query syntax rather than engineering subject matter.  They
# are masked before n-gram generation so a window cannot begin or end inside a
# phrase (for example, "不会" inside "会不会" or "是先" across "还是先").
_QUERY_BOUNDARY_PHRASES = tuple(sorted(
    _CJK_STOP_FRAGMENTS | {"需要", "应该", "还是"},
    key=lambda phrase: (-len(phrase), phrase),
))
_LAYER_PREFERENCE = {
    "macro_first": {"L3": 1.0, "L2": 0.72, "L1": 0.34, "L0": 0.0},
    "detail": {"L1": 1.0, "L2": 0.72, "L0": 0.50, "L3": 0.0},
    "neutral": {"L3": 0.72, "L2": 0.52, "L1": 0.25, "L0": 0.0},
}


def match_key(value: object) -> str:
    """Normalize text for conservative lexical/heading comparisons."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return "".join(
        char for char in text
        if char.isalnum() or "\u3400" <= char <= "\u9fff"
    )


def _record_text(record: object) -> str:
    if isinstance(record, Mapping):
        return " ".join(
            str(record.get(key, ""))
            for key in ("node_id", "title", "text")
        )
    return str(record)


def _fragment_candidates(query: str) -> list[tuple[str, int]]:
    candidates: list[tuple[str, int]] = []
    seen: set[str] = set()
    masked_query = query
    for phrase in _QUERY_BOUNDARY_PHRASES:
        masked_query = masked_query.replace(phrase, " " * len(phrase))
    for run in _CJK_RUN.findall(masked_query):
        for size in (4, 3, 2):
            for index in range(len(run) - size + 1):
                fragment = run[index:index + size]
                if fragment in _CJK_STOP_FRAGMENTS or fragment in seen:
                    continue
                seen.add(fragment)
                candidates.append((fragment, len(candidates)))
    return candidates


def query_core_terms(query: str) -> list[str]:
    """Return only terms explicitly present in the user's query."""
    return [term for term in re.split(r"[\s,，;；。！？、/]+", query.strip()) if term]


def select_query_fragments(
    query: str,
    documents: Iterable[object] | None = None,
    *,
    limit: int = 12,
) -> list[str]:
    """Select corpus-observed Chinese n-grams using document-frequency signal.

    Fragments not observed in the candidate corpus are ignored.  This keeps
    ordinary question morphology from becoming a hard-coded synonym list and
    gives rare, query-observed phrases a modest lexical bridge when whitespace
    tokenisation cannot segment a Chinese sentence.
    """
    candidates = _fragment_candidates(query)
    if not candidates or documents is None:
        return [fragment for fragment, _ in candidates[:max(limit, 0)]]
    corpus = [match_key(_record_text(document)) for document in documents]
    document_count = len(corpus)
    if not document_count:
        return []
    scored: list[tuple[float, int, int, str]] = []
    for fragment, position in candidates:
        frequency = sum(fragment in text for text in corpus)
        if not frequency:
            continue
        inverse_frequency = math.log((document_count + 1) / (frequency + 1))
        # Prefer a slightly longer observed phrase, but keep frequency as the
        # main signal so common question particles do not dominate.
        score = inverse_frequency * (1.0 + 0.12 * (len(fragment) - 2))
        scored.append((score, len(fragment), -position, fragment))
    scored.sort(reverse=True)
    return [fragment for _, _, _, fragment in scored[:max(limit, 0)]]


def text_hits(
    query: str,
    record: Mapping[str, object],
    terms: Iterable[str],
    fragments: Iterable[str],
) -> dict:
    """Return explainable lexical evidence for one already-scored record."""
    haystack = match_key(_record_text(record))
    title = match_key(record.get("title", ""))
    normalized_query = match_key(query)
    exact_phrase = bool(normalized_query) and normalized_query in haystack
    core_terms = query_core_terms(query)
    core_hits = [
        term for term in core_terms
        if match_key(term) and match_key(term) in haystack
    ]
    term_hits: list[str] = []
    for term in terms:
        normalized_term = match_key(term)
        if normalized_term and normalized_term in haystack and term not in term_hits:
            term_hits.append(term)
    fragment_hits = [
        fragment for fragment in fragments
        if fragment and match_key(fragment) in haystack
    ]
    title_hits = [term for term in core_hits if match_key(term) in title]
    informative_hits = [
        term for term in [*core_hits, *fragment_hits]
        if len(match_key(term)) >= 2
    ]
    explicit_formula = bool(re.search(r"[=<>±×÷]", query))
    qualified = bool(
        exact_phrase
        or len(set(match_key(term) for term in informative_hits)) >= 2
        or any(len(match_key(term)) >= 3 for term in informative_hits)
        or title_hits
        or (explicit_formula and informative_hits)
    )
    return {
        "exact_phrase": exact_phrase,
        "term_hits": term_hits,
        "core_hits": core_hits,
        "fragment_hits": fragment_hits,
        "title_hits": title_hits,
        "qualified": qualified,
    }


def attach_relevance(
    row: dict,
    *,
    query: str,
    terms: Iterable[str],
    fragments: Iterable[str],
    mode: str,
    source_kind: str,
) -> dict:
    """Add adapter diagnostics without changing the preserved score field."""
    evidence = text_hits(query, row, terms, fragments)
    raw_score = float(row.get("score", 0.0))
    # The existing vector adapter includes a layer bonus in `score`; remove it
    # before applying the bounded, qualification-aware display preference.
    base_score = raw_score
    if source_kind == "vector":
        base_score -= float(row.get("knowledge_layer_bonus", 0.0))
    fragment_signal = sum(
        1.0 + 0.12 * max(len(match_key(fragment)) - 2, 0)
        for fragment in evidence["fragment_hits"]
    )
    if source_kind == "vector":
        direct_signal = (
            0.06 * len(evidence["core_hits"])
            + 0.05 * len(evidence["fragment_hits"])
            + 0.20 * len(evidence["title_hits"])
        )
        relevance = max(base_score, 0.0) + min(fragment_signal, 4.0) * 0.045 + direct_signal
        if evidence["exact_phrase"]:
            relevance += 0.07
    else:
        relevance = base_score + min(fragment_signal, 8.0) * 0.45
        if evidence["exact_phrase"]:
            relevance += 1.5
    preference = _LAYER_PREFERENCE.get(mode, _LAYER_PREFERENCE["neutral"])
    layer = str(row.get("knowledge_layer", ""))
    layer_bias = 0.0
    if evidence["qualified"]:
        layer_bias = preference.get(layer, 0.0) * 0.05 * max(1.0, abs(relevance))
    row["relevance_score"] = relevance
    row["display_rank_score"] = relevance + layer_bias
    row["content_qualified"] = evidence["qualified"]
    row["relevance_evidence"] = {
        "exact_phrase": evidence["exact_phrase"],
        "term_hits": evidence["term_hits"],
        "fragment_hits": evidence["fragment_hits"],
        "title_hits": evidence["title_hits"],
        "core_hits": evidence["core_hits"],
        "layer_preference_applied": bool(layer_bias),
    }
    return row


def is_pure_chapter_title(record: Mapping[str, object]) -> bool:
    """Recognize only a normalized chapter-heading duplicate, not short prose."""
    if record.get("corpus") != "aspen_v10" or record.get("knowledge_layer") != "L0":
        return False
    text = str(record.get("text", "")).strip()
    title = str(record.get("title", "")).split(" / ", 1)[0].strip()
    if not re.match(r"^第\s*\d+\s*章", text):
        return False
    return bool(title) and match_key(text) == match_key(title)


def _duplicate_metadata(record: Mapping[str, object]) -> dict:
    return {
        "node_id": record.get("node_id"),
        "corpus": record.get("corpus"),
        "title": record.get("title"),
        "source": record.get("source"),
        "public_path": record.get("public_path"),
        "applicability": record.get("applicability"),
        "knowledge_layer": record.get("knowledge_layer"),
        "knowledge_status": record.get("knowledge_status"),
    }


def merge_exact_text_results(
    results: list[dict],
    *,
    limit: int,
    full_text: bool,
    merge: bool = True,
    all_records: Iterable[Mapping[str, object]] | None = None,
) -> list[dict]:
    """Merge only exact full-body hashes for natural-answer presentation."""
    ordered = results if merge else results[:]
    pool_by_hash: dict[str, list[Mapping[str, object]]] = {}
    if all_records is not None:
        for record in all_records:
            key = str(record.get("text_sha256", ""))
            if not key or not record.get("content_available", True) or not record.get("retrieval_eligible", True):
                continue
            pool_by_hash.setdefault(key, []).append(record)
    if not merge:
        leaders = ordered[:max(1, min(limit, 100))]
    else:
        groups: dict[str, list[dict]] = {}
        unique: list[tuple[str, dict]] = []
        for row in ordered:
            key = str(row.get("text_sha256", ""))
            if not key:
                key = "__unique__:" + str(row.get("corpus", "")) + ":" + str(row.get("node_id", ""))
            if key not in groups:
                groups[key] = []
                unique.append((key, row))
            groups[key].append(row)
        leaders = []
        for key, representative in unique:
            leader = dict(representative)
            group = groups[key]
            full_group = pool_by_hash.get(key, group)
            if len(full_group) > 1 and not key.startswith("__unique__:"):
                leader["same_text_sha256"] = key
                leader["same_text_count"] = len(full_group)
                ranked_ids = {str(item.get("node_id")) for item in group}
                remaining = [item for item in full_group if str(item.get("node_id")) not in ranked_ids]
                leader["same_text_group"] = [
                    _duplicate_metadata(item) for item in [*group, *remaining]
                ]
            leaders.append(leader)
        leaders = leaders[:max(1, min(limit, 100))]
    for row in leaders:
        row["text_is_excerpt"] = not full_text and len(row.get("text", "")) > 1600
        if row["text_is_excerpt"]:
            row["text"] = row["text"][:1600]
    return leaders
