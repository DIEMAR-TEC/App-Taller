"""La barra de módulos que el servidor pone a la izquierda de cada pantalla.

La arma gomeria/lateral.py y entra en el HTML. Eso trae un riesgo nuevo:
dos listas, una en inicio.html —que tiene la suya adentro de su grilla— y
otra en lateral.py, que se separan en silencio. El día que se agregue un
módulo y se lo cargue en un solo lado, nadie se entera hasta que alguien lo
busca y no está. Por eso la prueba grande de acá compara las dos.
"""
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "gomeria"))
import app
import lateral


def _nav_de_la_portada():
    """Los módulos como los escribe inicio.html, en orden."""
    html = (RAIZ / "inicio.html").read_text()
    nav = re.search(r'<nav class="nav".*?</nav>', html, re.S).group(0)
    return [(re.search(r'href="([^"]+)"', a.group(1)).group(1),
             re.search(r"<span>(.*?)</span>", a.group(2), re.S).group(1))
            for a in re.finditer(r"<a\b([^>]*)>(.*?)</a>", nav, re.S)]


def _pantalla(ruta, html=b"<html><head></head><body></body></html>",
              usuario={"id": 1, "administra": True}):
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
        barra = [(m["href"], m["texto"]) for m in lateral.MODULOS]
        self.assertEqual(barra, _nav_de_la_portada(),
                         "inicio.html y lateral.py se separaron: el módulo que "
                         "falta de un lado no se ve desde esa pantalla.")

    def test_hay_modulos_de_verdad(self):
        """Si los dos lados quedaran vacíos, la comparación de arriba pasaría
        sin mirar nada."""
        self.assertGreaterEqual(len(lateral.MODULOS), 8)

    def test_cada_modulo_apunta_a_una_direccion_que_el_servidor_sirve(self):
        """Un enlace a una pantalla que no existe es un 404 con el nombre del
        módulo arriba."""
        servidas = set(app.PANTALLAS) | {"/gomeria"}
        for m in lateral.MODULOS + [lateral.AJUSTES]:
            with self.subTest(modulo=m["texto"]):
                self.assertIn(m["href"], servidas)


class QueVeCadaRol(unittest.TestCase):
    """El marcado lo arma el servidor, que ya sabe quién entró: el módulo que
    el rol no abre no se escribe. Antes salían todos y un script los
    escondía después."""

    def test_el_que_administra_los_ve_todos(self):
        html = lateral.barra({"administra": True}, "/ordenes")
        for m in lateral.MODULOS:
            self.assertIn(f'href="{m["href"]}"', html)

    def test_un_rol_acotado_solo_ve_los_suyos(self):
        html = lateral.barra({"modulos": ["vencimientos"]}, "/vencimientos")
        self.assertIn('href="/vencimientos"', html)
        self.assertNotIn('href="/combustible"', html)

    def test_el_inicio_no_cuelga_de_ningun_permiso(self):
        """Es la portada de todos; sin esto un rol acotado se quedaba sin
        forma de volver."""
        self.assertIn('href="/"', lateral.barra({"modulos": []}, "/ordenes"))

    def test_marca_el_modulo_en_el_que_uno_esta(self):
        html = lateral.barra({"administra": True}, "/ordenes")
        self.assertIn('href="/ordenes" aria-current="page"', html)
        self.assertEqual(html.count('aria-current="page"'), 1)

    def test_configuracion_tambien_se_marca(self):
        html = lateral.barra({"administra": True}, "/configuracion")
        self.assertIn('aria-current="page"', html)


class DondeVa(unittest.TestCase):
    def test_entra_en_el_html_de_las_pantallas_de_trabajo(self):
        salida = _pantalla("/ordenes")
        self.assertIn('class="sidebar lateral"', salida)
        self.assertIn("/lateral.js", salida)

    def test_va_apenas_abre_el_body(self):
        """Más abajo quedaría después del contenido y, sin JavaScript, se
        vería al pie de la pantalla."""
        salida = _pantalla("/unidades")
        self.assertRegex(salida, r"<body[^>]*><aside class=\"sidebar lateral\"")

    def test_la_portada_no_la_recibe_porque_ya_tiene_la_suya(self):
        salida = _pantalla("/")
        self.assertNotIn('class="sidebar lateral"', salida)
        self.assertIn("/lateral.js", salida)      # el botón sí va

    def test_las_pantallas_del_telefono_quedan_afuera(self):
        """El QR de la goma se escanea parado al lado de la unidad: ahí el
        ancho es todo."""
        for ruta in ("/movil", "/u/AD247MQ"):
            with self.subTest(ruta=ruta):
                self.assertFalse(lateral.corresponde(ruta))
                self.assertNotIn('class="sidebar lateral"', _pantalla(ruta))

    def test_la_pantalla_embebida_no_la_lleva(self):
        """La portada mete a Titán adentro de un iframe (/asistente?embed=1).
        Con barra ahí, la tarjeta de Titán mostraba una barra en miniatura
        adentro: una barra adentro de otra. Una pantalla embebida es un
        pedazo de otra, no una pantalla: no se navega desde ella."""
        self.assertFalse(lateral.corresponde("/asistente", "embed=1"))
        self.assertNotIn('class="sidebar lateral"', _pantalla("/asistente?embed=1"))

    def test_pero_a_pantalla_completa_si(self):
        self.assertTrue(lateral.corresponde("/asistente", ""))
        self.assertIn('class="sidebar lateral"', _pantalla("/asistente"))

    def test_la_pantalla_que_ya_la_trae_no_recibe_otra(self):
        propio = '<html><head></head><body><aside class="sidebar lateral"></aside></body></html>'
        self.assertEqual(
            _pantalla("/alertas", propio.encode()).count('class="sidebar lateral"'), 1)

    def test_sin_sesion_no_se_toca_nada(self):
        """El login no lleva barra: todavía no se sabe quién es."""
        self.assertEqual(_pantalla("/login", "login", usuario=None), "login")

    def test_todas_las_pantallas_tienen_body(self):
        """La barra entra apenas abre el <body>. Repuestos no lo tenía: el
        lugar de la barra quedaba reservado y vacío."""
        for ruta, (archivo, tipo) in app.PANTALLAS.items():
            if tipo.startswith("text/html"):
                with self.subTest(ruta=ruta):
                    self.assertRegex((RAIZ / archivo).read_text(encoding="utf-8"), r"<body[^>]*>")

    def test_el_script_se_sirve(self):
        self.assertEqual(app.PANTALLAS["/lateral.js"][0], "lateral.js")
        self.assertTrue((RAIZ / "lateral.js").exists())


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


class LaPortadaAngosta(unittest.TestCase):
    """Abajo de 980px la portada arma su barra como una tira horizontal
    arriba. Encogerle la grilla ahí dejaba los íconos apretados en una franja
    vertical al lado del contenido, encima del panel de Titán."""

    def test_la_grilla_encogida_es_solo_para_pantalla_ancha(self):
        css = (RAIZ / "sistema.css").read_text()
        regla = re.search(r"operations-home \.shell\{grid-template-columns", css)
        self.assertIsNotNone(regla)
        antes = css[:regla.start()]
        media = antes.rfind("@media")
        self.assertNotEqual(media, -1, "la regla quedó fuera de toda media query")
        self.assertIn("min-width:981px", css[media:regla.start()])


if __name__ == "__main__":
    unittest.main()
