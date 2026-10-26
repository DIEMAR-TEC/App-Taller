"""Que cualquier satelital termine en la misma lectura estándar.

Hawk por API no se prueba contra el servidor (pide usuario y contraseña):
se prueban las formas en que un .asmx puede contestar y que de todas salga
la misma fila. Y que las cuentas se lean con sus secrets, de a una, sin que
la que falla frene a las otras.
"""
import json
import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "gomeria"))
import leer_km
import subir_odometros as subir
import satelitales as sat
from satelitales import hawk_api

XML_CAMPOS = """<?xml version="1.0" encoding="utf-8"?>
<ArrayOfUnit xmlns="http://tempuri.org/">
  <Unit><idGPS>29627</idGPS><Patente>AE 527 FA</Patente>
        <Kilometraje>120000,5</Kilometraje><FechaServer>11/09/2026 09:00</FechaServer></Unit>
  <Unit><idGPS>30001</idGPS><Patente>VXO389</Patente><Kilometraje></Kilometraje></Unit>
</ArrayOfUnit>"""

# Lo que devuelve getUnits de verdad (20/10/2026), recortado a dos unidades.
GETUNITS = """<?xml version="1.0" encoding="utf-8"?>
<ArrayOfUnit xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://tempuri.org/">
  <Unit><GPSDate>2026-10-20T12:25:53</GPSDate><Vehicle>AA472IP_HC</Vehicle>
    <VehiclePlate>AA472IP_HC</VehiclePlate><Odometer>29358.74609375</Odometer>
    <Latitude>-34.706623077392578</Latitude><Longitude>-58.49969482421875</Longitude>
    <Speed>0</Speed><Heading>39</Heading></Unit>
  <Unit><GPSDate>2026-10-20T12:22:27</GPSDate><Vehicle>AA823XJ QUIÑONES GABRIEL</Vehicle>
    <VehiclePlate>AA823XJ</VehiclePlate><Odometer>359191.65625</Odometer>
    <Latitude>-31.359960556030273</Latitude><Longitude>-64.143867492675781</Longitude>
    <Speed>0</Speed><Heading>0</Heading></Unit>
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

    def test_getunits_real_toma_patente_y_odometro(self):
        filas = self.leer(GETUNITS)
        self.assertEqual([(subir._patente(f["Patente"]), f["Kilometraje"]) for f in filas],
                         [("AA472IP", 29358.74609375), ("AA823XJ", 359191.65625)])
        self.assertEqual(filas[1]["Ultimo_reporte"], "2026-10-20 12:22:27")
        # Y así quedan para la tabla: el _HC se va y el km se redondea.
        (p, _, km, _, _), _ = subir.filas_de(filas)
        self.assertEqual((p, km), ("AA472IP", 29358.75))

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

    def test_sin_parametros_va_por_get_con_usuario_y_clave_en_la_cabecera(self):
        pedidos = []
        def pedir(url, datos=None, cabeceras=None):
            pedidos.append((url, datos, cabeceras))
            if url.endswith("?WSDL"):
                raise RuntimeError("HTTP 404")
            return GETUNITS
        with mock.patch.object(hawk_api, "_pedir", side_effect=pedir):
            hawk_api.leer({"usuario": "u", "clave": "c"})
        url, datos, cabeceras = pedidos[-1]
        self.assertEqual((url, datos), (hawk_api.URL + "/getUnits", None))
        self.assertEqual(cabeceras["Authorization"], "Basic dTpj")

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

    def test_el_respaldo_entra_con_sus_propias_credenciales(self):
        cuenta = {"empresa": "Uno", "proveedor": "hawk_api",
                  "credenciales": {"usuario": "API_U", "clave": "API_C"},
                  "respaldo": [{"proveedor": "hawk_web",
                                "credenciales": {"usuario": "U1", "clave": "C1"}}]}
        recibidas = []
        lectura = [{"Patente": "AE527FA", "Kilometraje": 10.0}]
        # Sin los secrets de la API todavía cargados: entra la web con los suyos.
        with mock.patch.dict(os.environ, self.secretos), \
             mock.patch("satelitales.hawk_web.lecturas",
                        side_effect=lambda c, o: recibidas.append(c) or lectura):
            self.assertEqual(leer_km.leer_cuenta(cuenta), ("hawk", lectura))
        self.assertEqual(recibidas, [{"usuario": "a", "clave": "b"}])

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
                self.assertIn(r["proveedor"] if isinstance(r, dict) else r, sat.PROVEEDORES)
            self.assertTrue(c.get("credenciales"))


class ElWorkflow(unittest.TestCase):
    """Que el workflow pase los secrets que cuentas.json nombra, uno por uno.

    Pasaban todos juntos, con toJSON(secrets). GitHub lee ese volcado como
    una fuga de secretos: marca el workflow como posiblemente malicioso y lo
    deja esperando que alguien lo apruebe a mano. Del 24 al 26/10/2026 no
    entró un solo odómetro y nada lo avisó, porque el job nunca arrancó y el
    mail de error sale adentro del job.

    Nombrados, el riesgo se da vuelta: sumar una empresa a cuentas.json y
    olvidarse de su secret acá tampoco avisa hasta la madrugada siguiente.
    De eso se encarga la primera prueba.
    """

    def workflows(self):
        carpeta = RAIZ / ".github" / "workflows"
        archivos = sorted(carpeta.glob("*.yml")) + sorted(carpeta.glob("*.yaml"))
        self.assertTrue(archivos, "no se encontró ningún workflow")
        return [(a.name, a.read_text(encoding="utf-8")) for a in archivos]

    def test_el_workflow_nombra_todos_los_secrets_de_las_cuentas(self):
        texto = (RAIZ / ".github" / "workflows" / "odometros.yml").read_text(encoding="utf-8")
        pasados = set(re.findall(r"^\s*([A-Z0-9_]+):\s*\$\{\{\s*secrets\.", texto, re.M))

        hacen_falta = set()
        def anotar(cuenta):
            hacen_falta.update((cuenta.get("credenciales") or {}).values())
            for r in cuenta.get("respaldo") or []:
                if isinstance(r, dict):
                    anotar(r)
        for c in sat.cuentas(solo_activas=False):
            anotar(c)

        self.assertTrue(hacen_falta, "cuentas.json no nombra ningún secret")
        self.assertEqual(hacen_falta - pasados, set(),
                         "el workflow no le pasa estos secrets a leer_km.py: "
                         "la cuenta que los usa se queda sin leer.")

    def test_ningun_workflow_vuelca_todos_los_secrets(self):
        """Los comentarios no cuentan: el de odometros.yml cuenta justamente
        esta historia y nombra el volcado para que no se repita."""
        for nombre, texto in self.workflows():
            sin_comentarios = "\n".join(l for l in texto.splitlines()
                                        if not l.lstrip().startswith("#"))
            with self.subTest(workflow=nombre):
                self.assertFalse(
                    re.search(r"toJSON\(\s*secrets\s*\)", sin_comentarios),
                    f"{nombre} vuelca todos los secrets del repo en una "
                    "variable. GitHub lo lee como una fuga, bloquea el "
                    "workflow y las corridas quedan esperando que alguien "
                    "las apruebe a mano: nombrá cada secret.")


class Conexiones(unittest.TestCase):
    def test_parametros_muestra_las_cuentas_sin_valores_de_secrets(self):
        import parametros
        with mock.patch.dict(os.environ, {"HAWK_API_PASS": "no-mostrar"}):
            (c,) = parametros.satelitales_configurados()
        self.assertEqual((c["empresa"], c["proveedor"], c["respaldo"]),
                         ("Flota propia", "hawk_api", ["hawk_web"]))
        self.assertEqual(c["secrets"], ["HAWK_API_USER", "HAWK_API_PASS", "HAWK_USER", "HAWK_PASS"])
        self.assertNotIn("no-mostrar", json.dumps(c))


if __name__ == "__main__":
    unittest.main()
