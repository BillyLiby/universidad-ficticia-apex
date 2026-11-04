"""Registro de eventos de seguridad (Fase II-E).

Reglas seguidas en este módulo:
- NUNCA se registran: contraseñas (ni su hash), tokens de sesión, claves
  criptográficas, credenciales de base de datos, ni el valor de un dato
  cifrado (p. ej. el teléfono del estudiante, protegido en la Fase II-B).
- Se registra solo lo necesario para auditar quién hizo qué: el actor
  (correo de quien actúa), el tipo de evento, un objetivo mínimo (p. ej.
  el ID de un estudiante, nunca su nombre completo ni su teléfono), el
  resultado, y la IP de origen.
- Cada línea es un objeto JSON (un evento por línea), fácil de leer,
  buscar y procesar con herramientas de monitoreo.
- Todo texto que vino del usuario se sanea antes de registrarse, para
  evitar inyección de líneas de registro (alguien escribiendo un salto
  de línea en un campo para fabricar una entrada de auditoría falsa).
"""
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "security.log")

# Campos que JAMÁS deben llegar a un registro, ni siquiera por error del
# programador. Es una barrera adicional a la disciplina de no pasarlos.
_FORBIDDEN_KEYS = {
    "password", "password_hash", "contrasena", "contraseña",
    "token", "session", "cookie",
    "secret", "secret_key", "db_password", "encryption_key",
    "phone", "phone_encrypted", "telefono",
}

_logger = logging.getLogger("apex.security")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=3, encoding="utf-8")
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)
    _logger.propagate = False


def _sanitize(value):
    """Evita inyección de líneas de registro: un salto de línea en un
    valor del usuario podría simular una entrada de auditoría falsa."""
    if value is None:
        return None
    text = str(value)
    text = text.replace("\n", "\\n").replace("\r", "\\r")
    return text[:200]  # límite razonable para no inflar el log


def log_event(event, actor=None, target=None, outcome=None, ip=None, **extra):
    """Escribe una línea de auditoría en JSON.

    event: tipo de evento ('login_success', 'expediente_view', etc.)
    actor: quién realizó la acción (correo del usuario autenticado)
    target: sobre qué se actuó (p. ej. un student_id; nunca datos sensibles)
    outcome: 'success', 'failed', 'rejected', 'error', etc.
    extra: campos adicionales SIN información sensible (se valida el
           nombre de cada campo contra la lista prohibida).
    """
    for key in extra:
        if key.lower() in _FORBIDDEN_KEYS:
            raise ValueError(f"Campo no permitido en el registro de seguridad: {key}")
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event": event,
        "actor": _sanitize(actor),
        "target": _sanitize(target),
        "outcome": outcome,
        "ip": ip,
    }
    for key, value in extra.items():
        entry[key] = _sanitize(value)
    _logger.info(json.dumps(entry, ensure_ascii=False))


def read_recent(n=20):
    """Devuelve las últimas n líneas del log de seguridad (para mostrarlas
    en el panel de administración). Solo lectura."""
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [line.strip() for line in lines[-n:]]
