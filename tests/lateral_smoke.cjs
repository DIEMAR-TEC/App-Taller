// La barra lateral que lateral.js pone en todas las pantallas.
//
// Lo que se verifica acá no se puede verificar con cadenas: que el cuerpo
// de la pantalla quede al lado de la barra y no abajo, que el botón de
// ocultar recupere el ancho, que la elección se recuerde al cambiar de
// pantalla, y que la portada —que ya trae la suya escrita— no termine con
// dos.
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path'), assert = require('assert');
const dir = path.resolve(__dirname, '..');

const YO = {nombre: 'Nicolás', usuario: 'nico', rol: 'admin', rol_nombre: 'Administrador',
            administra: false, modulos: ['vencimientos', 'gomeria', 'repuestos', 'unidades']};

(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.BROWSER_PATH ? {executablePath: process.env.BROWSER_PATH} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 900}});
    const errores = [];
    page.on('pageerror', e => errores.push(e.message));

    // El servidor de verdad inyecta lateral.js y sistema.css en el encabezado
    // de cada pantalla (app.py). Acá se hace lo mismo.
    const pantallas = {'/vencimientos': 'vencimientos.html', '/ordenes': 'ordenes.html',
                       '/': 'inicio.html'};
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/api/yo') return route.fulfill({json: YO});
      if (url.pathname.startsWith('/api/'))
        return route.fulfill({json: {}});
      if (pantallas[url.pathname])
        return route.fulfill({
          body: fs.readFileSync(path.join(dir, pantallas[url.pathname]), 'utf8')
                  .replace('</head>', '<script src="/lateral.js"></script>' +
                                      '<link rel="stylesheet" href="/sistema.css"></head>'),
          contentType: 'text/html'});
      if (url.pathname === '/logo.png')
        return route.fulfill({body: fs.readFileSync(path.join(dir, 'titan-flota-logo.png')),
                              contentType: 'image/png'});
      const archivo = path.join(dir, url.pathname.slice(1));
      if (fs.existsSync(archivo) && fs.statSync(archivo).isFile())
        return route.fulfill({path: archivo});
      return route.fulfill({status: 404, body: ''});
    });

    const margen = () => page.evaluate(
      () => parseFloat(getComputedStyle(document.body).marginLeft));
    const estado = () => page.evaluate(() => document.documentElement.dataset.lateral);

    // ---------------------------------------------------------------
    // En una pantalla de módulo: la barra está, y el contenido al lado.
    // ---------------------------------------------------------------
    await page.goto('http://taller.test/vencimientos');
    await page.locator('aside.lateral').waitFor();

    const barra = await page.locator('aside.lateral').boundingBox();
    assert.equal(Math.round(barra.width), 230, `la barra mide ${barra.width}`);
    assert.equal(Math.round(await margen()), 230,
                 'el cuerpo no se corrió: la barra le tapa el contenido');

    // Lo de la pantalla arranca después de la barra, no debajo ni abajo.
    const cab = await page.locator('header.top').boundingBox();
    assert(cab.x >= 230, `el encabezado arranca en ${cab.x}, tapado por la barra`);
    assert(cab.y < 120, `el encabezado quedó empujado hacia abajo (y=${cab.y})`);

    // El módulo en el que uno está, marcado.
    assert.equal(await page.locator('aside.lateral a[aria-current="page"]').getAttribute('href'),
                 '/vencimientos');

    // Y se salta a otro módulo sin pasar por el inicio, que es para lo que está.
    assert.equal(await page.locator('aside.lateral a[href="/repuestos"]').count(), 1);

    // ---------------------------------------------------------------
    // Los módulos que el rol no tiene no se listan.
    // ---------------------------------------------------------------
    await page.locator('aside.lateral a[href="/combustible"][hidden]').waitFor({state: 'hidden'});
    assert(await page.locator('aside.lateral a[href="/combustible"]').isHidden(),
           'se listó un módulo que el rol no tiene');
    assert(await page.locator('aside.lateral a[href="/vencimientos"]').isVisible(),
           'se escondió un módulo que el rol sí tiene');
    // Inicio no cuelga de ningún permiso: es la portada de todos.
    assert(await page.locator('aside.lateral .nav a[href="/"]').isVisible());

    // ---------------------------------------------------------------
    // El botón de ocultarla.
    // ---------------------------------------------------------------
    assert.equal(await estado(), 'abierta');
    assert(await page.locator('aside.lateral .nav a[href="/repuestos"] span').isVisible());

    await page.click('.lateral-boton');
    assert.equal(await estado(), 'chica');
    const angosta = Math.round(await margen());
    assert(angosta > 0 && angosta < 80,
           `encogida el cuerpo tendría que arrancar en una tira angosta, arranca en ${angosta}`);
    // El nombre deja de ocupar ancho, pero sigue en el árbol de
    // accesibilidad: un lector de pantalla tiene que poder decir a dónde
    // lleva el ícono. Por eso se mide el ancho y no isVisible(), que da
    // verdadero igual para un texto recortado a un píxel.
    assert(await page.evaluate(() => document.querySelector(
             'aside.lateral .nav a[href="/repuestos"] span')
             .getBoundingClientRect().width) <= 1,
           'encogida sigue mostrando los nombres');
    assert.equal(await page.locator('aside.lateral .nav a[href="/repuestos"]')
                           .getAttribute('title'), 'Repuestos',
                 'encogida el ícono quedó sin nombre que lo explique');
    // Encogida se sigue navegando: los íconos quedan.
    assert(await page.locator('aside.lateral .nav a[href="/repuestos"]').isVisible(),
           'encogida se perdió el acceso al módulo');

    // Y el botón para volver a abrirla sigue a la vista, entero y adentro
    // de la tira. El rótulo «Módulos» es texto suelto y, sin envolverlo,
    // seguía ocupando el ancho y empujaba al botón fuera del borde.
    assert(await page.locator('.lateral-boton').isVisible(),
           'ocultó la barra y también el botón de traerla de vuelta');
    const desborde = await page.evaluate(() => {
      const barra = document.querySelector('aside.lateral');
      const borde = barra.getBoundingClientRect().right;
      return [...barra.querySelectorAll('*')]
        .filter(n => n.getBoundingClientRect().width > 2 &&
                     n.getBoundingClientRect().right > borde + 1)
        .map(n => n.className || n.tagName);
    });
    assert.deepEqual(desborde, [],
                     `encogida se sale de la tira: ${desborde.join(', ')}`);
    await page.click('.lateral-boton');
    assert.equal(await estado(), 'abierta');

    // ---------------------------------------------------------------
    // La elección vale para todas las pantallas, no solo para esta.
    // ---------------------------------------------------------------
    await page.click('.lateral-boton');
    await page.goto('http://taller.test/ordenes');
    await page.locator('aside.lateral').waitFor();
    assert.equal(await estado(), 'chica', 'se olvidó de que estaba oculta');
    assert.equal(await page.locator('aside.lateral a[aria-current="page"]').getAttribute('href'),
                 '/ordenes');

    await page.click('.lateral-boton');          // queda abierta para lo que sigue
    assert.equal(await estado(), 'abierta');

    // ---------------------------------------------------------------
    // La portada ya trae la suya: no le ponemos otra.
    // ---------------------------------------------------------------
    await page.goto('http://taller.test/');
    await page.locator('aside.sidebar .lateral-boton').waitFor();
    assert.equal(await page.locator('aside.sidebar').count(), 1,
                 'la portada terminó con dos barras');
    assert.equal(await page.locator('aside.lateral').count(), 0,
                 'se le inyectó una barra a la portada, que ya tenía la suya');
    assert.equal(Math.round(await margen()), 0,
                 'a la portada se le corrió el cuerpo: su barra va adentro de la grilla');

    // El botón también está ahí, y encoge la columna de la grilla.
    const antes = (await page.locator('aside.sidebar').boundingBox()).width;
    await page.click('.lateral-boton');
    const despues = (await page.locator('aside.sidebar').boundingBox()).width;
    assert(despues < antes - 100,
           `en la portada la barra no encogió (${antes} -> ${despues})`);

    assert.deepEqual(errores, [], 'la pantalla tiró errores de JavaScript');
    console.log('lateral_smoke: bien');
  } finally {
    await browser.close();
  }
})();
