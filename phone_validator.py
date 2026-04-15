import re


def validate_phone(phone: str) -> bool:
    """Validate a phone number.

    Supports common formats:
      - (123) 456-7890
      - 123-456-7890
      - +1-123-456-7890
      - 1234567890
      - +11234567890

    Returns True if valid, False otherwise.
    """
    if not phone or not isinstance(phone, str):
        return False

    # Strip all formatting characters, keeping only digits and leading +
    stripped = phone.strip()
    # Remove common separators and formatting
    digits = re.sub(r'[\s\-\(\)\.\+]', '', stripped)

    if not digits.isdigit():
        return False

    # Accept 7 digits (local), 10 digits (US), or 11 digits (with country code)
    if len(digits) not in (7, 10, 11):
        return False

    # If 11 digits, first digit should be a country code (1 for US/CA)
    if len(digits) == 11 and digits[0] == '0':
        return False

    return True


if __name__ == "__main__":
    tests = [
        ("(123) 456-7890", True),
        ("123-456-7890", True),
        ("+1-123-456-7890", True),
        ("1234567890", True),
        ("+11234567890", True),
        ("456-7890", True),
        ("", False),
        ("123", False),
        ("abc-def-ghij", False),
        ("123456789012345", False),
    ]
    for phone, expected in tests:
        result = validate_phone(phone)
        status = "✓" if result == expected else "✗"
        print(f"  {status} validate_phone({phone!r}) = {result}")
