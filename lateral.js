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
  var SIN_BARRA = ['/movil', '/u/'];

  function donde() { return location.pathname.replace(/\/+$/, '') || '/'; }

  function corresponde() {
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

  function arrancar() {
    var caja = document.querySelector('aside.sidebar');
    if (caja) boton(caja);
  }

  if (document.readyState === 'loading')
    document.addEventListener('DOMContentLoaded', arrancar);
  else
    arrancar();
})();
