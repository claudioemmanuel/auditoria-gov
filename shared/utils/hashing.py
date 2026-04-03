import hashlib
import hmac
import re


def hash_cpf(cpf: str, salt: str) -> str:
    """Hash a CPF using HMAC-SHA256 for deterministic ER matching."""
    cleaned = re.sub(r"\D", "", cpf)
    return hmac.new(salt.encode(), cleaned.encode(), hashlib.sha256).hexdigest()
