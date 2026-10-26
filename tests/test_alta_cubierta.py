"""El alta de una cubierta con los campos numéricos vacíos."""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "gomeria"))
import base


class Resultado:
    def fetchone(self):
        return {"id": 1}


class Base:
    def __init__(self):
        self.consultas = []

    def execute(self, consulta, valores=()):
        self.consultas.append((" ".join(consulta.split()), valores))
        return Resultado()


class AltaCubierta(unittest.TestCase):
    def test_costo_y_remanente_vacios_van_como_sin_dato(self):
        """El formulario manda "" y la columna es numérica."""
        cx = Base()
        original = base._hay_vidas
        base._hay_vidas = lambda cx: False
        try:
            base.alta_cubierta(cx, "457", marca="Michelin",
                               costo_compra="", remanente_mm="")
        finally:
            base._hay_vidas = original
        alta = cx.consultas[0][1]
        self.assertEqual(alta[4], None)
        self.assertEqual(alta[5], None)

    def test_los_numeros_con_coma_se_entienden(self):
        cx = Base()
        original = base._hay_vidas
        base._hay_vidas = lambda cx: False
        try:
            base.alta_cubierta(cx, "458", costo_compra="172830,58", remanente_mm="16")
        finally:
            base._hay_vidas = original
        self.assertEqual(cx.consultas[0][1][4], 172830.58)
        self.assertEqual(cx.consultas[0][1][5], 16.0)


if __name__ == "__main__":
    unittest.main()
