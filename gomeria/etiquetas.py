"""
La hoja de etiquetas QR de los repuestos, lista para imprimir.

Cada etiqueta lleva un QR con la dirección del repuesto en la app. El
gomero le apunta con la cámara del celular y se abre la salida de ese
repuesto, con la cantidad en 1: no tiene que buscarlo en una lista de
cientos.

El QR guarda la dirección, no el stock. Por eso la etiqueta no se vence:
sirve igual aunque el artículo cambie de cantidad, de rubro o de precio.
El SVG va incrustado en la página, así que la hoja se imprime bien aunque
la impresora esté en una máquina sin internet.

Medidas: 70 × 37 mm, tres columnas por ocho filas, 24 por hoja A4. Es el
tamaño de las hojas autoadhesivas más comunes. Para cambiarlo, están las
constantes de acá abajo.
"""
import base64
import io
import html
import os

import qrcode
from qrcode.image.svg import SvgPathImage

AQUI = os.path.dirname(os.path.abspath(__file__))
# El logo de Titán Flota en una versión liviana para imprimir: va
# incrustado en la hoja de etiquetas.
LOGO = os.path.join(AQUI, os.pardir, "titan-flota-impresion.png")
# La «T» del sistema, la misma del ícono de la app: va en el centro de los
# QR que se pegan en los camiones.
ICONO = os.path.join(AQUI, os.pardir, "titan-flota-icono.png")

ANCHO_MM = 70
ALTO_MM = 37
COLUMNAS = 3
FILAS = 8


def _qr(texto, icono=False):
    """El QR como SVG, sin cabecera XML, para incrustarlo en la página.

    Con icono, lleva el logo del sistema en el centro. Para que se siga
    leyendo con el centro tapado, se arma con la corrección de errores más
    alta (H, recupera hasta el 30%) y el logo ocupa menos de un cuarto del
    ancho.
    """
    if icono:
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H,
                           box_size=10, border=1, image_factory=SvgPathImage)
        qr.add_data(texto)
        qr.make(fit=True)
        img = qr.make_image()
    else:
        img = qrcode.make(texto, image_factory=SvgPathImage, box_size=10, border=1)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode()
    svg = svg[svg.index("<svg"):]
    # El SVG que sale trae un tamaño fijo en milímetros; se lo saca para
    # que ocupe el alto de la etiqueta y no el que decidió la librería.
    for atributo in ('width="', 'height="'):
        while atributo in svg:
            i = svg.index(atributo)
            j = svg.index('"', i + len(atributo)) + 1
            svg = svg[:i] + svg[j:]
    svg = svg.replace("<svg", '<svg class="qr" preserveAspectRatio="xMidYMid meet"', 1)
    if icono and os.path.exists(ICONO):
        lado = float(svg.split('viewBox="0 0 ', 1)[1].split(" ", 1)[0])
        t = round(lado * 0.24, 2)
        x = round((lado - t) / 2, 2)
        datos = base64.b64encode(open(ICONO, "rb").read()).decode()
        svg = svg.replace("</svg>",
            f'<rect x="{x - 0.6}" y="{x - 0.6}" width="{t + 1.2}" height="{t + 1.2}" rx="1" fill="#fff"/>'
            f'<image x="{x}" y="{x}" width="{t}" height="{t}" '
            f'href="data:image/png;base64,{datos}" xlink:href="data:image/png;base64,{datos}"/></svg>')
        svg = svg.replace('xmlns="http://www.w3.org/2000/svg"',
                          'xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"', 1)
    return svg


def _logo():
    """El logo incrustado, para que la hoja se imprima igual sin internet."""
    if not os.path.exists(LOGO):
        return ""
    datos = base64.b64encode(open(LOGO, "rb").read()).decode()
    return f'<img class="dm" src="data:image/png;base64,{datos}" alt="Titán Flota">'


def _articulos(cx, rubro=None, codigos=None, solo_activos=True):
    condiciones = []
    valores = []
    if solo_activos:
        condiciones.append("activo")
    if rubro:
        condiciones.append("rubro = %s")
        valores.append(rubro)
    if codigos:
        condiciones.append("codigo = any(%s)")
        valores.append(list(codigos))
    donde = (" where " + " and ".join(condiciones)) if condiciones else ""
    return cx.execute(f"""
        select codigo, descripcion, rubro, codigo_interno
        from repuestos_articulos {donde}
        order by rubro, descripcion, codigo
    """, valores).fetchall()


def rubros(cx):
    return [r["rubro"] for r in cx.execute("""
        select distinct rubro from repuestos_articulos
        where activo order by rubro""").fetchall()]


def hoja(cx, base, rubro=None, codigos=None):
    """La página de etiquetas. `base` es la dirección que ven los celulares."""
    arts = _articulos(cx, rubro, codigos)
    base = base.rstrip("/")

    marca = _logo()

    def etiqueta(a):
        from urllib.parse import quote
        destino = f"{base}/repuestos/{quote(a['codigo'], safe='')}"
        interno = a["codigo_interno"] or ""
        return f"""    <div class="et">
      {_qr(destino)}
      <div class="txt">
        <div class="cab"><b>{html.escape(a['codigo'])}</b>{marca}</div>
        <span class="desc">{html.escape(a['descripcion'])}</span>
        <span class="pie">{html.escape(a['rubro'])}{' · int. ' + html.escape(interno) if interno else ''}</span>
      </div>
    </div>"""

    cuerpo = "\n".join(etiqueta(a) for a in arts) or \
        '    <p class="vacio">No hay repuestos que entren en ese filtro.</p>'
    titulo = f"{len(arts)} etiqueta{'' if len(arts) == 1 else 's'}"
    if rubro:
        titulo += f" · {html.escape(rubro)}"

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Etiquetas de repuestos | Titán Flota</title>
<style>
  /* En pantalla se ve sobre gris para distinguir las hojas; al imprimir
     solo salen las etiquetas. */
  @page {{ size: A4; margin: 8mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #6b7280; color: #111;
    font: 13px Inter, system-ui, -apple-system, sans-serif; }}

  .barra {{ position: sticky; top: 0; z-index: 5; display: flex; gap: 14px;
    align-items: center; padding: 12px 20px; background: #12161a; color: #edf0f2; }}
  .barra b {{ font-size: 14px; }}
  .barra a, .barra button {{ color: #fff; background: #2563eb; border: 0;
    border-radius: 9px; padding: 9px 15px; font: inherit; font-weight: 700;
    text-decoration: none; cursor: pointer; }}
  .barra .volver {{ background: #20262c; }}
  .barra .nota {{ margin-left: auto; color: #8d959e; font-size: 12px; }}

  .hoja {{ width: 210mm; margin: 14px auto; padding: 8mm; background: #fff;
    display: grid; grid-template-columns: repeat({COLUMNAS}, {ANCHO_MM}mm);
    grid-auto-rows: {ALTO_MM}mm; justify-content: center; }}

  .et {{ display: flex; align-items: center; gap: 3mm; padding: 2.5mm;
    overflow: hidden; border: 1px dashed #d4d4d8; }}
  .et .qr {{ height: {ALTO_MM - 7}mm; width: {ALTO_MM - 7}mm; flex: none; }}
  .et .txt {{ min-width: 0; display: flex; flex-direction: column; gap: 0.6mm; }}
  .et .cab {{ display: flex; align-items: center; gap: 2mm; }}
  .et b {{ font-size: 11pt; font-weight: 800; letter-spacing: .2px; min-width: 0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  /* El logo se queda con el ancho que sobra al lado del código, nunca al
     revés: si el código es largo, se achica el logo y no el código. */
  .et .dm {{ margin-left: auto; height: 3.4mm; flex: 0 1 auto; min-width: 0;
    object-fit: contain; object-position: right; }}
  /* La descripción es lo que más varía de largo: se le dan tres renglones
     y lo que no entra se corta, para que ninguna etiqueta empuje a la de
     al lado y se desarme la grilla. */
  .et .desc {{ font-size: 7.6pt; line-height: 1.25; display: -webkit-box;
    -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }}
  .et .pie {{ font-size: 6.4pt; color: #52525b; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; }}
  .vacio {{ grid-column: 1 / -1; text-align: center; color: #6b7280; padding: 30mm 0; }}

  @media print {{
    body {{ background: #fff; }}
    .barra {{ display: none; }}
    .hoja {{ width: auto; margin: 0; padding: 0; }}
    /* El borde punteado es la guía para cortar; si molesta, se saca acá. */
    .et {{ border-color: #e4e4e7; break-inside: avoid; }}
  }}
</style>
</head>
<body>

<div class="barra">
  <img src="/logo.png" alt="Titán Flota" style="height:24px" onerror="this.style.display='none'">
  <a class="volver" href="/repuestos">‹ Volver</a>
  <b>{titulo}</b>
  <button onclick="print()">Imprimir</button>
  <span class="nota">{ANCHO_MM} × {ALTO_MM} mm · {COLUMNAS * FILAS} por hoja A4</span>
</div>

<div class="hoja">
{cuerpo}
</div>

</body>
</html>
"""


def cartel_handheld(cx, base):
    """El QR de «registrar trabajo», para la gomería, y uno por unidad,
    para pegar en cada camión: abre su registro (datos, gomería y stock).
    Sirven igual desde la handheld y desde la cámara de un celular.

    Las de los camiones son más grandes que las de los repuestos —95 × 68
    mm, ocho por hoja A4— y llevan el logo arriba y en el centro del QR:
    se leen a un metro y se reconocen como del sistema.
    """
    base = base.rstrip("/")
    unidades = cx.execute("""
        select patente, interno from unidades where activa
        order by patente""").fetchall()
    marca = _logo()

    def tarjeta(u):
        destino = f"{base}/handheld/u/{u['patente']}"
        interno = f"Interno {u['interno']}" if u["interno"] else ""
        return f"""    <div class="et">
      <div class="cab">{marca}<span>Registro de la unidad</span></div>
      <div class="cuerpo">{_qr(destino, icono=True)}
        <div class="txt"><b>{html.escape(u['patente'])}</b><span>{html.escape(interno)}</span></div>
      </div>
    </div>"""

    grande = f"""<div class="grande">{marca}
      {_qr(base + "/handheld#v-trabajo", icono=True)}
      <h1>Movimiento de gomería</h1>
      <p>Escanear para cargar el trabajo escrito o dictado.</p></div>"""
    chicas = "\n".join(tarjeta(u) for u in unidades)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>QR de unidades | Titán Flota</title>
<style>
  @page {{ size: A4; margin: 8mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #6b7280; color: #111; font: 13px Inter, system-ui, sans-serif; }}
  .barra {{ position: sticky; top: 0; z-index: 5; display: flex; gap: 14px; align-items: center;
    padding: 12px 20px; background: #12161a; color: #edf0f2; }}
  .barra a, .barra button {{ color: #fff; background: #2563eb; border: 0; border-radius: 9px;
    padding: 9px 15px; font: inherit; font-weight: 700; text-decoration: none; cursor: pointer; }}
  .hoja {{ width: 210mm; margin: 14px auto; padding: 8mm; background: #fff; }}
  .grande {{ text-align: center; padding: 8mm 0; break-after: page; }}
  .grande .dm {{ height: 16mm; }}
  .grande .qr {{ display: block; margin: 8mm auto 0; width: 120mm; height: 120mm; }}
  .grande h1 {{ font-size: 26pt; margin: 6mm 0 2mm; }}
  .grilla {{ display: grid; grid-template-columns: repeat(2, 95mm); grid-auto-rows: 68mm;
    gap: 0; justify-content: center; }}
  .et {{ display: flex; flex-direction: column; padding: 4mm; border: 1px dashed #d4d4d8; }}
  .et .cab {{ display: flex; align-items: center; justify-content: space-between;
    border-bottom: 1.2mm solid #14243a; padding-bottom: 1.5mm; }}
  .et .cab .dm {{ height: 8mm; }}
  .et .cab span {{ font-size: 8pt; font-weight: 700; letter-spacing: .5px; text-transform: uppercase; color: #14243a; }}
  .et .cuerpo {{ flex: 1; display: flex; align-items: center; gap: 4mm; padding-top: 2mm; }}
  .et .qr {{ width: 46mm; height: 46mm; flex: none; }}
  .et .txt {{ min-width: 0; }}
  .et .txt b {{ display: block; font-size: 18pt; letter-spacing: .5px; color: #14243a; line-height: 1.05; }}
  .et .txt span {{ font-size: 10pt; color: #52525b; }}
  @media print {{ body {{ background: #fff; }} .barra {{ display: none; }}
    .hoja {{ width: auto; margin: 0; padding: 0; }} .et {{ break-inside: avoid; }} }}
</style></head>
<body>
<div class="barra"><b>QR de unidades</b>
  <button onclick="print()">Imprimir</button>
  <span style="margin-left:auto;color:#8d959e;font-size:12px">95 × 68 mm · 8 por hoja A4</span></div>
<div class="hoja">
{grande}
<div class="grilla">
{chicas}
</div>
</div>
</body></html>
"""
