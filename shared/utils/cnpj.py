import re


def clean_cnpj(cnpj: str) -> str:
    """Remove all non-digit characters from a CNPJ."""
    return re.sub(r"\D", "", cnpj)


def format_cnpj(cnpj: str) -> str:
    """Format a CNPJ: 00.000.000/0001-00."""
    cleaned = clean_cnpj(cnpj)
    if len(cleaned) != 14:
        return cleaned
    return f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}/{cleaned[8:12]}-{cleaned[12:]}"


def validate_cnpj(cnpj: str) -> bool:
    """Validate a CNPJ check digits."""
    cleaned = clean_cnpj(cnpj)
    if len(cleaned) != 14:
        return False

    # All same digits is invalid
    if len(set(cleaned)) == 1:
        return False

    # First check digit
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cleaned[i]) * weights_1[i] for i in range(12))
    remainder = total % 11
    digit_1 = 0 if remainder < 2 else 11 - remainder
    if int(cleaned[12]) != digit_1:
        return False

    # Second check digit
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    total = sum(int(cleaned[i]) * weights_2[i] for i in range(13))
    remainder = total % 11
    digit_2 = 0 if remainder < 2 else 11 - remainder
    return int(cleaned[13]) == digit_2
