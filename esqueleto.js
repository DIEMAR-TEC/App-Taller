/* Los esqueletos mientras carga: en lugar del "Cargando…" pelado, la forma
 * de lo que va a aparecer —filas de tabla, renglones, barras de gráfico—
 * en gris y con un brillo que pasa.
 *
 * Ninguna pantalla tiene que hacer nada: el servidor inyecta este archivo
 * en todas (app.py) y acá se buscan los textos de espera que ya existen
 * ("Cargando…", "Cargando costos…", "Buscando…"). Así una pantalla nueva
 * que escriba su "Cargando…" de siempre recibe el esqueleto sola.
 *
 * Va sin defer, en el <head>, como tema.js: el observador mira el HTML
 * mientras el navegador lo va leyendo, y el texto se cambia antes de que
 * llegue a pintarse. Esperar al final de la carga dejaba ver un instante
 * el "Cargando…" y después el salto al esqueleto.
 *
 * Cuando llegan los datos, la pantalla reemplaza el contenido como hacía
 * siempre y el esqueleto se va con él. Los textos que la pantalla pisa
 * en el lugar (el contador del pie, la fecha) pierden el gris solos.
 */
(function () {
  'use strict';

  var ESPERA = /^(cargando|buscando)\b[^]*…$/i;
  var FILAS = 6;
  /* Anchos que se repiten para que las filas no salgan todas iguales. */
  var ANCHOS = [72, 48, 86, 60, 38, 78, 54, 66];

  /* Los textos de espera que son un bloque propio: se reemplaza su
     contenido por renglones o barras. El resto (un subtítulo, un
     contador) queda en su lugar y solo se tapa con gris. */
  var BLOQUE = '.vacio,.dashboard-empty,.alerts-empty,.cargando';

  function estilo() {
    if (document.getElementById('esqueleto-css')) return;
    var css = document.createElement('style');
    css.id = 'esqueleto-css';
    css.textContent =
      ':root{--esq-base:color-mix(in srgb,var(--ink,#14243a) 9%,transparent);' +
      '--esq-brillo:color-mix(in srgb,var(--ink,#14243a) 4%,transparent)}' +
      '.esq,.esq-texto{background:linear-gradient(90deg,var(--esq-base) 0%,' +
      'var(--esq-brillo) 40%,var(--esq-base) 80%) 0 0/300% 100%;' +
      'animation:esq-brillo 1.4s ease-in-out infinite}' +
      '.esq{display:block;height:12px;border-radius:6px}' +
      '.esq-texto{color:transparent!important;border-radius:6px;' +
      'display:inline-block;min-width:14ch;user-select:none}' +
      '.esq-fila td{padding-top:12px!important;padding-bottom:12px!important;border-color:var(--line,#e5e7eb)}' +
      '.esq-renglones{display:grid;gap:10px;padding:8px 0;width:100%}' +
      '.esq-barras{display:flex;align-items:flex-end;gap:6px;height:120px;padding:8px 0;width:100%}' +
      '.esq-barras .esq{flex:1;height:auto;border-radius:4px 4px 0 0}' +
      '.esq-oculto{position:absolute!important;width:1px;height:1px;overflow:hidden;' +
      'clip:rect(0 0 0 0);white-space:nowrap}' +
      '@keyframes esq-brillo{0%{background-position:100% 0}100%{background-position:0 0}}' +
      '@media(prefers-reduced-motion:reduce){.esq,.esq-texto{animation:none}}';
    (document.head || document.documentElement).appendChild(css);
  }

  function barra(ancho, alto) {
    var b = document.createElement('span');
    b.className = 'esq';
    b.setAttribute('aria-hidden', 'true');
    if (ancho) b.style.width = ancho + '%';
    if (alto) b.style.height = alto + '%';
    return b;
  }

  function oculto(texto) {
    var s = document.createElement('span');
    s.className = 'esq-oculto';
    s.textContent = texto;
    return s;
  }

  function columnas(td) {
    var tabla = td.closest('table');
    var cab = tabla && tabla.querySelector('thead tr');
    var n = cab ? cab.children.length : 0;
    return n || td.colSpan || 1;
  }

  /* La fila de "Cargando…" de una tabla pasa a ser varias filas con una
     barra por columna. El texto queda en la primera, invisible, para el
     que usa lector de pantalla. */
  function tabla(td) {
    var fila = td.parentNode, cuerpo = fila && fila.parentNode;
    if (!cuerpo || fila.tagName !== 'TR') return;
    var n = columnas(td), texto = td.textContent.trim();
    var frag = document.createDocumentFragment();
    for (var i = 0; i < FILAS; i++) {
      var tr = document.createElement('tr');
      tr.className = 'esq-fila';
      for (var j = 0; j < n; j++) {
        var c = document.createElement('td');
        c.appendChild(barra(ANCHOS[(i * 3 + j) % ANCHOS.length]));
        tr.appendChild(c);
      }
      if (i === 0) tr.firstChild.appendChild(oculto(texto));
      frag.appendChild(tr);
    }
    cuerpo.replaceChild(frag, fila);
  }

  /* Un bloque de espera: barras si es el lugar de un gráfico, renglones
     si no. */
  function bloque(el) {
    var texto = el.textContent.trim();
    var grafico = el.closest('[class*="chart"]');
    var caja = document.createElement('div');
    caja.setAttribute('aria-hidden', 'true');
    if (grafico) {
      caja.className = 'esq-barras';
      for (var i = 0; i < 12; i++) caja.appendChild(barra(0, 30 + ANCHOS[i % ANCHOS.length] * 0.7));
    } else {
      caja.className = 'esq-renglones';
      [92, 74, 58].forEach(function (a) { caja.appendChild(barra(a)); });
    }
    el.textContent = '';
    el.appendChild(caja);
    el.appendChild(oculto(texto));
  }

  /* Un texto suelto: se tapa con gris en el lugar y se destapa apenas la
     pantalla le escribe otra cosa. */
  var vigilados = typeof MutationObserver === 'function' ? new MutationObserver(function (cambios) {
    cambios.forEach(function (c) {
      var el = c.target.nodeType === 1 ? c.target : c.target.parentNode;
      while (el && !el.classList.contains('esq-texto')) el = el.parentNode;
      if (el && !ESPERA.test(el.textContent.trim())) {
        el.classList.remove('esq-texto');
        el.removeAttribute('aria-busy');
      }
    });
  }) : null;

  function texto(el) {
    el.classList.add('esq-texto');
    el.setAttribute('aria-busy', 'true');
    if (vigilados) vigilados.observe(el, { childList: true, characterData: true, subtree: true });
  }

  function convertir(el) {
    if (el.classList.contains('esq-texto')) return;
    if (el.closest('button,select,option,textarea,script,style,.esq-oculto')) return;
    if (el.tagName === 'TD') return tabla(el);
    if (el.matches(BLOQUE)) return bloque(el);
    texto(el);
  }

  /* Solo cuentan los elementos cuyo único contenido es el texto de
     espera: "Se está cargando después" en medio de un párrafo no es un
     aviso de carga. */
  function esEspera(el) {
    return el.nodeType === 1 && el.children.length === 0 &&
      ESPERA.test(el.textContent.trim());
  }

  function revisar(nodo) {
    if (nodo.nodeType === 3) nodo = nodo.parentNode;
    if (!nodo || nodo.nodeType !== 1) return;
    var t = nodo.textContent;
    if (t.length > 4000 || !/cargando|buscando/i.test(t)) return;
    if (esEspera(nodo)) return convertir(nodo);
    var hijos = nodo.getElementsByTagName('*');
    var halla = [];
    for (var i = 0; i < hijos.length; i++) if (esEspera(hijos[i])) halla.push(hijos[i]);
    halla.forEach(convertir);
  }

  if (typeof MutationObserver !== 'function') return;
  estilo();
  new MutationObserver(function (cambios) {
    cambios.forEach(function (c) {
      if (c.type === 'characterData') return revisar(c.target);
      for (var i = 0; i < c.addedNodes.length; i++) revisar(c.addedNodes[i]);
    });
  }).observe(document.documentElement, { childList: true, subtree: true, characterData: true });
  /* Lo que ya estaba escrito antes de que este archivo corriera. */
  if (document.body) revisar(document.body);
})();
