/* =====================================================================
   ABRIR Y CERRAR LA BARRA DE MÓDULOS
   ---------------------------------------------------------------------
   La barra en sí la manda el servidor armada adentro del HTML (ver
   gomeria/lateral.py). Acá queda solo lo que el servidor no puede hacer:
   acordarse de si el que mira la quiere abierta o encogida.

   Esto se carga sin defer, en el encabezado, igual que tema.js. Marcar el
   <html> acá y no al final es lo que evita que la pantalla se dibuje
   pegada al borde y pegue un salto cuando aparece la barra: el ancho sale
   de sistema.css mirando estos atributos, y la hoja ya está leída antes
   del primer pintado.
   ===================================================================== */
(function () {
  'use strict';

  var LLAVE = 'titan.lateral';
  var raiz = document.documentElement;

  /* Las pantallas del teléfono no la llevan: el QR de la goma se escanea
     parado al lado de la unidad y ahí el ancho es todo. La portada tiene
     la suya adentro de su grilla y se encoge sola. La misma lista vive en
     gomeria/lateral.py, que decide a qué pantalla le pone el marcado. */
  var SIN_BARRA = ['/movil', '/handheld', '/u/'];

  function donde() { return location.pathname.replace(/\/+$/, '') || '/'; }

  function corresponde() {
    /* La portada mete a Titán adentro de un iframe (/asistente?embed=1).
       Ahí no va barra —ya se ve la de afuera— y tampoco hay que correrle
       el cuerpo: el iframe mide lo que mide la tarjeta. */
    if (location.search.indexOf('embed=1') !== -1) return false;
    var p = donde();
    for (var i = 0; i < SIN_BARRA.length; i++)
      if (p === SIN_BARRA[i] || p.indexOf(SIN_BARRA[i]) === 0) return false;
    return true;
  }

  function guardado() {
    try { return localStorage.getItem(LLAVE); } catch (e) { return null; }
  }

  function recordar(valor) {
    try { localStorage.setItem(LLAVE, valor); } catch (e) { /* modo privado */ }
  }

  if (corresponde()) {
    raiz.dataset.lateral = guardado() === 'chica' ? 'chica' : 'abierta';
    /* La portada la lleva adentro de la grilla; las demás la reciben fija
       y hay que correrles el cuerpo. */
    if (donde() !== '/') raiz.dataset.lateralFija = '1';
  }

  /* Las tres barras: es el dibujo que todo el mundo asocia con abrir y
     cerrar el menú, así que no hace falta explicarlo. */
  var TRES_BARRAS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
    'stroke-width="2" stroke-linecap="round" aria-hidden="true">' +
    '<path d="M4 7h16M4 12h16M4 17h16"/></svg>';

  function boton(caja) {
    var fila = caja.querySelector('.nav-label');
    if (!fila || fila.querySelector('.lateral-boton')) return;

    /* En la portada el rótulo «Módulos» es texto suelto, y un nodo de
       texto no se puede esconder con CSS: encogida la barra seguía
       ocupando el ancho y empujaba al botón fuera del borde. */
    if (!fila.querySelector('span')) {
      var rotulo = document.createElement('span');
      rotulo.textContent = fila.textContent.trim();
      fila.textContent = '';
      fila.appendChild(rotulo);
    }

    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'lateral-boton';
    b.innerHTML = TRES_BARRAS;
    fila.appendChild(b);

    function pintar() {
      var chica = raiz.dataset.lateral === 'chica';
      b.title = chica ? 'Mostrar los nombres' : 'Ocultar la barra';
      b.setAttribute('aria-label', b.title);
      b.setAttribute('aria-expanded', chica ? 'false' : 'true');
    }
    pintar();

    b.addEventListener('click', function () {
      raiz.dataset.lateral = raiz.dataset.lateral === 'chica' ? 'abierta' : 'chica';
      recordar(raiz.dataset.lateral);
      pintar();
    });
  }

  /* ------------------------------------------------------------------
     EL CAJÓN DEL TELÉFONO
     ------------------------------------------------------------------
     En una pantalla angosta la barra no se queda al costado comiéndose el
     ancho: se abre encima con las tres barras del encabezado y se va al
     tocar afuera, como cualquier aplicación del teléfono. Quién manda
     —barra al costado o cajón— lo decide sistema.css por el ancho; acá
     solo se abre y se cierra. */
  var velo = null;

  function cerrarCajon() {
    delete raiz.dataset.cajon;
    if (velo) { velo.remove(); velo = null; }
  }

  function abrirCajon() {
    if (raiz.dataset.cajon) return cerrarCajon();
    raiz.dataset.cajon = 'si';
    velo = document.createElement('button');
    velo.type = 'button';
    velo.className = 'lateral-velo';
    velo.setAttribute('aria-label', 'Cerrar el menú');
    velo.addEventListener('click', cerrarCajon);
    document.body.appendChild(velo);
  }

  function abridor() {
    /* Las pantallas de trabajo tienen header.top; la portada, .topbar. */
    var cab = document.querySelector('header.top') ||
              document.querySelector('header.topbar');
    if (!cab || cab.querySelector('.lateral-abrir')) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'lateral-abrir';
    b.title = 'Módulos';
    b.setAttribute('aria-label', 'Abrir el menú de módulos');
    b.innerHTML = TRES_BARRAS;
    b.addEventListener('click', abrirCajon);
    cab.insertBefore(b, cab.firstChild);
  }

  function arrancar() {
    var caja = document.querySelector('aside.sidebar');
    if (!caja) return;
    boton(caja);
    abridor();
    /* Al elegir un módulo la pantalla cambia igual, pero si es la misma
       el cajón quedaría abierto tapándola. */
    caja.addEventListener('click', function (ev) {
      if (ev.target.closest('a')) cerrarCajon();
    });
    document.addEventListener('keydown', function (ev) {
      if (ev.key === 'Escape') cerrarCajon();
    });
    /* Al girar el teléfono o agrandar la ventana manda la barra al
       costado: un velo colgado ahí taparía la pantalla entera. */
    addEventListener('resize', cerrarCajon);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', arrancar);
  else
    arrancar();
})();
