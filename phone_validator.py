import re


def validate_phone(phone: str) -> bool:
    """Validate a phone number.

    Supports common formats like +1-555-123-4567, (555) 123-4567,
    555-123-4567, 5551234567, and international numbers.
    Strips formatting and checks for 7–15 digits (per E.164).
    Returns True if valid, False otherwise.
    """
    if not phone or not isinstance(phone, str):
        return False

    # Remove common formatting characters
    digits = re.sub(r'[\s\-\(\)\.\+]', '', phone)

    # Must be all digits after stripping
    if not digits.isdigit():
        return False

    # E.164: 7-15 digits (without +)
    return 7 <= len(digits) <= 15


if __name__ == "__main__":
    tests = [
        ("+1-555-123-4567", True),
        ("(555) 123-4567", True),
        ("555-123-4567", True),
        ("5551234567", True),
        ("+44 20 7946 0958", True),
        ("123", False),
        ("", False),
        ("abc-def-ghij", False),
        ("12345678901234567890", False),
    ]
    for phone, expected in tests:
        result = validate_phone(phone)
        status = "✓" if result == expected else "✗"
        print(f"  {status} validate_phone({phone!r}) = {result}")
