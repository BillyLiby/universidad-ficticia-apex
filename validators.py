"""Validación de entradas (Fase I-A). Lista blanca: se acepta solo lo esperado.
IMPORTANTE: validar NO sustituye a parametrizar SQL, escapar HTML ni evitar
concatenar comandos; son capas distintas (ver informe)."""
import math
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
STUDENT_ID_RE = re.compile(r"^\d{7}$")
LETTERS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
NAME_RE = re.compile(rf"^[{LETTERS}]+(?:[ '-][{LETTERS}]+)*$")
SEARCH_RE = re.compile(rf"^[{LETTERS}0-9 .@'_-]*$")


def valid_email(value):
    return isinstance(value, str) and len(value) <= 254 and bool(EMAIL_RE.match(value))


def valid_student_id(value):
    return isinstance(value, str) and bool(STUDENT_ID_RE.match(value))


def valid_name(value):
    return isinstance(value, str) and 1 <= len(value) <= 50 and bool(NAME_RE.match(value))


def valid_grade(value):
    """Devuelve la nota como float (0-100) o None si no es válida."""
    try:
        g = float(str(value).strip())
    except (ValueError, TypeError):
        return None
    if not math.isfinite(g) or g < 0 or g > 100:
        return None
    return g


def valid_search(value):
    return isinstance(value, str) and len(value) <= 50 and bool(SEARCH_RE.match(value))


def valid_password(value):
    return (isinstance(value, str) and 8 <= len(value) <= 128
            and any(c.isalpha() for c in value) and any(c.isdigit() for c in value))


def valid_comment(value):
    return isinstance(value, str) and 1 <= len(value.strip()) <= 500
