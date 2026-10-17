"""La barra lateral que lateral.js pone en todas las pantallas.

Hasta acá la lista de módulos vivía solo en la portada: para ir de
Gomería a Repuestos había que volver al inicio y entrar de nuevo. Ahora
está en todas, y eso trae un riesgo nuevo: dos listas, una en inicio.html
y otra en lateral.js, que se separan en silencio. El día que se agregue un
módulo y se lo cargue en un solo lado, nadie se entera hasta que alguien
lo busca y no está. Por eso la prueba grande de acá compara las dos.
"""
import json
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
import app


def _nav_de_la_portada():
    """Los módulos como los escribe inicio.html, en orden."""
    html = (RAIZ / "inicio.html").read_text()
    nav = re.search(r'<nav class="nav".*?</nav>', html, re.S).group(0)
    salida = []
    for a in re.finditer(r"<a\b([^>]*)>(.*?)</a>", nav, re.S):
        atributos, adentro = a.group(1), a.group(2)
        salida.append((
            re.search(r'href="([^"]+)"', atributos).group(1),
            re.search(r"<span>(.*?)</span>", adentro, re.S).group(1),
        ))
    return salida


def _modulos_de_la_barra():
    """Los módulos como los declara lateral.js, en orden."""
    js = (RAIZ / "lateral.js").read_text()
    bloque = re.search(r"var MODULOS = \[(.*?)\n  \];", js, re.S).group(1)
    return [(json.loads(m.group(1)), json.loads(m.group(2)))
            for m in re.finditer(r'href:\s*("(?:[^"\\]|\\.)*").*?texto:\s*("(?:[^"\\]|\\.)*")',
                                 bloque, re.S)]


def _pantalla(ruta, html=b"<html><head></head><body></body></html>", usuario={"id": 1}):
    """Lo que sale al servir esa pantalla, con el agregado del servidor."""
    manejador = object.__new__(app.App)
    manejador.usuario = usuario
    manejador.path = ruta
    with patch.object(app.gom.Handler, "_responder") as salida:
        manejador._responder(html, "text/html")
        return salida.call_args.args[0]


class LaListaDeModulos(unittest.TestCase):
    """Una sola lista, aunque esté escrita en dos archivos."""

    def test_la_barra_y_la_portada_listan_lo_mismo_y_en_el_mismo_orden(self):
        portada, barra = _nav_de_la_portada(), _modulos_de_la_barra()
        self.assertEqual(barra, portada,
                         "inicio.html y lateral.js se separaron: el módulo que "
                         "falta de un lado no se ve desde esa pantalla.")

    def test_hay_modulos_de_verdad(self):
        """Si los dos lados quedaran vacíos, la comparación de arriba pasaría
        sin mirar nada."""
        self.assertGreaterEqual(len(_modulos_de_la_barra()), 8)

    def test_cada_modulo_apunta_a_una_direccion_que_el_servidor_sirve(self):
        """Un enlace a una pantalla que no existe es un 404 con el nombre del
        módulo arriba."""
        servidas = set(app.PANTALLAS) | {"/gomeria"}
        for href, texto in _modulos_de_la_barra():
            with self.subTest(modulo=texto):
                self.assertIn(href, servidas)


class ComoLlegaALaPantalla(unittest.TestCase):
    def test_se_inyecta_en_las_pantallas_de_trabajo(self):
        self.assertIn("/lateral.js", _pantalla("/ordenes"))
        self.assertIn("/lateral.js", _pantalla("/"))

    def test_va_sin_defer_para_que_el_contenido_no_pegue_un_salto(self):
        """Marca el <html> antes de que se pinte: con defer, la pantalla
        aparecía pegada al borde y se corría al armarse la barra."""
        self.assertIn('<script src="/lateral.js"></script>', _pantalla("/unidades"))

    def test_la_pantalla_que_ya_lo_declara_no_recibe_otro(self):
        propio = ('<html><head><script src="/lateral.js"></script></head>'
                  '<body></body></html>')
        self.assertEqual(_pantalla("/alertas", propio.encode()).count("/lateral.js"), 1)

    def test_sin_sesion_no_se_toca_nada(self):
        """El login no lleva barra: todavía no se sabe quién es."""
        self.assertEqual(_pantalla("/login", "login", usuario=None), "login")

    def test_el_archivo_se_sirve(self):
        self.assertEqual(app.PANTALLAS["/lateral.js"][0], "lateral.js")
        self.assertTrue((RAIZ / "lateral.js").exists())


class LasPantallasDelTelefono(unittest.TestCase):
    """El QR de la goma se escanea parado al lado de la unidad: ahí el ancho
    es todo y la barra no va."""

    def test_estan_declaradas_como_excepcion(self):
        js = (RAIZ / "lateral.js").read_text()
        afuera = re.search(r"var SIN_BARRA = \[(.*?)\];", js, re.S).group(1)
        self.assertIn("/movil", afuera)
        self.assertIn("/u/", afuera)


class ElZIndex(unittest.TestCase):
    """La barra es navegación, no un modal: cualquier diálogo tiene que
    taparla, incluido su velo."""

    def test_queda_debajo_del_velo_mas_bajo_de_las_pantallas(self):
        css = (RAIZ / "sistema.css").read_text()
        regla = re.search(r"aside\.lateral\{[^}]*z-index:(\d+)", css)
        self.assertIsNotNone(regla, "la barra fija perdió su z-index")
        suyo = int(regla.group(1))

        velos = []
        for pantalla in RAIZ.glob("*.html"):
            texto = pantalla.read_text()
            for m in re.finditer(r"position:fixed", texto):
                fin = texto.find("}", m.start())
                z = re.search(r"z-index:\s*(\d+)", texto[m.start():fin])
                if z:
                    velos.append(int(z.group(1)))
        self.assertTrue(velos, "no se encontró ningún velo con el que comparar")
        self.assertLess(suyo, min(velos),
                        "la barra tapa un modal: un diálogo abierto dejaría "
                        "la navegación encima.")


if __name__ == "__main__":
    unittest.main()
