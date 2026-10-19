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
            administra: false, modulos: ['vencimientos', 'gomeria', 'repuestos', 'unidades', 'ordenes']};

// El marcado sale de gomeria/lateral.py, que es quien lo arma de verdad.
// Pedírselo a Python en vez de copiarlo evita que la prueba valide una
// barra que el servidor ya no manda.
const {execFileSync} = require('child_process');
function barraDelServidor(ruta) {
  return execFileSync('python3', ['-c',
    'import sys;sys.path.insert(0,"gomeria");import json,lateral;' +
    'print(lateral.barra(json.loads(sys.argv[1]), sys.argv[2]))',
    JSON.stringify(YO), ruta], {cwd: dir, encoding: 'utf8'}).trim();
}

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
      if (pantallas[url.pathname]) {
        let cuerpo = fs.readFileSync(path.join(dir, pantallas[url.pathname]), 'utf8')
          .replace('</head>', '<script src="/lateral.js"></script>' +
                              '<link rel="stylesheet" href="/sistema.css"></head>');
        // Igual que app.py: la barra la arma el servidor y entra en el HTML.
        if (url.pathname !== '/')
          cuerpo = cuerpo.replace(/<body[^>]*>/, m => m + barraDelServidor(url.pathname));
        return route.fulfill({body: cuerpo, contentType: 'text/html'});
      }
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
    assert.equal(await page.locator('aside.lateral a[href="/combustible"]').count(), 0,
                 'se escribió un módulo que el rol no tiene');
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

    // ---------------------------------------------------------------
    // Angosta, la portada no queda en dos columnas: la barra sale del
    // flujo y pasa a ser el cajón. Antes se le forzaban dos columnas y
    // los íconos quedaban apretados en una franja vertical al lado del
    // contenido, encima del panel de Titán.
    // ---------------------------------------------------------------
    await page.setViewportSize({width: 760, height: 1100});
    await page.reload();
    await page.locator('.lateral-abrir').waitFor();
    const columnas = await page.evaluate(
      () => getComputedStyle(document.querySelector('.shell')).gridTemplateColumns);
    assert(!/^\d+(\.\d+)?px \d/.test(columnas),
           `angosta, la portada quedó en dos columnas: ${columnas}`);

    // ---------------------------------------------------------------
    // EL TELÉFONO
    // ---------------------------------------------------------------
    // Una barra fija se come 66 de 390 píxeles y no se puede cerrar: eso
    // no es una barra de celular, es un recorte permanente. Acá tiene que
    // ser un cajón que se abre encima y se va al tocar afuera.
    await page.setViewportSize({width: 390, height: 844});
    for (const ruta of ['/ordenes', '/']) {
      await page.goto('http://taller.test' + ruta);
      await page.locator('.lateral-abrir').waitFor();

      assert.equal(Math.round(await margen()), 0,
                   `${ruta}: en el teléfono la barra le come el ancho a la pantalla`);
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth),
                   390, `${ruta}: la pantalla se va de ancho en el teléfono`);

      // Cerrada, el cajón no está a la vista ni se puede tabular hasta él.
      assert.equal(await page.evaluate(
        () => getComputedStyle(document.querySelector('aside.sidebar')).visibility),
        'hidden', `${ruta}: el cajón quedó alcanzable con la barra cerrada`);

      // El botón tiene que verse: fijarle el blanco lo hacía desaparecer
      // en la portada, que tiene el encabezado claro.
      const contraste = await page.evaluate(() => {
        const b = document.querySelector('.lateral-abrir');
        const luz = c => {
          const [r, g, v] = c.match(/\d+/g).map(Number);
          return (0.299 * r + 0.587 * g + 0.114 * v) / 255;
        };
        let fondo = b, color = getComputedStyle(b).backgroundColor;
        while (fondo && /rgba\(0, 0, 0, 0\)|transparent/.test(color)) {
          fondo = fondo.parentElement;
          color = fondo ? getComputedStyle(fondo).backgroundColor : 'rgb(255,255,255)';
        }
        return Math.abs(luz(getComputedStyle(b).color) - luz(color));
      });
      assert(contraste > 0.25,
             `${ruta}: el botón de las tres barras no se distingue del encabezado`);

      // Se abre encima, sin correr la pantalla.
      await page.click('.lateral-abrir');
      await page.waitForTimeout(350);
      const cajon = await page.locator('aside.sidebar').boundingBox();
      assert.equal(Math.round(cajon.x), 0, `${ruta}: el cajón no llegó al borde`);
      assert(cajon.width >= 240, `${ruta}: el cajón quedó angosto (${cajon.width})`);
      assert.equal(Math.round(await margen()), 0,
                   `${ruta}: abrir el cajón corrió la pantalla en vez de taparla`);
      assert.equal(await page.locator('.lateral-velo').count(), 1,
                   `${ruta}: falta el velo que apaga lo de atrás`);
      // Adentro del cajón se leen los nombres: un ícono solo obliga a adivinar.
      assert(await page.evaluate(() => document.querySelector(
               'aside.sidebar .nav a[href="/repuestos"] span').getBoundingClientRect().width) > 20,
             `${ruta}: el cajón muestra íconos sin nombre`);

      // Y se va al tocar afuera, como cualquier aplicación del teléfono.
      await page.mouse.click(370, 700);
      await page.waitForTimeout(350);
      assert(!await page.evaluate(() => document.documentElement.dataset.cajon),
             `${ruta}: el cajón no se cerró al tocar afuera`);
    }

    assert.deepEqual(errores, [], 'la pantalla tiró errores de JavaScript');
    console.log('lateral_smoke: bien');
  } finally {
    await browser.close();
  }
})();
