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

Además de la hoja A4, las dos páginas se pueden imprimir en una
etiquetadora de rollo (Brother QL, Zebra, Dymo, Xprinter): se elige la
medida del rollo en la barra y cada etiqueta sale en su propia página de
ese tamaño, ya autoadhesiva. La elección se recuerda en el navegador y
también viaja en la dirección (?formato=62x29).
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

ANCHO_MM = 70
ALTO_MM = 37
COLUMNAS = 3
FILAS = 8

# Las medidas de rollo que se ofrecen, ancho × alto en milímetros. Son las
# más comunes de las etiquetadoras térmicas; para agregar otra, alcanza
# con sumarla acá.
ROLLOS = [
    ("62x29", "Rollo 62 × 29 mm (Brother QL)"),
    ("62x100", "Rollo 62 × 100 mm (Brother QL)"),
    ("29x90", "Rollo 29 × 90 mm (Brother QL)"),
    ("50x25", "Rollo 50 × 25 mm"),
    ("50x30", "Rollo 50 × 30 mm"),
    ("60x40", "Rollo 60 × 40 mm"),
    ("100x50", "Rollo 100 × 50 mm (Zebra)"),
    ("89x36", "Rollo 89 × 36 mm (Dymo)"),
]


def _formato():
    """El selector de formato de la barra y el código que lo aplica.

    En rollo, el @page pasa a medir lo que la etiqueta y cada una sale en
    su propia página: así lo espera el driver de cualquier etiquetadora.
    Las etiquetas altas (más alto que ancho) se imprimen giradas para que
    el QR y el texto entren a lo largo."""
    opciones = f'<option value="a4">Hoja A4 · {ANCHO_MM} × {ALTO_MM} mm</option>' + "".join(
        f'<option value="{v}">{html.escape(t)}</option>' for v, t in ROLLOS)
    selector = f'<select id="formato" title="Formato de impresión">{opciones}</select>'
    script = """<style id="estilo-rollo"></style>
<script>
(function(){
  var sel = document.getElementById("formato");
  var est = document.getElementById("estilo-rollo");
  var nota = document.getElementById("nota-formato");
  var notaA4 = nota ? nota.textContent : "";
  function aplicar(v){
    var m = /^(\\d+)x(\\d+)$/.exec(v || "");
    if(!m || !sel.querySelector('option[value="' + v + '"]')){ v = "a4"; m = null; }
    sel.value = v;
    document.body.classList.toggle("rollo", !!m);
    if(!m){ est.textContent = ""; if(nota) nota.textContent = notaA4; return; }
    var w = +m[1], h = +m[2];
    // La etiqueta se diseña apaisada; si el rollo es alto, se gira.
    var girar = h > w, ew = girar ? h : w, eh = girar ? w : h;
    est.textContent =
      "@page{size:" + w + "mm " + h + "mm;margin:0}" +
      "body.rollo{--ew:" + ew + "mm;--eh:" + eh + "mm;--pw:" + w + "mm;--ph:" + h + "mm}" +
      (girar ? "body.rollo .et,body.rollo .grande{transform:rotate(90deg) translateY(-100%);transform-origin:top left}" : "");
    if(nota) nota.textContent = w + " × " + h + " mm · una etiqueta por página";
  }
  var guardado = null;
  try { guardado = localStorage.getItem("etiquetas-formato"); } catch(e){}
  aplicar(new URLSearchParams(location.search).get("formato") || guardado);
  sel.addEventListener("change", function(){
    aplicar(sel.value);
    try { localStorage.setItem("etiquetas-formato", sel.value); } catch(e){}
    var u = new URL(location.href);
    if(sel.value === "a4") u.searchParams.delete("formato"); else u.searchParams.set("formato", sel.value);
    history.replaceState(null, "", u);
  });
})();
</script>"""
    return selector, script


# Lo que cambia en modo rollo, igual para las dos páginas. Cada etiqueta
# ocupa una página entera del tamaño del rollo (--pw × --ph); --ew × --eh
# es la etiqueta ya acostada, que es lo mismo salvo en los rollos altos.
CSS_ROLLO = """
  .barra select { background: #20262c; color: #fff; border: 1px solid #3a424a;
    border-radius: 9px; padding: 8px 10px; font: inherit; }
  body.rollo .hoja { width: auto; padding: 0; background: none; display: flex;
    flex-direction: column; align-items: center; gap: 4mm; }
  body.rollo .grilla { display: contents; }
  body.rollo .pag { display: block; width: var(--pw); height: var(--ph); background: #fff;
    overflow: hidden; flex: none; }
  body.rollo .et, body.rollo .grande { width: var(--ew); height: var(--eh);
    border: 0; padding: 1.5mm 2mm; gap: 2mm; display: flex; align-items: center;
    text-align: left; overflow: hidden; }
  body.rollo .et .qr, body.rollo .grande .qr { height: calc(var(--eh) - 3mm);
    width: calc(var(--eh) - 3mm); flex: none; }
  body.rollo .grande h1 { font-size: 10pt; margin: 0; }
  body.rollo .grande p { display: none; }
  body.rollo .et .desc { -webkit-line-clamp: 2; }
  @media print {
    body.rollo .hoja { display: block; }
    body.rollo .pag { break-after: page; }
    body.rollo .pag:last-child { break-after: auto; }
  }
"""


def _qr(texto):
    """El QR como SVG, sin cabecera XML, para incrustarlo en la página."""
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
    return svg.replace("<svg", '<svg class="qr" preserveAspectRatio="xMidYMid meet"', 1)


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
        return f"""    <div class="pag"><div class="et">
      {_qr(destino)}
      <div class="txt">
        <div class="cab"><b>{html.escape(a['codigo'])}</b>{marca}</div>
        <span class="desc">{html.escape(a['descripcion'])}</span>
        <span class="pie">{html.escape(a['rubro'])}{' · int. ' + html.escape(interno) if interno else ''}</span>
      </div>
    </div></div>"""

    cuerpo = "\n".join(etiqueta(a) for a in arts) or \
        '    <p class="vacio">No hay repuestos que entren en ese filtro.</p>'
    titulo = f"{len(arts)} etiqueta{'' if len(arts) == 1 else 's'}"
    if rubro:
        titulo += f" · {html.escape(rubro)}"
    selector, script = _formato()

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
  .pag {{ display: contents; }}

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
{CSS_ROLLO}
</style>
</head>
<body>

<div class="barra">
  <img src="/logo.png" alt="Titán Flota" style="height:24px" onerror="this.style.display='none'">
  <a class="volver" href="/repuestos">‹ Volver</a>
  <b>{titulo}</b>
  {selector}
  <button onclick="print()">Imprimir</button>
  <span class="nota" id="nota-formato">{ANCHO_MM} × {ALTO_MM} mm · {COLUMNAS * FILAS} por hoja A4</span>
</div>

<div class="hoja">
{cuerpo}
</div>
{script}
</body>
</html>
"""


def cartel_handheld(cx, base):
    """El QR de «registrar trabajo», para la gomería, y uno por unidad,
    para pegar en cada camión: abre su ficha (historia clínica) con los
    accesos a cubiertas y órdenes. Sirven igual desde la handheld y desde
    la cámara de un celular."""
    base = base.rstrip("/")
    unidades = cx.execute("""
        select patente, interno from unidades where activa
        order by patente""").fetchall()

    def tarjeta(destino, titulo, sub):
        return f"""    <div class="pag"><div class="et">
      {_qr(destino)}
      <div class="txt"><b>{html.escape(titulo)}</b><span class="desc">{html.escape(sub)}</span></div>
    </div></div>"""

    grande = f"""<div class="pag"><div class="grande">{_qr(base + "/handheld#v-trabajo")}
      <h1>Registrar trabajo de gomería</h1>
      <p>Escanear para cargar el parte escrito o dictado.</p></div></div>"""
    selector, script = _formato()
    chicas = "\n".join(tarjeta(f"{base}/handheld/u/{u['patente']}", u["patente"],
                               f"Int. {u['interno']}" if u["interno"] else "Ficha de la unidad")
                       for u in unidades)
    return f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>QR de gomería | Titán Flota</title>
<style>
  @page {{ size: A4; margin: 8mm; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #6b7280; color: #111; font: 13px Inter, system-ui, sans-serif; }}
  .barra {{ position: sticky; top: 0; display: flex; gap: 14px; align-items: center;
    padding: 12px 20px; background: #12161a; color: #edf0f2; }}
  .barra a, .barra button {{ color: #fff; background: #2563eb; border: 0; border-radius: 9px;
    padding: 9px 15px; font: inherit; font-weight: 700; text-decoration: none; cursor: pointer; }}
  .hoja {{ width: 210mm; margin: 14px auto; padding: 8mm; background: #fff; }}
  .grande {{ text-align: center; padding: 10mm 0; break-after: page; }}
  .grande .qr {{ width: 120mm; height: 120mm; }}
  .grande h1 {{ font-size: 26pt; margin: 6mm 0 2mm; }}
  .grilla {{ display: grid; grid-template-columns: repeat({COLUMNAS}, {ANCHO_MM}mm);
    grid-auto-rows: {ALTO_MM}mm; justify-content: center; }}
  .pag {{ display: contents; }}
  .et {{ display: flex; align-items: center; gap: 3mm; padding: 2.5mm; border: 1px dashed #d4d4d8; }}
  .et .qr {{ height: {ALTO_MM - 7}mm; width: {ALTO_MM - 7}mm; flex: none; }}
  .et b {{ display: block; font-size: 13pt; }}
  .et .desc {{ font-size: 8pt; color: #52525b; }}
  @media print {{ body {{ background: #fff; }} .barra {{ display: none; }}
    .hoja {{ width: auto; margin: 0; padding: 0; }} .et {{ break-inside: avoid; }} }}
{CSS_ROLLO}
</style></head>
<body>
<div class="barra"><a href="/handheld">‹ Volver</a><b>QR de gomería</b>
  {selector}
  <button onclick="print()">Imprimir</button></div>
<div class="hoja">
{grande}
<div class="grilla">
{chicas}
</div>
</div>
{script}
</body></html>
"""
