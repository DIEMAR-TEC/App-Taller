"""La barra de módulos que va a la izquierda de todas las pantallas.

La arma el servidor y entra en el HTML, no la dibuja el navegador. La
diferencia se nota al cambiar de módulo: si la pusiera un script después de
cargar, cada navegación tendría un instante sin barra y el ojo lo ve como un
parpadeo. Viniendo en el HTML se pinta junto con el resto y parece que no se
hubiera movido.

Y como acá ya se sabe quién entró, los módulos que el rol no abre no se
escriben: antes salían todos y un script los escondía después, que es otro
parpadeo y además deja en la página direcciones que esa persona no usa.

La portada tiene la suya escrita en inicio.html, adentro de su grilla. Esta
es para las demás. Que las dos listas digan lo mismo lo cuida
tests/test_lateral.py.
"""
import permisos

# Las pantallas del teléfono no la llevan: el QR de la goma se escanea
# parado al lado de la unidad y ahí el ancho es todo. La portada tampoco,
# que ya trae la suya.
SIN_BARRA = ("/", "/movil", "/handheld", "/handheld/qr")
SIN_BARRA_PREFIJO = ("/u/", "/handheld/")

MODULOS = [
    {"href": "/", "modulo": None, "texto": "Inicio",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10Z\"/><path d=\"M9 21v-7h6v7\"/></svg>"},
    {"href": "/unidades", "modulo": "unidades", "texto": "Flota",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><rect x=\"3\" y=\"9\" width=\"13\" height=\"7\" rx=\"1\"/><path d=\"M16 11h3l2 3v2h-5z\"/><circle cx=\"7\" cy=\"18\" r=\"1.6\"/><circle cx=\"17.5\" cy=\"18\" r=\"1.6\"/></svg>"},
    {"href": "/vencimientos", "modulo": "vencimientos", "texto": "Vencimientos",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"16\" rx=\"2\"/><path d=\"M3 10h18M8 3v4M16 3v4\"/><path d=\"m9 15 2 2 4-4\"/></svg>"},
    {"href": "/gomeria", "modulo": "gomeria", "texto": "Gomería",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><circle cx=\"12\" cy=\"12\" r=\"8\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/></svg>"},
    {"href": "/repuestos", "modulo": "repuestos", "texto": "Repuestos",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"m21 8-9 5-9-5 9-5 9 5Z\"/><path d=\"M3 8v8l9 5 9-5V8\"/><path d=\"M12 13v8\"/></svg>"},
    {"href": "/ordenes", "modulo": "ordenes", "texto": "Órdenes",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><rect x=\"5\" y=\"3\" width=\"14\" height=\"18\" rx=\"2\"/><path d=\"M9 3h6v3H9z\"/><path d=\"M8.5 12h7M8.5 16h4\"/></svg>"},
    {"href": "/solicitudes", "modulo": "solicitudes", "texto": "Solicitudes",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M4 5h16v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5Z\"/><path d=\"M7.5 9h9M7.5 12.5h5\"/><path d=\"M8 19h8\"/></svg>"},
    {"href": "/combustible", "modulo": "combustible", "texto": "Combustible",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M3 21h10V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v17Z\"/><path d=\"M13 9h3a2 2 0 0 1 2 2v6a2 2 0 0 0 3 1.7\"/><path d=\"M6 8h4\"/></svg>"},
    {"href": "/viento", "modulo": "viento", "texto": "Viento",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M3 8h11a3 3 0 1 0-3-3\"/><path d=\"M3 12h16a3 3 0 1 1-3 3\"/><path d=\"M3 16h7\"/></svg>"},
    {"href": "/control", "modulo": "flota", "texto": "Services",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M3 17V7a1 1 0 0 1 1-1h10v11H3z\"/><path d=\"M14 10h4l3 3v4h-7z\"/><circle cx=\"7\" cy=\"17.5\" r=\"2\"/><circle cx=\"17\" cy=\"17.5\" r=\"2\"/></svg>"},
]

AJUSTES = {"href": "/configuracion", "texto": "Configuración",
     "icono": "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z\"/></svg>"}


def corresponde(ruta, consulta=""):
    """Si esa pantalla lleva barra.

    'consulta' es lo que va después del signo de pregunta. Hace falta por
    las pantallas embebidas: la portada mete a Titán adentro de un iframe
    (/asistente?embed=1) y ahí la barra salía dibujada en miniatura dentro
    de la tarjeta, como una barra adentro de otra. Una pantalla embebida es
    un pedazo de otra, no una pantalla: no se navega desde ella.
    """
    if "embed=1" in (consulta or ""):
        return False
    ruta = (ruta or "/").split("?")[0].rstrip("/") or "/"
    if ruta in SIN_BARRA:
        return False
    return not ruta.startswith(SIN_BARRA_PREFIJO)


def _enlace(item, ruta, clase=""):
    aca = ' aria-current="page"' if ruta == item["href"] else ""
    clase = f' class="{clase}"' if clase else ""
    return (f'<a{clase} href="{item["href"]}"{aca} title="{item["texto"]}">'
            f'{item["icono"]}<span>{item["texto"]}</span></a>')


def barra(usuario, ruta):
    """El HTML de la barra, con los módulos que ese rol abre.

    Esconder un módulo es comodidad, no seguridad: el permiso lo revisa el
    servidor en cada pedido. Lo que se gana es que nadie vea la puerta de
    un cuarto al que no puede entrar.
    """
    ruta = (ruta or "/").split("?")[0].rstrip("/") or "/"
    visibles = [m for m in MODULOS if permisos.puede_ver(usuario, m["modulo"])]
    return (
        '<aside class="sidebar lateral">'
        '<a class="brand" href="/" aria-label="Titán Flota · Inicio">'
        '<img src="/logo.png" alt="Titán Flota" width="128" height="40"></a>'
        '<p class="nav-label"><span>Módulos</span></p>'
        '<nav class="nav" aria-label="Módulos principales">'
        + "".join(_enlace(m, ruta) for m in visibles) +
        '</nav>'
        + _enlace(AJUSTES, ruta, "ajustes") +
        '</aside>')
