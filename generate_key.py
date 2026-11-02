"""Genera una clave Fernet nueva para cifrar datos en reposo (Fase II-B).
Ejecutar UNA vez y guardar la clave como variable de entorno, nunca en el
código ni en el repositorio."""
from cryptography.fernet import Fernet

if __name__ == "__main__":
    print(Fernet.generate_key().decode())
