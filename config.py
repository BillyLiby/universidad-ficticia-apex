"""Configuración de la aplicación.

CORREGIDO (Fase II-C): ya no hay credenciales escritas en el código.
Los valores se leen de variables de entorno, cargadas desde un archivo
.env que NUNCA se sube al repositorio (ver .gitignore). Si falta alguna,
la aplicación falla de forma explícita en vez de usar un valor por
defecto inseguro.
"""
import os

from dotenv import load_dotenv

load_dotenv(override=True)  # .env manda siempre, incluso si la terminal ya
# tenía definida la misma variable con un valor distinto (evita confusiones
# como usar sin querer una clave vieja que quedó en una sesión de PowerShell).


def _require(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Falta la variable de entorno {name}. Copia .env.example a .env "
            "y completa sus valores antes de iniciar la aplicación (ver SECRETS.md)."
        )
    return value


SECRET_KEY = _require("APEX_SECRET_KEY")
DB_PASSWORD = _require("APEX_DB_PASSWORD")
DB_PATH = "portal.db"
