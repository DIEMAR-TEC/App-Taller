"""A dónde va cada uno al entrar: el chofer a informar fallas; el taller,
desde el celular, a la pantalla de la handheld."""
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
# Un rol armado a mano que reporta fallas y además ve vencimientos y services.
CHOFER_AMPLIADO = {"id": 3, "nombre": "Chofer", "rol": "choferes_ruta",
                   "modulos": ["choferes", "vencimientos", "flota"]}
SUCURSAL = {"id": 4, "nombre": "Sucursal", "rol": "sucursal", "modulos": ["choferes", "solicitudes"]}


IPHONE = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1"
ANDROID = "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 Chrome/130.0 Mobile Safari/537.36"
MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
APK = "Mozilla/5.0 (Linux; Android 8.1; TC51) AppleWebKit/537.36 Chrome/69.0 Mobile Safari/537.36 TitanHandheld/1.4"
ENCARGADO = {"id": 5, "nombre": "Encargado", "rol": "encargado", "administra": True,
             "modulos": ["gomeria", "repuestos", "ordenes"]}
OFICINA = {"id": 6, "nombre": "Oficina", "rol": "oficina", "modulos": ["combustible", "vencimientos"]}


def pedir(ruta, usuario, agente="", galleta=""):
    h = object.__new__(app.App)
    h.path = ruta
    h.headers = {"User-Agent": agente, "Cookie": galleta}
    h._es_https = lambda: True
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
        h = pedir("/handheld", CHOFER)
        h._redirigir.assert_called_once_with("/choferes/")

    def test_el_chofer_que_entra_por_la_portada_va_a_fallas(self):
        for usuario in (CHOFER, CHOFER_AMPLIADO):
            h = pedir("/", usuario)
            h._redirigir.assert_called_once_with("/choferes/")

    def test_el_qr_de_la_unidad_la_deja_elegida(self):
        for ruta in ("/handheld/u/AD247MQ", "/gomeria/u/AD247MQ"):
            h = pedir(ruta, CHOFER_AMPLIADO)
            h._redirigir.assert_called_once_with("/choferes/?patente=AD247MQ")

    def test_la_sucursal_sigue_en_la_portada(self):
        h = pedir("/", SUCURSAL)
        h._redirigir.assert_not_called()

    def test_el_que_tiene_gomeria_se_queda(self):
        h = pedir("/handheld", GOMERO)
        h._redirigir.assert_not_called()

    def test_sin_sesion_va_al_login(self):
        h = pedir("/handheld", None)
        h._redirigir.assert_not_called()
        h._exigir_sesion.assert_called()




class TallerEnElCelular(unittest.TestCase):
    def test_en_el_celular_va_a_la_handheld(self):
        for agente in (IPHONE, ANDROID):
            for usuario in (GOMERO, ENCARGADO):
                h = pedir("/", usuario, agente)
                h._redirigir.assert_called_once_with("/handheld")

    def test_la_pantalla_movil_vieja_lleva_a_la_handheld(self):
        h = pedir("/movil", GOMERO, ANDROID)
        h._redirigir.assert_called_once_with("/handheld")
        # Con la unidad (desde el registro, para abrir una orden) se queda.
        h = pedir("/movil?patente=AD247MQ", GOMERO, ANDROID)
        h._redirigir.assert_not_called()

    def test_en_la_computadora_y_en_la_apk_nada_cambia(self):
        for agente in (MAC, APK):
            h = pedir("/", ENCARGADO, agente)
            h._redirigir.assert_not_called()

    def test_sin_taller_se_queda_en_el_sistema(self):
        h = pedir("/", OFICINA, IPHONE)
        h._redirigir.assert_not_called()

    def test_sistema_completo_se_recuerda(self):
        h = pedir("/?vista=completa", ENCARGADO, IPHONE)
        destino, = h._redirigir.call_args.args
        self.assertEqual(destino, "/")
        self.assertIn("vista=completa", h._redirigir.call_args.kwargs["cookie"])
        h = pedir("/", ENCARGADO, IPHONE, galleta="vista=completa")
        h._redirigir.assert_not_called()
        # «Versión handheld» borra la elección.
        h = pedir("/handheld?vista=handheld", ENCARGADO, IPHONE, galleta="vista=completa")
        self.assertIn("Max-Age=0", h._redirigir.call_args.kwargs["cookie"])

    def test_el_boton_de_vuelta_solo_con_el_sistema_completo_en_el_celular(self):
        h = pedir("/", ENCARGADO, IPHONE, galleta="vista=completa")
        h.usuario = ENCARGADO
        h.ruta_original = "/ordenes"
        self.assertIn("Versión handheld", h._boton_handheld())
        h = pedir("/", ENCARGADO, MAC, galleta="vista=completa")
        h.usuario = ENCARGADO
        h.ruta_original = "/ordenes"
        self.assertEqual(h._boton_handheld(), "")


if __name__ == "__main__":
    unittest.main()
