"""El chofer que abre la app de la handheld va directo a informar fallas."""
import os
import sys
import unittest
from unittest import mock

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, ".."))
sys.path.insert(0, os.path.join(AQUI, "..", "gomeria"))

import app  # noqa: E402

CHOFER = {"id": 1, "nombre": "Chofer", "rol": "chofer", "modulos": ["choferes"]}
GOMERO = {"id": 2, "nombre": "Gomero", "rol": "operario", "modulos": ["gomeria", "choferes"]}


def pedir(ruta, usuario):
    h = object.__new__(app.App)
    h.path = ruta
    h.headers = {}
    h.usuario = None

    def sesion():
        h.usuario = usuario
        return usuario is not None

    h._sesion = sesion
    h._redirigir = mock.Mock(name="redirigir")
    h._exigir_sesion = mock.Mock(name="exigir", return_value=False)
    h.do_GET()
    return h


class ChoferEnLaHandheld(unittest.TestCase):
    def test_el_chofer_va_a_fallas(self):
        for ruta in ("/handheld", "/handheld/u/AD247MQ"):
            h = pedir(ruta, CHOFER)
            h._redirigir.assert_called_once_with("/choferes/")

    def test_el_que_tiene_gomeria_se_queda(self):
        h = pedir("/handheld", GOMERO)
        h._redirigir.assert_not_called()

    def test_sin_sesion_va_al_login(self):
        h = pedir("/handheld", None)
        h._redirigir.assert_not_called()
        h._exigir_sesion.assert_called()


if __name__ == "__main__":
    unittest.main()
