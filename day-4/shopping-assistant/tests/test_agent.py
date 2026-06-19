import pytest
from app.agent import redeem_discount, DISCOUNT_STORE

@pytest.fixture(autouse=True)
def reset_store():
    """Ensure strict test isolation by resetting in-memory store state."""
    DISCOUNT_STORE["WELCOME50"] = False
    DISCOUNT_STORE["SUMMER20"] = False
    yield
    DISCOUNT_STORE["WELCOME50"] = False
    DISCOUNT_STORE["SUMMER20"] = False

def test_discount_code_can_only_be_redeemed_once():
    """Verify a user cannot reuse a single-use code."""
    res_one = redeem_discount("WELCOME50", "user_123")
    assert "Success" in res_one
    assert DISCOUNT_STORE["WELCOME50"] is True

    res_two = redeem_discount("WELCOME50", "user_456")
    assert "Error: Discount code has already been redeemed" in res_two

def test_discount_redemption_rejects_invalid_code():
    """Verify that unknown discount codes are hard-blocked."""
    res = redeem_discount("INVALID999", "user_123")
    assert "Error: Invalid discount code" in res

def test_discount_redemption_rejects_guest_accounts():
    """Verify that unauthenticated guest accounts cannot redeem discounts."""
    res = redeem_discount("SUMMER20", "guest_999")
    assert "Error: Registered user account required" in res
    assert DISCOUNT_STORE["SUMMER20"] is False
