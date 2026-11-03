"""Rotación de la clave de cifrado (Fase II-C).

A diferencia de SECRET_KEY o DB_PASSWORD, la clave de cifrado NO se puede
simplemente reemplazar: los datos ya guardados (el teléfono de cada
estudiante) fueron cifrados con la clave ANTERIOR, y con una clave nueva
dejarían de poder descifrarse. Este script:

  1. Lee cada teléfono cifrado con la clave ANTIGUA.
  2. Lo descifra.
  3. Lo vuelve a cifrar con la clave NUEVA.
  4. Guarda el resultado en la base de datos.

Uso:
    python rotate_encryption_key.py CLAVE_ANTIGUA CLAVE_NUEVA

Después de ejecutarlo con éxito, actualiza APEX_ENCRYPTION_KEY en tu .env
con la clave nueva y reinicia la aplicación. Conserva la clave antigua en
un lugar seguro solo hasta confirmar que todo funciona; luego trátala
como revocada (no debe volver a usarse).
"""
import sys

from cryptography.fernet import Fernet, InvalidToken

from db import DB_PATH, get_db


def rotate(old_key, new_key):
    old_f = Fernet(old_key.encode())
    new_f = Fernet(new_key.encode())
    conn = get_db()
    rows = conn.execute("SELECT id, student_id, phone_encrypted FROM students").fetchall()
    updated, sin_dato = 0, 0
    for row in rows:
        token = row["phone_encrypted"]
        if not token:
            sin_dato += 1
            continue
        try:
            plano = old_f.decrypt(token.encode()).decode()
        except InvalidToken:
            print(f"AVISO: no se pudo descifrar el registro {row['student_id']} con la clave antigua; se omite.")
            continue
        nuevo_token = new_f.encrypt(plano.encode()).decode()
        conn.execute("UPDATE students SET phone_encrypted = ? WHERE id = ?", (nuevo_token, row["id"]))
        updated += 1
    conn.commit()
    conn.close()
    print(f"Listo. {updated} registro(s) re-cifrados con la clave nueva, {sin_dato} sin dato.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python rotate_encryption_key.py CLAVE_ANTIGUA CLAVE_NUEVA")
        sys.exit(1)
    rotate(sys.argv[1], sys.argv[2])
