"""Text processing utilities for keyword extraction."""


def extract_keywords_yake(
    text_corpus: str,
    language: str = "en",
    max_ngram_size: int = 2,
    deduplication_threshold: float = 0.5,
    num_keywords: int = 50
) -> list[dict]:
    """Extract keywords from text corpus using YAKE."""
    import yake

    if not text_corpus or not text_corpus.strip():
        return []

    kw_extractor = yake.KeywordExtractor(
        lan=language,
        n=max_ngram_size,
        dedupLim=deduplication_threshold,
        top=num_keywords,
        features=None
    )

    keywords = kw_extractor.extract_keywords(text_corpus)

    return [
        {"keyword": kw, "score": score}
        for kw, score in keywords
    ]


def diversify_keywords(
    keywords: list[dict],
    search_term: str,
    max_results: int = 30
) -> list[dict]:
    """Post-process keywords to increase diversity by filtering redundant terms."""
    if not keywords or max_results <= 0:
        return []

    # Normalize search term words
    search_words = set(search_term.lower().split())

    diversified = []
    seen_word_sets = []

    for kw in keywords:
        kw_lower = kw["keyword"].lower()
        kw_words = set(kw_lower.split())

        # Skip if keyword contains search term words
        if search_words & kw_words:
            continue

        # Skip if >50% overlap with any already-selected keyword
        is_redundant = False
        for seen_words in seen_word_sets:
            overlap = len(kw_words & seen_words)
            min_len = min(len(kw_words), len(seen_words))
            if min_len > 0 and overlap / min_len > 0.5:
                is_redundant = True
                break

        if not is_redundant:
            diversified.append(kw)
            seen_word_sets.append(kw_words)

        if len(diversified) >= max_results:
            break

    return diversified
