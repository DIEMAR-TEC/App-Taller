"""Los esqueletos de carga que el servidor pone en todas las pantallas.

El comportamiento se prueba en el navegador (esqueleto_smoke.cjs). Acá
solo que el archivo se sirva y que entre en el encabezado, sin defer: si
esperara al final de la carga, el "Cargando…" llegaría a verse.
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "gomeria"))
import app
from test_lateral import _pantalla


class Esqueleto(unittest.TestCase):
    def test_el_script_se_sirve(self):
        self.assertEqual(app.PANTALLAS["/esqueleto.js"][0], "esqueleto.js")
        self.assertTrue((RAIZ / "esqueleto.js").exists())

    def test_entra_en_el_encabezado_sin_defer(self):
        salida = _pantalla("/ordenes")
        cabeza = salida.split("</head>")[0]
        self.assertIn('<script src="/esqueleto.js"></script>', cabeza)

    def test_no_se_repite(self):
        propio = b'<html><head><script src="/esqueleto.js"></script></head><body></body></html>'
        self.assertEqual(_pantalla("/ordenes", propio).count("/esqueleto.js"), 1)


if __name__ == "__main__":
    unittest.main()
