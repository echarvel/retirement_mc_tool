"""Loan amortization helpers."""


def amort_payment(principal: float, rate_real: float, term_years: int) -> float:
    if principal <= 0:
        return 0.0
    r = rate_real
    n = term_years
    return (r * principal) / (1.0 - (1.0 + r) ** (-n))


def loan_balance_after_k(
    principal: float, rate_real: float, payment: float, k: int
) -> float:
    if principal <= 0:
        return 0.0
    r = rate_real
    return principal * (1.0 + r) ** k - payment * (((1.0 + r) ** k - 1.0) / r)
