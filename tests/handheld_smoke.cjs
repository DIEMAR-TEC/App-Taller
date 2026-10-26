// La pantalla de la handheld (handheld.html) con la API simulada.
//
// Se verifica lo que hace el operario: fijar la patente, escanear el QR
// de un repuesto —como lo escribe el lector en modo teclado y como lo
// manda la APK por broadcast— y que cada escaneo sea una salida de una
// unidad; el movimiento con cantidad; y retirar y montar en Gomería.
const {chromium} = require('playwright');
const fs = require('fs'), path = require('path'), assert = require('assert');
const dir = path.resolve(__dirname, '..');

const ARTS = [
  {codigo: 'FIL-001', descripcion: 'Filtro de aceite', rubro: 'Filtros', interno: 'I-77', activo: true},
  {codigo: 'COR 2', descripcion: 'Correa', rubro: 'Motor', interno: '', activo: true},
];

(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.BROWSER_PATH ? {executablePath: process.env.BROWSER_PATH} : {})});
  const posts = [];
  let movs = [{id: 1, codigo: 'FIL-001', tipo: 'Entrada', cantidad: 5}];
  let mapa = [
    {posicion_id: 11, posicion: 'D1I', cubierta_id: 501, cubierta: 'F100', medida: '295/80R22.5', remanente_mm: 12},
    {posicion_id: 12, posicion: 'D1D', cubierta_id: null, cubierta: null},
  ];
  try {
    const page = await browser.newPage({viewport: {width: 400, height: 800}});
    const errores = [];
    page.on('pageerror', e => errores.push(e.message));
    page.on('dialog', d => d.accept());
    await page.route('**/*', async route => {
      const req = route.request();
      const url = new URL(req.url());
      const p = url.pathname;
      if (p === '/api/handheld/unidad') {
        if (url.searchParams.get('patente') !== 'AD247MQ')
          return route.fulfill({status: 404, json: {error: 'No se encontró la unidad AD247MQ.'}});
        return route.fulfill({json: {
          unidad: {id: 7, patente: 'AD247MQ', interno: '12', marca: 'Scania', chofer: 'Pérez', km_actual: 512345},
          recorrido: {km: 8200, dias: 28},
          combustible: [{mes: '2026-10-01', litros: 2950, km: 8100, litros_100km: 36.4},
                        {mes: '2026-09-01', litros: 3100, km: null, litros_100km: null, sin_consumo: 'sin lecturas'}],
          ordenes: {total: 450000, ordenes: [{numero: 'OT-0012', fecha: '2026-10-10', tipo: 'interna', estado: 'abierta',
                                              mantenimiento: 'correctivo', solicitado: 'Pérdida de aire', total: 120000}]},
          cubiertas: [{posicion: 'D1I', cubierta: 'F100', marca: 'Fate', remanente_mm: 12}],
          documentos: [{tipo: 'VTV', vence: '2026-10-01', estado: 'vencido'}],
          gomeria: [{fecha: '2026-10-20', tipo: 'montaje', cubierta: 'F100', hasta: 'D1I'}]}});
      }
      if (p === '/handheld' || p.startsWith('/handheld/u/')) return route.fulfill({path: path.join(dir, 'handheld.html'), contentType: 'text/html'});
      if (p === '/vendor/jsQR.js') return route.fulfill({path: path.join(dir, 'vendor/jsQR.js')});
      if (p === '/api/yo') return route.fulfill({json: {nombre: 'Operario', usuario: 'op'}});
      if (p === '/api/repuestos' && req.method() === 'GET')
        return route.fulfill({json: {arts: ARTS, movs, puede_gestionar: true}});
      if (p === '/api/repuestos') {
        const d = req.postDataJSON();
        posts.push(d);
        if (d.op === 'movimiento_crear') {
          const id = 100 + posts.length;
          movs.push({id, ...d.movimiento});
          return route.fulfill({json: {id}});
        }
        return route.fulfill({json: {ok: true}});
      }
      if (p === '/api/mapa') {
        if (url.searchParams.get('patente') !== 'AD247MQ')
          return route.fulfill({status: 404, json: {error: 'No se encontró la unidad.'}});
        return route.fulfill({json: {unidad: {id: 7, patente: 'AD247MQ', marca: 'Scania'}, mapa}});
      }
      if (p === '/api/interpretar') {
        const d = req.postDataJSON();
        posts.push({op: 'interpretar', ...d});
        return route.fulfill({json: {parte_id: 55, unidad: {patente: 'AD247MQ'},
          propuesta: {resumen: 'Cambio en 3 eje', acciones: [{tipo: 'montar', posicion: '3I', cubierta: '079'}]}}});
      }
      if (p === '/api/confirmar') {
        posts.push({op: 'confirmar', ...req.postDataJSON()});
        return route.fulfill({json: {hecho: ['079 montada en 3I']}});
      }
      if (p === '/api/gomeria/stock')
        return route.fulfill({json: [{id: 900, codigo: 'F200', medida: '295/80R22.5', estado: 'stock'}]});
      if (p === '/api/gomeria/posicion') {
        const d = req.postDataJSON();
        posts.push(d);
        if (d.accion === 'desmontar') mapa = mapa.map(x => x.posicion_id === d.posicion_id ? {...x, cubierta_id: null, cubierta: null} : x);
        if (d.accion === 'montar') mapa = mapa.map(x => x.posicion_id === d.posicion_id ? {...x, cubierta_id: d.cubierta_id, cubierta: 'F200'} : x);
        return route.fulfill({json: {mapa}});
      }
      return route.fulfill({status: 404, body: ''});
    });

    await page.goto('http://hh.test/handheld');
    assert.ok(await page.evaluate(() => window.__hhListo), 'el código de la página corrió');
    await page.click('[data-ir="v-baja"]');

    // Sin patente, el escaneo no da de baja.
    await page.fill('#b-scan', 'FIL-001');
    await page.press('#b-scan', 'Enter');
    await page.waitForSelector('#b-estado .estado.mal');
    assert.strictEqual(posts.length, 0);

    await page.fill('#b-patente', 'ad 247 mq');
    await page.press('#b-patente', 'Enter');
    assert.strictEqual(await page.inputValue('#b-patente'), 'AD247MQ');

    // El QR de la etiqueta trae la dirección completa: es una salida de 1.
    await page.focus('#b-scan');
    await page.keyboard.type('https://app.test/repuestos/FIL-001');
    await page.keyboard.press('Enter');
    await page.waitForSelector('#b-estado .estado.bien');
    let ult = posts.at(-1).movimiento;
    assert.deepStrictEqual([ult.codigo, ult.tipo, ult.cantidad, ult.patente], ['FIL-001', 'Salida', 1, 'AD247MQ']);
    assert.match(await page.textContent('#b-estado'), /queda 4/);

    // El código con espacio viaja codificado en la dirección; y por broadcast.
    await page.evaluate(() => window.alEscanear('https://app.test/repuestos/COR%202'));
    // La correa no tiene stock: pide confirmación antes de dar de baja.
    await page.waitForSelector('#b-si');
    assert.strictEqual(posts.length, 1);
    await page.click('#b-si');
    await page.waitForFunction(() => document.querySelectorAll('#b-lista li').length === 2);
    assert.strictEqual(posts.at(-1).movimiento.codigo, 'COR 2');

    // El código interno también encuentra el repuesto.
    await page.evaluate(() => window.alEscanear('I-77'));
    await page.waitForFunction(() => document.querySelectorAll('#b-lista li').length === 3);
    assert.strictEqual(posts.at(-1).movimiento.codigo, 'FIL-001');

    // Anular la última baja.
    await page.click('#b-lista [data-anular="0"]');
    await page.waitForSelector('#b-lista li.anulado');
    assert.strictEqual(posts.at(-1).op, 'movimiento_borrar');

    // Código desconocido.
    await page.evaluate(() => window.alEscanear('NO-EXISTE'));
    await page.waitForFunction(() => /no encontrado/.test(document.querySelector('#b-estado').textContent));

    // Movimiento de stock: entrada de 10 con costo.
    await page.click('#volver');
    await page.click('[data-ir="v-stock"]');
    await page.evaluate(() => window.alEscanear('FIL-001'));
    await page.waitForSelector('#s-ficha .ficha');
    await page.fill('#s-cantidad', '10');
    await page.fill('#s-costo', '1500');
    await page.click('#s-guardar');
    await page.waitForSelector('#s-estado .estado.bien');
    ult = posts.at(-1).movimiento;
    assert.deepStrictEqual([ult.tipo, ult.cantidad, ult.costo_unitario], ['Entrada', 10, '1500']);

    // Gomería: retirar y montar.
    await page.click('#volver');
    await page.click('[data-ir="v-gomeria"]');
    await page.evaluate(() => window.alEscanear('https://app.test/gomeria/u/AD247MQ'));
    await page.waitForSelector('.pos[data-pos="0"]');
    await page.click('.pos[data-pos="0"]');
    await page.click('#g-retirar');
    assert.strictEqual(posts.filter(x => x.accion).length, 0, 'sin motivo no se retira');
    await page.fill('#g-motivo', 'Corte lateral');
    await page.selectOption('#g-destino', 'baja');
    await page.click('#g-retirar');
    await page.waitForFunction(() => /retirada/.test(document.querySelector('#g-estado').textContent));
    assert.deepStrictEqual([posts.at(-1).accion, posts.at(-1).destino, posts.at(-1).cubierta_esperada], ['desmontar', 'baja', 501]);

    await page.click('.pos[data-pos="1"]');
    await page.waitForSelector('#g-fuego');
    await page.evaluate(() => window.alEscanear('f200'));
    await page.waitForFunction(() => /montada/.test(document.querySelector('#g-estado').textContent));
    assert.deepStrictEqual([posts.at(-1).accion, posts.at(-1).cubierta_id, posts.at(-1).posicion_id], ['montar', 900, 12]);

    // Registrar trabajo: el QR de la unidad desde el inicio abre su ficha,
    // y de ahí el parte con la unidad elegida.
    await page.click('#volver');
    await page.evaluate(() => window.alEscanear('https://app.test/gomeria/u/AD247MQ'));
    await page.waitForSelector('#v-unidad.on [data-acc="trabajo"]');
    await page.click('[data-acc="trabajo"]');
    await page.waitForSelector('#v-trabajo.on');
    await page.fill('#t-texto', '3 eje izquierdo entra Michelin 079');
    await page.click('#t-interpretar');
    await page.waitForSelector('#t-confirmar');
    assert.deepStrictEqual([posts.at(-1).op, posts.at(-1).patente], ['interpretar', 'AD247MQ']);
    await page.click('#t-confirmar');
    await page.waitForFunction(() => /guardado/.test(document.querySelector('#t-salida').textContent));
    assert.deepStrictEqual([posts.at(-1).op, posts.at(-1).parte_id], ['confirmar', 55]);

    // El dictado que devuelve la APK se interpreta solo.
    await page.evaluate(() => window.alDictar('sale la 380 para recapar'));
    await page.waitForSelector('#t-confirmar');
    assert.strictEqual(posts.at(-1).texto, 'sale la 380 para recapar');

    // El QR de «registrar trabajo» desde el inicio.
    await page.click('#volver');
    await page.evaluate(() => window.alEscanear('https://app.test/handheld#v-trabajo'));
    await page.waitForSelector('#v-trabajo.on');

    // Un lector sin Enter: el código escrito de golpe se toma igual.
    await page.click('#volver');
    const antes = posts.length;
    await page.focus('#i-scan');
    await page.keyboard.insertText('https://app.test/repuestos/FIL-001');
    await page.waitForFunction(n => document.querySelector('#v-baja.on') && document.querySelectorAll('#b-lista li').length > 3, antes);
    assert.strictEqual(posts.at(-1).movimiento.codigo, 'FIL-001');

    // El QR pegado en el camión abre su ficha.
    await page.goto('http://hh.test/handheld/u/AD247MQ');
    await page.waitForSelector('#v-unidad.on .kpi');
    const ficha = await page.textContent('#u-ficha');
    for (const t of ['512.345', '8.200', '2.950', '36,4', 'OT-0012', 'Pérdida de aire', 'VTV', 'F100'])
      assert.ok(ficha.includes(t), 'falta ' + t + ' en la ficha');
    assert.strictEqual(await page.getAttribute('a[href*="#v-orden"]', 'href'), '/movil?patente=AD247MQ#v-orden');
    assert.strictEqual(await page.getAttribute('a[href*="#v-externo"]', 'href'), '/movil?patente=AD247MQ#v-externo');
    await page.click('[data-acc="cubiertas"]');
    await page.waitForSelector('#v-gomeria.on .pos');
    // Desde el inicio, el QR de una unidad abre la ficha.
    await page.click('#volver');
    await page.evaluate(() => window.alEscanear('https://app.test/handheld/u/AD247MQ'));
    await page.waitForSelector('#v-unidad.on .kpi');

    assert.deepStrictEqual(errores, []);
    console.log('handheld_smoke: ok');
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
