"""Que cualquier satelital termine en la misma lectura estándar.

Hawk por API no se prueba contra el servidor (pide usuario y contraseña):
se prueban las formas en que un .asmx puede contestar y que de todas salga
la misma fila. Y que las cuentas se lean con sus secrets, de a una, sin que
la que falla frene a las otras.
"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "gomeria"))
import leer_km
import satelitales as sat
from satelitales import hawk_api

XML_CAMPOS = """<?xml version="1.0" encoding="utf-8"?>
<ArrayOfUnit xmlns="http://tempuri.org/">
  <Unit><idGPS>29627</idGPS><Patente>AE 527 FA</Patente>
        <Kilometraje>120000,5</Kilometraje><FechaServer>11/09/2026 09:00</FechaServer></Unit>
  <Unit><idGPS>30001</idGPS><Patente>VXO389</Patente><Kilometraje></Kilometraje></Unit>
</ArrayOfUnit>"""

XML_CON_JSON = """<?xml version="1.0" encoding="utf-8"?>
<string xmlns="http://tempuri.org/">[{"idGPS":29627,"Descripcion":"AF527AE",
"Odometro":120000.5,"FechaServer":"/Date(1789128000000)/"}]</string>"""

SOAP = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body>
<getUnitsResponse xmlns="http://tempuri.org/"><getUnitsResult>{"d":[{"Patente":"AE527FA",
"Kilometraje":"120.000,5","Fecha":"2026-09-11T12:00:00Z"}]}</getUnitsResult>
</getUnitsResponse></soap:Body></soap:Envelope>"""

WSDL = """<?xml version="1.0" encoding="utf-8"?>
<wsdl:definitions xmlns:wsdl="http://schemas.xmlsoap.org/wsdl/"
  xmlns:s="http://www.w3.org/2001/XMLSchema" targetNamespace="http://hawk/">
 <wsdl:types><s:schema><s:element name="getUnits"><s:complexType><s:sequence>
   <s:element name="usuario" type="s:string"/><s:element name="contrasena" type="s:string"/>
 </s:sequence></s:complexType></s:element></s:schema></wsdl:types>
</wsdl:definitions>"""


class Respuestas(unittest.TestCase):
    def leer(self, texto):
        with mock.patch.object(hawk_api, "leer", return_value=texto):
            return hawk_api.lecturas({"usuario": "u", "clave": "c"})

    def test_las_tres_formas_dan_la_misma_lectura(self):
        for texto in (XML_CAMPOS, XML_CON_JSON, SOAP):
            fila = self.leer(texto)[0]
            self.assertEqual(fila["Patente"], "AE527FA")
            self.assertEqual(fila["Kilometraje"], 120000.5)
            self.assertEqual(fila["Ultimo_reporte"], "2026-09-11 09:00:00")

    def test_la_unidad_sin_km_viene_vacia_y_no_inventa(self):
        filas = self.leer(XML_CAMPOS)
        self.assertEqual(len(filas), 2)
        self.assertIsNone(filas[1]["Kilometraje"])

    def test_sin_campo_de_km_el_error_dice_que_llego(self):
        with self.assertRaises(SystemExit) as e:
            self.leer('[{"Patente":"AE527FA","Velocidad":80}]')
        self.assertIn("Velocidad", str(e.exception))

    def test_campos_con_otro_nombre_por_configuracion(self):
        with mock.patch.object(hawk_api, "leer", return_value='[{"Dom":"AE527FA","Cuenta":5}]'):
            (fila,) = hawk_api.lecturas({}, {"campos": {"patente": "Dom", "km": "Cuenta"}})
        self.assertEqual((fila["Patente"], fila["Kilometraje"]), ("AE527FA", 5.0))


class Parametros(unittest.TestCase):
    def test_los_nombres_salen_del_wsdl(self):
        with mock.patch.object(hawk_api, "_pedir", return_value=WSDL):
            nombres, ns = hawk_api._wsdl("http://x/Api.asmx", "getUnits")
        self.assertEqual((nombres, ns), (["usuario", "contrasena"], "http://hawk/"))
        self.assertEqual(hawk_api._parametros(nombres, {"usuario": "u", "clave": "c"}, {}),
                         {"usuario": "u", "contrasena": "c"})

    def test_sin_wsdl_se_usan_los_de_la_configuracion(self):
        salida = hawk_api._parametros(None, {"usuario": "u", "clave": "c"},
                                      {"parametros": {"usuario": "login", "clave": "pwd",
                                                      "idEmpresa": 7}})
        self.assertEqual(salida, {"login": "u", "pwd": "c", "idEmpresa": "7"})


class Ayudas(unittest.TestCase):
    def test_numeros(self):
        for texto in (120000.5, "120000,5", "120.000,5", "120,000.5", "120000.5 km"):
            self.assertEqual(sat.numero(texto), 120000.5)
        self.assertEqual(sat.numero("120,000"), 120000.0)
        self.assertIsNone(sat.numero(""))

    def test_fuentes_en_sql(self):
        self.assertEqual(sat.en_sql(), "('hawk')")


class Cuentas(unittest.TestCase):
    def setUp(self):
        self.cuentas = [
            {"empresa": "Uno", "proveedor": "hawk_api", "respaldo": ["hawk_web"],
             "credenciales": {"usuario": "U1", "clave": "C1"}},
            {"empresa": "Dos", "proveedor": "hawk_api",
             "credenciales": {"usuario": "U2", "clave": "C2"}},
        ]
        self.secretos = {"SECRETOS": json.dumps({"U1": "a", "C1": "b", "U2": "c", "C2": "d"})}

    def test_los_secrets_llegan_por_el_json_del_workflow(self):
        with mock.patch.dict(os.environ, self.secretos):
            self.assertEqual(sat.credenciales(self.cuentas[0]), {"usuario": "a", "clave": "b"})

    def test_sin_secret_avisa_cual_falta(self):
        with mock.patch.dict(os.environ, {"SECRETOS": "{}"}), self.assertRaises(SystemExit) as e:
            sat.credenciales(self.cuentas[1])
        self.assertIn("U2", str(e.exception))

    def test_si_la_api_falla_entra_el_respaldo(self):
        lectura = [{"Patente": "AE527FA", "Kilometraje": 10.0}]
        with mock.patch.dict(os.environ, self.secretos), \
             mock.patch.object(hawk_api, "lecturas", side_effect=RuntimeError("HTTP 500")), \
             mock.patch("satelitales.hawk_web.lecturas", return_value=lectura):
            self.assertEqual(leer_km.leer_cuenta(self.cuentas[0]), ("hawk", lectura))

    def test_una_cuenta_caida_no_frena_a_la_otra(self):
        subidas = []
        def lecturas(cred, opciones):
            if cred["usuario"] == "a":
                raise RuntimeError("caída")
            return [{"Patente": "AE527FA", "Kilometraje": 10.0}]
        with mock.patch.dict(os.environ, self.secretos), \
             mock.patch.object(sat, "cuentas", return_value=self.cuentas), \
             mock.patch.object(hawk_api, "lecturas", side_effect=lecturas), \
             mock.patch("satelitales.hawk_web.lecturas", side_effect=RuntimeError("sin chrome")), \
             mock.patch.object(leer_km.subir_odometros, "subir",
                               side_effect=lambda f, fuente: subidas.append(fuente) or 1), \
             self.assertRaises(SystemExit) as e:
            leer_km.main()
        self.assertEqual(subidas, ["hawk"])
        self.assertIn("Uno", str(e.exception))
        self.assertNotIn("Dos", str(e.exception))

    def test_el_archivo_de_cuentas_es_valido(self):
        for c in sat.cuentas():
            self.assertIn(c["proveedor"], sat.PROVEEDORES)
            for r in c.get("respaldo") or []:
                self.assertIn(r, sat.PROVEEDORES)
            self.assertTrue(c.get("credenciales"))


if __name__ == "__main__":
    unittest.main()
