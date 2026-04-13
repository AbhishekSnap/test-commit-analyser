"""
document_classifier.py
-----------------------
Classifies uploaded documents by type (invoice, contract, purchase order, etc.)
using keyword scoring and structural pattern matching.
Used as a pre-processing step before routing documents to the correct parser.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DocumentType(Enum):
    INVOICE          = "invoice"
    CONTRACT         = "contract"
    PURCHASE_ORDER   = "purchase_order"
    STATEMENT        = "statement"
    CREDIT_NOTE      = "credit_note"
    DELIVERY_NOTE    = "delivery_note"
    UNKNOWN          = "unknown"


@dataclass
class ClassificationResult:
    document_type: DocumentType
    confidence: float          # 0.0 – 1.0
    matched_keywords: list[str] = field(default_factory=list)
    fallback_used: bool = False


# ── Keyword scoring tables ─────────────────────────────────────────────────────
# Each document type has a list of (keyword, weight) pairs.
# Higher weight = stronger signal for that type.

KEYWORD_WEIGHTS: dict[DocumentType, list[tuple[str, float]]] = {
    DocumentType.INVOICE: [
        ("invoice", 1.0),
        ("inv no", 0.9),
        ("invoice number", 1.0),
        ("amount due", 0.9),
        ("payment terms", 0.7),
        ("vat", 0.7),
        ("bill to", 0.7),
    ],
    DocumentType.CONTRACT: [
        ("agreement", 0.8),
        ("terms and conditions", 1.0),
        ("party", 0.6),
        ("whereas", 0.9),
        ("obligations", 0.8),
        ("governing law", 1.0),
        ("signed by", 0.7),
        ("effective date", 0.7),
    ],
    DocumentType.PURCHASE_ORDER: [
        ("purchase order", 1.0),
        ("po number", 1.0),
        ("ship to", 0.8),
        ("delivery address", 0.7),
        ("order date", 0.7),
        ("unit price", 0.6),
        ("qty", 0.5),
    ],
    DocumentType.STATEMENT: [
        ("statement of account", 1.0),
        ("opening balance", 0.9),
        ("closing balance", 0.9),
        ("transactions", 0.6),
        ("period", 0.5),
    ],
    DocumentType.CREDIT_NOTE: [
        ("credit note", 1.0),
        ("cn no", 0.9),
        ("credit memo", 1.0),
        ("amount credited", 0.9),
        ("original invoice", 0.8),
    ]

}

# Minimum confidence to accept a classification (below this → UNKNOWN)
CONFIDENCE_THRESHOLD = 0.50


def _score_text(text: str) -> dict[DocumentType, tuple[float, list[str]]]:
    """
    Score the document text against every keyword table.
    Returns {DocumentType: (raw_score, matched_keywords)}.
    """
    normalised = text.lower()
    scores: dict[DocumentType, tuple[float, list[str]]] = {}

    for doc_type, keywords in KEYWORD_WEIGHTS.items():
        total_weight = sum(w for _, w in keywords)
        matched: list[str] = []
        earned = 0.0

        for keyword, weight in keywords:
            if re.search(r"\b" + re.escape(keyword) + r"\b", normalised):
                matched.append(keyword)
                earned += weight

        confidence = round(earned / total_weight, 4) if total_weight else 0.0
        scores[doc_type] = (confidence, matched)

    return scores


def classify(text: str, fallback: Optional[DocumentType] = None) -> ClassificationResult:
    """
    Classify a document from its raw text content.

    Steps:
    1. Score text against all keyword tables
    2. Pick the DocumentType with the highest confidence score
    3. If best score is below CONFIDENCE_THRESHOLD, use fallback or UNKNOWN

    Args:
        text:     Raw extracted text from the document
        fallback: DocumentType to return when confidence is too low (optional)

    Returns:
        ClassificationResult with type, confidence, and matched keywords
    """
    if not text or not text.strip():
        return ClassificationResult(
            document_type=fallback or DocumentType.UNKNOWN,
            confidence=0.0,
            fallback_used=True,
        )

    scores = _score_text(text)

    best_type = max(scores, key=lambda t: scores[t][0])
    best_confidence, matched_keywords = scores[best_type]

    if best_confidence < CONFIDENCE_THRESHOLD:
        return ClassificationResult(
            document_type=fallback or DocumentType.UNKNOWN,
            confidence=best_confidence,
            matched_keywords=matched_keywords,
            fallback_used=True,
        )

    return ClassificationResult(
        document_type=best_type,
        confidence=best_confidence,
        matched_keywords=matched_keywords,
        fallback_used=False,
    )


def classify_batch(documents: list[str]) -> list[ClassificationResult]:
    """
    Classify a list of documents. Preserves order.
    Each document is classified independently.
    """
    return [classify(doc) for doc in documents]
