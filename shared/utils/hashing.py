import hashlib
import hmac
import re


def hash_cpf(cpf: str, salt: str) -> str:
    """Hash a CPF for LGPD compliance using HMAC-SHA256."""
    cleaned = re.sub(r"\D", "", cpf)
    return hmac.new(salt.encode(), cleaned.encode(), hashlib.sha256).hexdigest()


def mask_cpf(cpf: str) -> str:
    """Mask a CPF for display: ***.***.789-00."""
    cleaned = re.sub(r"\D", "", cpf)
    if len(cleaned) != 11:
        return "***.***.***-**"
    return f"***.***{cleaned[6:9]}-{cleaned[9:]}"
