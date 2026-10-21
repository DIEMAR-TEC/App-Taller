// Los esqueletos de carga que esqueleto.js pone en todas las pantallas.
//
// Se abre Órdenes con la API demorada: mientras espera, la tabla tiene que
// mostrar filas grises con una barra por columna y el pie un renglón gris,
// sin el texto "Cargando…" a la vista. Cuando llegan los datos, el
// esqueleto se va.
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path'), assert = require('assert');
const dir = path.resolve(__dirname, '..');

(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.BROWSER_PATH ? {executablePath: process.env.BROWSER_PATH} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 1280, height: 800}});
    const errores = [];
    page.on('pageerror', e => errores.push(e.message));
    let soltar;
    const demora = new Promise(r => { soltar = r; });

    await page.route('**/*', async route => {
      const url = new URL(route.request().url());
      if (url.pathname === '/ordenes') {
        const cuerpo = fs.readFileSync(path.join(dir, 'ordenes.html'), 'utf8')
          .replace('</head>', '<script src="/tema.js"></script><script src="/esqueleto.js"></script>' +
                              '<link rel="stylesheet" href="/sistema.css"></head>');
        return route.fulfill({body: cuerpo, contentType: 'text/html'});
      }
      if (url.pathname.startsWith('/api/')) {
        await demora;
        return route.fulfill({status: 500, json: {error: 'Sin datos de prueba.'}});
      }
      const archivo = path.join(dir, url.pathname.slice(1));
      if (fs.existsSync(archivo) && fs.statSync(archivo).isFile())
        return route.fulfill({path: archivo});
      return route.fulfill({status: 404, body: ''});
    });

    await page.goto('http://taller.test/ordenes', {waitUntil: 'domcontentloaded'});

    // La tabla: varias filas grises, tantas celdas como columnas.
    const filas = page.locator('#filas tr.esq-fila');
    assert.equal(await filas.count(), 6, 'la tabla no muestra las filas del esqueleto');
    const columnas = await page.locator('#filas').evaluate(
      t => t.closest('table').querySelectorAll('thead tr:first-child > *').length);
    assert.equal(await filas.first().locator('td').count(), columnas,
                 'el esqueleto no tiene una celda por columna');
    assert.equal(await page.locator('#filas .esq').first().isVisible(), true);

    // El texto sigue para el lector de pantalla, pero no se ve.
    const oculto = await page.locator('#filas .esq-oculto').boundingBox();
    assert(oculto.width <= 1, 'el "Cargando…" de la tabla se sigue viendo');

    // El pie: un renglón gris en el lugar del texto.
    assert(await page.locator('#pie').evaluate(p => p.classList.contains('esq-texto')),
           'el pie no se tapó con gris');
    assert.equal(await page.locator('#pie').evaluate(p => getComputedStyle(p).color),
                 'rgba(0, 0, 0, 0)', 'el texto del pie se sigue viendo');

    // Llegan los datos (acá, un error): el esqueleto se va.
    soltar();
    await page.waitForFunction(() => !document.querySelector('#filas .esq-fila'));
    await page.waitForFunction(() => !document.querySelector('#pie').classList.contains('esq-texto'));

    // Un "Cargando…" que la pantalla escribe después también se convierte.
    await page.evaluate(() => {
      const d = document.createElement('div');
      d.id = 'prueba';
      d.innerHTML = '<p class="vacio">Cargando…</p>';
      document.body.appendChild(d);
    });
    await page.waitForFunction(() => document.querySelector('#prueba .esq-renglones'));

    // Y un texto que no es solo la espera queda como está.
    await page.evaluate(() => {
      const p = document.createElement('p');
      p.id = 'frase';
      p.innerHTML = 'Se autorizó en ruta y se está cargando después';
      document.body.appendChild(p);
    });
    await page.waitForTimeout(50);
    assert(!(await page.locator('#frase').evaluate(p => p.classList.contains('esq-texto'))));

    assert.deepEqual(errores, [], `errores en la página: ${errores.join(' | ')}`);
    console.log('esqueleto: ok');
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
