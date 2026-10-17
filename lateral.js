/* =====================================================================
   LA BARRA LATERAL, EN TODAS LAS PANTALLAS
   ---------------------------------------------------------------------
   Hasta acá los módulos se listaban solo en la portada: para ir de
   Gomería a Repuestos había que volver al inicio y entrar de nuevo. Dos
   clics y una pantalla de por medio, cada vez. Esta barra pone esa lista
   en todas las pantallas, así se salta de un módulo a otro directo.

   Se inyecta sola —como tema.js y barra.js— y no se toca ningún archivo
   de pantalla: son diecisiete y cada una tiene su propio armado. Lo que
   sí comparten es la hoja sistema.css, que ya sabe pintar una .sidebar
   porque la portada tiene una. Por eso acá se arma el mismo marcado: el
   color, el hover y el módulo marcado salen de ahí sin repetir nada.

   El botón de ocultar deja una tira angosta con los íconos en vez de
   sacar la barra del todo. Sacarla entera dejaba el contenido pegado al
   borde y, sobre todo, dejaba al botón de volver a abrirla encima del
   encabezado de cada pantalla. Con la tira angosta se recupera casi todo
   el ancho, los módulos siguen a un clic y nada se pisa. La elección
   queda guardada y vale para todas las pantallas.

   Lo que se ve acá es comodidad, no seguridad: el permiso lo revisa el
   servidor en cada pedido (ver permisos.py). Un módulo que el rol no
   tiene se esconde, pero quien fuerce la dirección se choca igual con la
   puerta cerrada.
   ===================================================================== */
(function () {
  'use strict';

  var LLAVE = 'titan.lateral';
  var raiz = document.documentElement;

  /* Las pantallas del teléfono no la llevan: el QR de la goma se escanea
     parado al lado de la unidad y ahí el ancho es todo. */
  var SIN_BARRA = ['/movil', '/u/'];

  var MODULOS = [
    { href: "/", modulo: null, texto: "Inicio",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V10Z\"/><path d=\"M9 21v-7h6v7\"/></svg>" },
    { href: "/unidades", modulo: "unidades", texto: "Flota",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><rect x=\"3\" y=\"9\" width=\"13\" height=\"7\" rx=\"1\"/><path d=\"M16 11h3l2 3v2h-5z\"/><circle cx=\"7\" cy=\"18\" r=\"1.6\"/><circle cx=\"17.5\" cy=\"18\" r=\"1.6\"/></svg>" },
    { href: "/vencimientos", modulo: "vencimientos", texto: "Vencimientos",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><rect x=\"3\" y=\"5\" width=\"18\" height=\"16\" rx=\"2\"/><path d=\"M3 10h18M8 3v4M16 3v4\"/><path d=\"m9 15 2 2 4-4\"/></svg>" },
    { href: "/gomeria", modulo: "gomeria", texto: "Gomería",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><circle cx=\"12\" cy=\"12\" r=\"8\"/><circle cx=\"12\" cy=\"12\" r=\"3\"/></svg>" },
    { href: "/repuestos", modulo: "repuestos", texto: "Repuestos",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"m21 8-9 5-9-5 9-5 9 5Z\"/><path d=\"M3 8v8l9 5 9-5V8\"/><path d=\"M12 13v8\"/></svg>" },
    { href: "/ordenes", modulo: "ordenes", texto: "Órdenes",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><rect x=\"5\" y=\"3\" width=\"14\" height=\"18\" rx=\"2\"/><path d=\"M9 3h6v3H9z\"/><path d=\"M8.5 12h7M8.5 16h4\"/></svg>" },
    { href: "/solicitudes", modulo: "solicitudes", texto: "Solicitudes",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M4 5h16v9a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5Z\"/><path d=\"M7.5 9h9M7.5 12.5h5\"/><path d=\"M8 19h8\"/></svg>" },
    { href: "/combustible", modulo: "combustible", texto: "Combustible",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M3 21h10V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v17Z\"/><path d=\"M13 9h3a2 2 0 0 1 2 2v6a2 2 0 0 0 3 1.7\"/><path d=\"M6 8h4\"/></svg>" },
    { href: "/viento", modulo: "viento", texto: "Viento",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M3 8h11a3 3 0 1 0-3-3\"/><path d=\"M3 12h16a3 3 0 1 1-3 3\"/><path d=\"M3 16h7\"/></svg>" },
    { href: "/control", modulo: "flota", texto: "Services",
      icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke-width=\"1.8\"><path d=\"M3 17V7a1 1 0 0 1 1-1h10v11H3z\"/><path d=\"M14 10h4l3 3v4h-7z\"/><circle cx=\"7\" cy=\"17.5\" r=\"2\"/><circle cx=\"17\" cy=\"17.5\" r=\"2\"/></svg>" },
  ];

  var AJUSTES = { href: "/configuracion", texto: "Configuración",
    icono: "<svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.8\"><circle cx=\"12\" cy=\"12\" r=\"3\"/><path d=\"M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.6 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z\"/></svg>" };

  function donde() { return location.pathname.replace(/\/+$/, '') || '/'; }

  function corresponde() {
    var p = donde();
    for (var i = 0; i < SIN_BARRA.length; i++)
      if (p === SIN_BARRA[i] || p.indexOf(SIN_BARRA[i]) === 0) return false;
    return true;
  }

  /* ------------------------------------------------------------------
     EL ESTADO, ANTES DE PINTAR
     ------------------------------------------------------------------
     Este archivo se carga sin defer, en el encabezado, igual que tema.js.
     Marcar el <html> acá y no al armar la barra es lo que evita que la
     pantalla se dibuje pegada al borde y pegue un salto cuando la barra
     aparece. El ancho lo pone sistema.css mirando estos atributos. */
  function guardado() {
    try { return localStorage.getItem(LLAVE); } catch (e) { return null; }
  }

  if (corresponde()) {
    raiz.dataset.lateral = guardado() === 'chica' ? 'chica' : 'abierta';
    /* La portada ya tiene su barra adentro de la grilla y se encoge sola;
       las demás reciben una fija y hay que correrles el cuerpo. */
    if (donde() !== '/') raiz.dataset.lateralFija = '1';
  }

  function recordar(valor) {
    try { localStorage.setItem(LLAVE, valor); } catch (e) { /* modo privado */ }
  }

  /* ------------------------------------------------------------------
     EL MARCADO
     ------------------------------------------------------------------ */
  function enlace(m) {
    var aca = donde() === m.href;
    return '<a href="' + m.href + '"' +
      (m.modulo ? ' data-modulo="' + m.modulo + '"' : '') +
      (aca ? ' aria-current="page"' : '') +
      ' title="' + m.texto + '">' + m.icono +
      '<span>' + m.texto + '</span></a>';
  }

  function inyectar() {
    var caja = document.createElement('aside');
    caja.className = 'sidebar lateral';
    caja.innerHTML =
      '<a class="brand" href="/" aria-label="Titán Flota · Inicio">' +
      '<img src="/logo.png" alt="Titán Flota" width="176" height="65"></a>' +
      '<p class="nav-label">Módulos</p>' +
      '<nav class="nav" aria-label="Módulos principales">' +
      MODULOS.map(enlace).join('') + '</nav>' +
      '<a class="ajustes" href="' + AJUSTES.href + '"' +
      (donde() === AJUSTES.href ? ' aria-current="page"' : '') +
      ' title="' + AJUSTES.texto + '">' + AJUSTES.icono +
      '<span>' + AJUSTES.texto + '</span></a>';
    document.body.insertBefore(caja, document.body.firstChild);
    return caja;
  }

  /* ------------------------------------------------------------------
     OCULTARLA
     ------------------------------------------------------------------ */
  var OJO_CERRAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="1.9" aria-hidden="true"><path d="M14 7l-5 5 5 5"/></svg>';
  var OJO_ABRIR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="1.9" aria-hidden="true"><path d="M10 7l5 5-5 5"/></svg>';

  function boton(caja) {
    var fila = caja.querySelector('.nav-label');
    if (!fila || fila.querySelector('.lateral-boton')) return;

    /* El rótulo «Módulos» es texto suelto —así lo escribe la portada— y un
       nodo de texto no se puede esconder con CSS. Encogida la barra, ese
       texto seguía ocupando el ancho y empujaba al botón fuera del borde.
       Envolverlo acá lo arregla en las dos barras de una vez. */
    if (!fila.querySelector('span')) {
      var rotulo = document.createElement('span');
      rotulo.textContent = fila.textContent.trim();
      fila.textContent = '';
      fila.appendChild(rotulo);
    }

    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'lateral-boton';
    fila.appendChild(b);

    function pintar() {
      var chica = raiz.dataset.lateral === 'chica';
      b.innerHTML = chica ? OJO_ABRIR : OJO_CERRAR;
      b.title = chica ? 'Mostrar los nombres' : 'Ocultar la barra';
      b.setAttribute('aria-label', b.title);
      b.setAttribute('aria-expanded', chica ? 'false' : 'true');
    }
    pintar();

    b.addEventListener('click', function () {
      var chica = raiz.dataset.lateral === 'chica';
      raiz.dataset.lateral = chica ? 'abierta' : 'chica';
      recordar(raiz.dataset.lateral);
      pintar();
    });
  }

  /* ------------------------------------------------------------------
     QUÉ MÓDULOS VE CADA UNO
     ------------------------------------------------------------------
     Se pintan todos y después se esconden los que el rol no tiene, igual
     que en la portada: así la barra aparece con la pantalla y no espera a
     que conteste el servidor. */
  function permisos(caja) {
    fetch('/api/yo', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (yo) {
        if (!yo) return;
        var puede = {};
        (yo.modulos || []).forEach(function (m) { puede[m] = true; });
        caja.querySelectorAll('.nav a[data-modulo]').forEach(function (a) {
          a.hidden = !(yo.administra || puede[a.dataset.modulo]);
        });
      })
      .catch(function () { /* sin red: quedan todos y el servidor decide */ });
  }

  function arrancar() {
    if (!corresponde()) return;
    /* La portada trae la suya escrita en el archivo: no se le agrega otra,
       solo el botón. */
    var caja = document.querySelector('aside.sidebar') || inyectar();
    boton(caja);
    permisos(caja);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', arrancar);
  else
    arrancar();
})();
