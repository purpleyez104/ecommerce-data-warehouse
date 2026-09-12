"""Pure business-rule helpers for the M2.4 candidate data generator."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable, Mapping


CENT = Decimal("0.01")


class RuleViolation(ValueError):
    """Raised when candidate data violates a confirmed cross-row rule."""


def money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def allocate_discount(line_amounts: Iterable[Decimal | int | str], discount: Decimal | int | str) -> list[Decimal]:
    """Allocate an order discount by amount, resolving cents by amount then index."""

    amounts = [money(amount) for amount in line_amounts]
    total = sum(amounts, Decimal("0.00"))
    discount_amount = money(discount)
    if not amounts or total <= 0:
        raise RuleViolation("discount allocation requires positive line amounts")
    if discount_amount < 0 or discount_amount > total:
        raise RuleViolation("discount must be between zero and the order original amount")

    allocations = [money(discount_amount * amount / total) for amount in amounts]
    remainder = money(discount_amount - sum(allocations, Decimal("0.00")))
    ranked_indexes = sorted(range(len(amounts)), key=lambda index: (-amounts[index], index))
    while remainder > Decimal("0.00"):
        for index in ranked_indexes:
            if remainder <= Decimal("0.00"):
                break
            allocations[index] = money(allocations[index] + CENT)
            remainder = money(remainder - CENT)
    while remainder < Decimal("0.00"):
        for index in ranked_indexes:
            if remainder >= Decimal("0.00"):
                break
            if allocations[index] >= CENT:
                allocations[index] = money(allocations[index] - CENT)
                remainder = money(remainder + CENT)
    if sum(allocations, Decimal("0.00")) != discount_amount:
        raise RuleViolation("discount allocation does not conserve amount")
    return allocations


def assert_transition(current: str, target: str, allowed: Mapping[str, set[str]]) -> None:
    if target not in allowed.get(current, set()):
        raise RuleViolation(f"illegal state transition: {current} -> {target}")


def assert_successful_payment(order_id: str, successful_orders: set[str]) -> None:
    if order_id in successful_orders:
        raise RuleViolation(f"order already has a successful payment: {order_id}")
    successful_orders.add(order_id)


def assert_payment_amount(payment_amount: Decimal | int | str, payable_amount: Decimal | int | str) -> None:
    if money(payment_amount) != money(payable_amount):
        raise RuleViolation("successful payment must equal order payable amount")


def assert_return_limit(requested_quantity: int, completed_quantity: int, ordered_quantity: int) -> None:
    if requested_quantity <= 0 or completed_quantity + requested_quantity > ordered_quantity:
        raise RuleViolation("cumulative return quantity exceeds ordered quantity")


def next_active_return_quantity(
    status: str,
    requested_quantity: int,
    active_quantity: int,
    ordered_quantity: int,
) -> int:
    """Count only APPLIED, APPROVED and COMPLETED returns against the item limit."""

    if status not in {"APPLIED", "APPROVED", "REJECTED", "COMPLETED"}:
        raise RuleViolation("invalid return status")
    if status == "REJECTED":
        return active_quantity
    assert_return_limit(requested_quantity, active_quantity, ordered_quantity)
    return active_quantity + requested_quantity


def assert_refund_limit(requested_amount: Decimal | int | str, successful_amount: Decimal | int | str, payable_amount: Decimal | int | str) -> None:
    if money(requested_amount) < 0 or money(successful_amount) + money(requested_amount) > money(payable_amount):
        raise RuleViolation("cumulative successful refund exceeds payable amount")


def refund_amount_for_completed_return(
    item_payable_amount: Decimal | int | str,
    ordered_quantity: int,
    completed_quantity_before: int,
    completed_quantity_after: int,
    successful_refund_amount: Decimal | int | str,
) -> Decimal:
    """Return this completed return's amount using the confirmed cumulative rule."""

    if ordered_quantity <= 0 or completed_quantity_after > ordered_quantity or completed_quantity_after <= completed_quantity_before:
        raise RuleViolation("completed return quantity is invalid")
    cumulative_refundable = money(money(item_payable_amount) * completed_quantity_after / ordered_quantity)
    amount = money(cumulative_refundable - money(successful_refund_amount))
    if amount < 0:
        raise RuleViolation("completed return refund amount is negative")
    return amount


def assert_coupon_use(
    status: str,
    valid_at_lock: bool,
    already_used: bool,
    same_user: bool,
    original_amount: Decimal | int | str = "0",
    minimum_original_amount: Decimal | int | str = "0",
    discount_amount: Decimal | int | str = "0",
) -> None:
    if (
        status != "LOCKED"
        or not valid_at_lock
        or already_used
        or not same_user
        or money(original_amount) < money(minimum_original_amount)
        or money(discount_amount) > money(original_amount)
    ):
        raise RuleViolation("coupon cannot be used by this order")
