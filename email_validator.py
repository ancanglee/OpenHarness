import re


def validate_email(email: str) -> bool:
    """Validate an email address.

    Checks for a valid local part, @ symbol, and domain with at least one dot.
    Returns True if valid, False otherwise.
    """
    if not email or not isinstance(email, str):
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


if __name__ == "__main__":
    tests = [
        ("user@example.com", True),
        ("first.last@domain.co.uk", True),
        ("user+tag@example.org", True),
        ("user@.com", False),
        ("@example.com", False),
        ("user@com", False),
        ("", False),
        ("not-an-email", False),
    ]
    for email, expected in tests:
        result = validate_email(email)
        status = "✓" if result == expected else "✗"
        print(f"  {status} validate_email({email!r}) = {result}")
