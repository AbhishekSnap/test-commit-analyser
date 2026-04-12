"""
invoice_parser.py
-----------------
Parses invoice text extracted from PDFs and returns structured data.
Handles common UK/EU date formats and extracts line items, totals, and VAT.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class LineItem:
    description: str
    quantity: float
    unit_price: float
    total: float


@dataclass
class Invoice:
    invoice_number: str
    issue_date: Optional[datetime]
    due_date: Optional[datetime]
    vendor: str
    line_items: list[LineItem] = field(default_factory=list)
    subtotal: float = 0.0
    vat_rate: float = 0.20
    vat_amount: float = 0.0
    total: float = 0.0


# Regex patterns for UK (DD/MM/YYYY) and ISO (YYYY-MM-DD) date formats
_DATE_PATTERNS = [
    (r"\b(\d{2})/(\d{2})/(\d{4})\b", "%d/%m/%Y"),   # UK: 15/04/2025
    (r"\b(\d{4})-(\d{2})-(\d{2})\b", "%Y-%m-%d"),   # ISO: 2025-04-15
    (r"\b(\d{2})-(\d{2})-(\d{4})\b", "%d-%m-%Y"),   # EU:  15-04-2025
]


def parse_date(text: str) -> Optional[datetime]:
    """
    Extract and parse the first date found in a string.
    Tries UK, ISO, and EU formats in order.
    Returns None if no date is found.
    """
    for pattern, fmt in _DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                return datetime.strptime(match.group(0), fmt)
            except ValueError:
                continue
    return None


def parse_line_item(line: str) -> Optional[LineItem]:
    """
    Parse a single invoice line like:
      'Web Development Services  10  150.00  1500.00'
    Returns None if the line doesn't match the expected format.
    """
    # Match: description  qty  unit_price  total
    pattern = r"^(.+?)\s{2,}(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)\s+(\d+(?:\.\d+)?)$"
    match = re.match(pattern, line.strip())
    if not match:
        return None
    return LineItem(
        description=match.group(1).strip(),
        quantity=float(match.group(2)),
        unit_price=float(match.group(3)),
        total=float(match.group(4)),
    )


def parse_invoice(text: str) -> Invoice:
    """
    Parse raw invoice text into a structured Invoice object.

    Expects sections like:
      Invoice No: INV-2025-042
      Issue Date: 01/04/2025
      Due Date: 30/04/2025
      From: Acme Ltd
      [line items]
      Subtotal: 1500.00
      VAT (20%): 300.00
      Total: 1800.00
    """
    lines = text.strip().splitlines()

    invoice_number = ""
    issue_date = None
    due_date = None
    vendor = ""
    line_items = []
    subtotal = 0.0
    vat_amount = 0.0
    total = 0.0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        lower = line.lower()

        if lower.startswith("invoice no"):
            invoice_number = line.split(":", 1)[-1].strip()

        elif lower.startswith("issue date") or lower.startswith("date"):
            issue_date = parse_date(line)

        elif lower.startswith("due date"):
            due_date = parse_date(line)

        elif lower.startswith("from:") or lower.startswith("vendor:"):
            vendor = line.split(":", 1)[-1].strip()

        elif lower.startswith("subtotal"):
            match = re.search(r"[\d,]+\.\d{2}", line)
            if match:
                subtotal = float(match.group(0).replace(",", ""))

        elif lower.startswith("vat"):
            match = re.search(r"[\d,]+\.\d{2}", line)
            if match:
                vat_amount = float(match.group(0).replace(",", ""))

        elif lower.startswith("total"):
            match = re.search(r"[\d,]+\.\d{2}", line)
            if match:
                total = float(match.group(0).replace(",", ""))

        else:
            item = parse_line_item(line)
            if item:
                line_items.append(item)

    vat_rate = round(vat_amount / subtotal, 2) if subtotal else 0.20

    return Invoice(
        invoice_number=invoice_number,
        issue_date=issue_date,
        due_date=due_date,
        vendor=vendor,
        line_items=line_items,
        subtotal=subtotal,
        vat_rate=vat_rate,
        vat_amount=vat_amount,
        total=total,
    )
