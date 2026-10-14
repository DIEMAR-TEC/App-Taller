"""El stock mínimo de cubiertas: qué cuenta cada regla y cuándo avisa.

    295 · BF GOODRICH          cuenta las 295 de esa marca, nuevas o recapadas
    295 · dirección · nueva    cuenta las 295 de dirección sin recapar
"""
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "gomeria"))
import stock_minimo as sm


DEPOSITO = [
    {"medida": "295/80R22.5", "marca": "BF GOODRICH", "tipo": "direccion", "recapados": 0},
    {"medida": "295", "marca": "BF Goodrich", "tipo": "traccion", "recapados": 1},
    {"medida": "295", "marca": "FATE", "tipo": "direccion", "recapados": 0},
    {"medida": "295", "marca": "FATE", "tipo": None, "recapados": 2},
    {"medida": "275", "marca": "FATE", "tipo": "direccion", "recapados": 0},
]


class Resultado:
    def __init__(self, filas):
        self.filas = filas

    def fetchall(self):
        return self.filas

    def fetchone(self):
        return self.filas[0] if self.filas else None


class Base:
    """Devuelve las reglas o el depósito según la consulta."""
    def __init__(self, reglas):
        self.reglas = reglas

    def execute(self, sql, valores=()):
        if "from cubiertas_stock_minimo" in sql:
            return Resultado(self.reglas)
        if "from cubiertas c" in sql:
            return Resultado(DEPOSITO)
        raise AssertionError(sql)


def regla(id, medida, minimo, marca=None, tipo=None, condicion=None, activa=True):
    return {"id": id, "medida": medida, "marca": marca, "tipo": tipo,
            "condicion": condicion, "minimo": minimo, "activa": activa, "nota": None}


class StockMinimo(unittest.TestCase):
    def test_cuenta_por_medida_marca_tipo_y_condicion(self):
        filas = sm.reglas(Base([
            regla(1, "295", 10, marca="Bf Goodrich"),
            regla(2, "295", 5, tipo="direccion", condicion="nueva"),
            regla(3, "295", 2, condicion="recapada"),
            regla(4, "295", 1),
        ]))
        hay = {r["id"]: r["hay"] for r in filas}
        self.assertEqual(hay, {1: 2, 2: 2, 3: 2, 4: 4})
        self.assertEqual(filas[0]["nombre"], "295 · Bf Goodrich")
        self.assertEqual(filas[1]["nombre"], "295 · dirección · nueva")

    def test_avisa_solo_por_debajo_y_si_esta_activa(self):
        alertas = sm.alertas(Base([
            regla(1, "295", 10, marca="BF GOODRICH"),
            regla(2, "295", 2, tipo="direccion"),
            regla(3, "1000", 4),
            regla(4, "295", 50, activa=False),
        ]))
        por_id = {a["clave"]: a for a in alertas}
        self.assertEqual(set(por_id), {"1", "3"})
        self.assertEqual(por_id["1"]["severidad"], "media")
        self.assertEqual(por_id["3"]["severidad"], "grave")
        self.assertEqual(por_id["1"]["titulo"], "Quedan 2 cubiertas 295 · BF GOODRICH")

    def test_medida_corta(self):
        self.assertEqual(sm.medida_corta("295/80R22.5"), "295")
        self.assertEqual(sm.medida_corta("1000×20"), "1000")
        self.assertIsNone(sm.medida_corta(""))


if __name__ == "__main__":
    unittest.main()
