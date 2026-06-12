"""Text tokenization, stemming, and stopword removal."""

import re
import string
from functools import lru_cache

import nltk
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer


def _ensure_nltk_data():
    """Download required NLTK data if not present."""
    try:
        stopwords.words("english")
    except LookupError:
        nltk.download("stopwords", quiet=True)
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        nltk.download("punkt_tab", quiet=True)


_ensure_nltk_data()

_stemmer = PorterStemmer()
_stop_words = set(stopwords.words("english"))

# Regex to match words (alphanumeric sequences)
_word_pattern = re.compile(r"\b[a-z][a-z0-9]{1,}\b")


def tokenize(text: str) -> list[str]:
    """
    Tokenize text into lowercase words, removing punctuation and short tokens.
    
    Args:
        text: Input text string.
    
    Returns:
        List of lowercase tokens.
    """
    text = text.lower()
    tokens = _word_pattern.findall(text)
    return tokens


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Remove English stopwords from a list of tokens."""
    return [t for t in tokens if t not in _stop_words]


def stem_tokens(tokens: list[str]) -> list[str]:
    """Apply Porter stemming to a list of tokens."""
    return [_stemmer.stem(t) for t in tokens]


def process_text(text: str, stem: bool = False) -> list[str]:
    """
    Full text processing pipeline: tokenize → lowercase → remove stopwords → optional stemming.
    
    Args:
        text: Raw text to process.
        stem: Whether to apply stemming.
    
    Returns:
        List of processed tokens.
    """
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    if stem:
        tokens = stem_tokens(tokens)
    return tokens


def process_query(query: str) -> str:
    """
    Process a search query for Elasticsearch matching.
    
    Keeps it simpler than full text processing — just lowercase and basic cleanup.
    """
    return query.strip().lower()
