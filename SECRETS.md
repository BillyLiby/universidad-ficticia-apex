# Gestión de secretos (Fase II-C)

## Credenciales que estaban escritas en el código

Antes de esta corrección, `config.py` contenía:

```python
SECRET_KEY = "clave-secreta-de-laboratorio-123"
DB_PASSWORD = "Lab-Password-Ficticia-2026"
```

Ambas quedaron además guardadas en el **historial de Git** desde el primer
commit del proyecto ("feat: app base del portal universitario"), porque
Git conserva cada versión de cada archivo. Retirarlas de `config.py` no
las borra del historial: ese problema se aborda en la Fase II-D
(detección de secretos en Git). Por eso, además de retirarlas, se
**rotaron** (se generaron valores nuevos): el valor viejo, aunque ya no
se use, debe tratarse como comprometido.

## Dónde quedan ahora

En variables de entorno, cargadas desde un archivo `.env` que **nunca se
sube al repositorio** (está en `.gitignore`):

| Variable | Qué protege |
|---|---|
| `APEX_SECRET_KEY` | Firma las sesiones de Flask (cookies de inicio de sesión) |
| `APEX_DB_PASSWORD` | Representa una credencial de base de datos (ejemplo; SQLite local no la usa, pero así se vería en una app con una base de datos externa) |
| `APEX_ENCRYPTION_KEY` | Cifra el teléfono de los estudiantes (Fase II-B) |

`config.py` las lee con `os.environ.get(...)`, y si alguna falta, la
aplicación se niega a arrancar con un mensaje explícito, en vez de usar
un valor por defecto inseguro.

El repositorio incluye `.env.example` (sin valores reales) como
plantilla, para que cualquiera pueda crear su propio `.env` local.

## Control de permisos

- El archivo `.env` solo debe ser legible por el usuario que ejecuta la
  aplicación. En Windows, esto se puede forzar quitando los permisos
  heredados y dejando solo el usuario actual:

  ```powershell
  icacls .env /inheritance:r /grant:r "$env:USERNAME:F"
  ```

- `.env` nunca se comparte por correo, chat o captura de pantalla, ni se
  sube a servicios de almacenamiento en la nube sin cifrar.
- En un entorno de equipo o producción, el control de acceso correcto es
  una bóveda de secretos (HashiCorp Vault, AWS Secrets Manager, Azure Key
  Vault, GCP Secret Manager), donde el acceso se concede por rol/servicio
  (no por archivo compartido), queda registrado en un log de auditoría, y
  los secretos pueden tener una vida corta (*leases*) que expiran solos.
  Para esta tarea de laboratorio, con una sola persona y un entorno
  local, `.env` + control de permisos del sistema de archivos es
  proporcional al riesgo; en un equipo de varias personas o en
  producción, correspondería usar una bóveda.

## Procedimiento de rotación

Aplica a `APEX_SECRET_KEY` y `APEX_DB_PASSWORD`:

1. Generar un valor nuevo: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
2. Actualizar `.env` con el valor nuevo (nunca tocar el código).
3. Reiniciar la aplicación para que tome el valor nuevo.
4. Confirmar el efecto esperado: al rotar `APEX_SECRET_KEY`, las sesiones
   abiertas quedan invalidadas (todos deben iniciar sesión de nuevo); es
   el comportamiento correcto, no un error.
5. Registrar la rotación (fecha y motivo), para trazabilidad.

Aplica a `APEX_ENCRYPTION_KEY` (requiere un paso adicional, porque ya hay
datos cifrados con la clave anterior):

1. Generar la clave nueva: `python generate_key.py`
2. Ejecutar `python rotate_encryption_key.py CLAVE_ANTIGUA CLAVE_NUEVA`,
   que descifra cada dato con la clave antigua y lo vuelve a cifrar con
   la nueva, **antes** de cambiar nada más.
3. Recién entonces actualizar `APEX_ENCRYPTION_KEY` en `.env` con la
   clave nueva.
4. Reiniciar la aplicación y verificar que los datos (por ejemplo, un
   expediente) se sigan mostrando correctamente.

## Procedimiento de revocación

Cuando se sospecha que un secreto se expuso (por ejemplo, quedó en un
commit de Git, como ocurrió aquí):

1. Tratarlo como comprometido de inmediato, sin esperar confirmación.
2. Rotarlo siguiendo el procedimiento anterior.
3. Verificar que el valor viejo ya no esté en uso en ningún lado (código,
   `.env` de otros equipos, backups).
4. Si el secreto llegó a un repositorio Git (incluido el historial), no
   basta con rotarlo: el valor expuesto sigue siendo legible en commits
   anteriores. Este caso se documenta y demuestra en la Fase II-D.
