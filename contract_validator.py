"""
contract_validator.py
----------------------
Validates parsed contract data against business rules before storage.
Checks expiry dates, required fields, counterparty details, and value thresholds.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str]
    warnings: list[str]


@dataclass
class Contract:
    contract_id: str
    title: str
    counterparty: str
    start_date: Optional[datetime]
    expiry_date: Optional[datetime]
    value: float
    currency: str
    signed: bool


# Contracts above this value require a second approver
HIGH_VALUE_THRESHOLD = 50_000.00

# Warn if a contract expires within this many days
EXPIRY_WARNING_DAYS = 30


def validate_required_fields(contract: Contract) -> list[str]:
    """Return a list of error messages for any missing required fields."""
    errors = []
    if not contract.contract_id.strip():
        errors.append("contract_id is required")
    if not contract.title.strip():
        errors.append("title is required")
    if not contract.counterparty.strip():
        errors.append("counterparty is required")
    if contract.start_date is None:
        errors.append("start_date is required")
    if contract.expiry_date is None:
        errors.append("expiry_date is required")
    if not contract.currency.strip():
        errors.append("currency is required")
    return errors


def validate_dates(contract: Contract) -> tuple[list[str], list[str]]:
    """
    Validate date logic. Returns (errors, warnings).
    - Error if expiry is before start
    - Error if expiry is in the past
    - Warning if expiry is within EXPIRY_WARNING_DAYS days
    """
    errors = []
    warnings = []
    now = datetime.now(timezone.utc)

    if contract.start_date and contract.expiry_date:
        if contract.expiry_date <= contract.start_date:
            errors.append("expiry_date must be after start_date")

        if contract.expiry_date < now:
            errors.append(
                f"contract has already expired on "
                f"{contract.expiry_date.strftime('%Y-%m-%d')}"
            )
        else:
            days_remaining = (contract.expiry_date - now).days
            if days_remaining <= EXPIRY_WARNING_DAYS:
                warnings.append(
                    f"contract expires in {days_remaining} day(s) — "
                    f"renewal action may be required"
                )

    return errors, warnings


def validate_value(contract: Contract) -> tuple[list[str], list[str]]:
    """
    Validate contract value. Returns (errors, warnings).
    - Error if value is negative
    - Warning if value exceeds HIGH_VALUE_THRESHOLD (requires second approver)
    """
    errors = []
    warnings = []

    if contract.value < 0:
        errors.append(f"contract value cannot be negative (got {contract.value})")

    if contract.value > HIGH_VALUE_THRESHOLD:
        warnings.append(
            f"contract value {contract.currency} {contract.value:,.2f} exceeds "
            f"{HIGH_VALUE_THRESHOLD:,.0f} — second approver required"
        )

    return errors, warnings


def validate_contract(contract: Contract) -> ValidationResult:
    """
    Run all validation rules against a Contract and return a ValidationResult.

    Checks performed:
    1. Required field presence
    2. Date logic (expiry after start, not in the past, expiry warning)
    3. Value sanity and high-value threshold warning
    4. Signature status warning
    """
    all_errors: list[str] = []
    all_warnings: list[str] = []

    # Required fields
    all_errors.extend(validate_required_fields(contract))

    # Date validation
    date_errors, date_warnings = validate_dates(contract)
    all_errors.extend(date_errors)
    all_warnings.extend(date_warnings)

    # Value validation
    value_errors, value_warnings = validate_value(contract)
    all_errors.extend(value_errors)
    all_warnings.extend(value_warnings)

    # Signature check
    if not contract.signed:
        all_warnings.append("contract is not yet signed — cannot be enforced")

    return ValidationResult(
        is_valid=len(all_errors) == 0,
        errors=all_errors,
        warnings=all_warnings,
    )
