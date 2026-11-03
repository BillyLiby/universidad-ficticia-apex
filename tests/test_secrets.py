"""Fase II-C: no quedan credenciales escritas en el código; todo se carga
desde variables de entorno (.env)."""
import pathlib
import unittest


class TestSecrets(unittest.TestCase):
    def test_config_no_tiene_credenciales_literales(self):
        src = pathlib.Path("config.py").read_text(encoding="utf-8")
        self.assertNotIn("clave-secreta-de-laboratorio-123", src)
        self.assertNotIn("Lab-Password-Ficticia-2026", src)
        self.assertIn("os.environ", src)

    def test_env_example_no_tiene_valores_reales(self):
        src = pathlib.Path(".env.example").read_text(encoding="utf-8")
        for line in src.splitlines():
            if line.startswith("APEX_") and "=" in line:
                self.assertEqual(line.split("=", 1)[1].strip(), "", line)

    def test_variables_cargadas_tienen_nombres_correctos(self):
        import config
        self.assertTrue(config.SECRET_KEY)
        self.assertTrue(config.DB_PASSWORD)
        self.assertNotEqual(config.SECRET_KEY, "clave-secreta-de-laboratorio-123")
        self.assertNotEqual(config.DB_PASSWORD, "Lab-Password-Ficticia-2026")


if __name__ == "__main__":
    unittest.main(verbosity=2)
