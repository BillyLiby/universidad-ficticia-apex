"""Cifrado de campos sensibles en reposo (Fase II-B).

No se implementa ningún algoritmo propio: se usa Fernet, de la biblioteca
'cryptography', que combina AES-128 en modo CBC para confidencialidad con
HMAC-SHA256 para integridad/autenticidad (cifrado autenticado). Cada
mensaje incluye un vector de inicialización aleatorio y una marca de
tiempo, por lo que cifrar el mismo texto dos veces produce resultados
distintos.

La clave NUNCA se guarda junto con los datos cifrados ni en el código
fuente: se lee de la variable de entorno APEX_ENCRYPTION_KEY. Si falta,
la aplicación falla de forma explícita en vez de usar una clave por
defecto insegura.
"""
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

ENV_VAR = "APEX_ENCRYPTION_KEY"


@lru_cache(maxsize=1)
def _fernet():
    key = os.environ.get(ENV_VAR)
    if not key:
        raise RuntimeError(
            f"Falta la variable de entorno {ENV_VAR}. Genera una clave con "
            "generate_key.py y expórtala antes de iniciar la aplicación "
            "(ver README)."
        )
    return Fernet(key.encode())


def encrypt_field(plaintext):
    """Cifra un texto. Devuelve None si plaintext es None/vacío."""
    if not plaintext:
        return None
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_field(token):
    """Descifra un token. Devuelve None si el token falta o fue alterado
    (integridad violada), en vez de lanzar una excepción hacia la vista."""
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        return None
