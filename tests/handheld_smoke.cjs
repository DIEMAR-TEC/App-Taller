// La pantalla de la handheld (handheld.html) con la API simulada.
//
// Se verifica lo que hace el operario: escanear la unidad y ver su
// registro; desde ahí sacar repuestos de a uno escaneando y cargar el
// movimiento de gomería escrito o dictado; entradas con cantidad; y
// retirar y montar por posición.
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

    // Los WebView viejos no mandan la cookie si el fetch no la pide: sin
    // esto, la handheld veía «sesión cerrada» con la sesión abierta.
    for (const f of ['handheld.html', 'telefono.html']) {
      const codigo = fs.readFileSync(path.join(dir, f), 'utf8');
      const llamadas = codigo.match(/fetch\([^;]*;/g) || [];
      for (const ll of llamadas)
        assert.ok(/credentials/.test(ll) || /fetch\(url, cuerpo/.test(ll), `${f}: fetch sin credentials: ${ll.slice(0, 60)}`);
    }

    await page.goto('http://hh.test/handheld');
    assert.ok(await page.evaluate(() => window.__hhListo), 'el código de la página corrió');
    // El inicio: el escáner y dos accesos, nada más.
    assert.strictEqual(await page.locator('#v-inicio .tile').count(), 2);
    assert.strictEqual(await page.locator('text=Dirección del servidor').count(), 0);
    assert.strictEqual(await page.locator('a[href="/handheld/qr"]').count(), 0);

    // Tipear una patente a mano no dispara la búsqueda letra por letra.
    await page.click('#v-inicio [data-teclado="i-scan"]');
    await page.focus('#i-scan');
    for (const c of 'AD247') { await page.keyboard.type(c); await page.waitForTimeout(120); }
    await page.waitForTimeout(500);
    assert.ok(await page.isVisible('#v-inicio'), 'sigue en el inicio mientras se tipea');
    await page.keyboard.type('MQ');
    await page.keyboard.press('Enter');
    await page.waitForSelector('#v-unidad.on .kpi');

    // El registro de la unidad.
    const ficha = await page.textContent('#u-ficha');
    for (const t of ['512.345', '8.200', '2.950', '36,4', 'OT-0012', 'Pérdida de aire', 'VTV', 'F100'])
      assert.ok(ficha.includes(t), 'falta ' + t + ' en la ficha');
    assert.strictEqual(await page.getAttribute('a[href*="#v-orden"]', 'href'), '/movil?patente=AD247MQ#v-orden');

    // Movimiento de stock desde la unidad: cada escaneo es una salida de 1.
    await page.click('[data-acc="stock"]');
    await page.waitForSelector('#v-stock.on');
    assert.strictEqual(await page.inputValue('#s-patente'), 'AD247MQ');
    await page.focus('#s-scan');
    await page.keyboard.type('https://app.test/repuestos/FIL-001');
    await page.keyboard.press('Enter');
    await page.waitForSelector('#s-estado .estado.bien');
    let ult = posts.at(-1).movimiento;
    assert.deepStrictEqual([ult.codigo, ult.tipo, ult.cantidad, ult.patente], ['FIL-001', 'Salida', 1, 'AD247MQ']);
    assert.match(await page.textContent('#s-estado'), /queda 4/);

    // Sin stock pide confirmar; el código interno también encuentra.
    await page.evaluate(() => window.alEscanear('https://app.test/repuestos/COR%202'));
    await page.waitForSelector('#s-si');
    await page.click('#s-si');
    await page.waitForFunction(() => document.querySelectorAll('#s-lista li').length === 2);
    assert.strictEqual(posts.at(-1).movimiento.codigo, 'COR 2');
    await page.evaluate(() => window.alEscanear('I-77'));
    await page.waitForFunction(() => document.querySelectorAll('#s-lista li').length === 3);
    await page.click('#s-lista [data-anular="0"]');
    await page.waitForSelector('#s-lista li.anulado');
    assert.strictEqual(posts.at(-1).op, 'movimiento_borrar');

    // Entrada con cantidad y costo.
    await page.click('#s-tipo [data-tipo="Entrada"]');
    assert.ok(await page.isHidden('#s-patente-caja'));
    await page.evaluate(() => window.alEscanear('FIL-001'));
    await page.waitForSelector('#s-detalle:not([hidden])');
    await page.fill('#s-cantidad', '10');
    await page.fill('#s-costo', '1500');
    await page.click('#s-guardar');
    await page.waitForFunction(() => /Entrada registrada/.test(document.querySelector('#s-estado').textContent));
    ult = posts.at(-1).movimiento;
    assert.deepStrictEqual([ult.tipo, ult.cantidad, ult.costo_unitario], ['Entrada', 10, '1500']);

    // Movimiento de gomería desde la unidad: escrito, dictado y confirmado.
    await page.goto('http://hh.test/handheld/u/AD247MQ');
    await page.waitForSelector('#v-unidad.on [data-acc="trabajo"]');
    await page.click('[data-acc="trabajo"]');
    await page.waitForSelector('#v-trabajo.on');
    await page.fill('#t-texto', '3 eje izquierdo entra Michelin 079');
    // El dictado se suma y no se manda solo.
    await page.evaluate(() => window.alDictar('sale la 380 para recapar'));
    assert.strictEqual(await page.inputValue('#t-texto'), '3 eje izquierdo entra Michelin 079 sale la 380 para recapar');
    assert.ok(!posts.some(x => x.op === 'interpretar'), 'el dictado no interpreta solo');
    // Lo escrito sobrevive a una recarga.
    await page.reload();
    await page.waitForSelector('#v-trabajo.on');
    assert.match(await page.inputValue('#t-texto'), /sale la 380/);
    await page.click('#t-interpretar');
    await page.waitForSelector('#t-confirmar');
    assert.deepStrictEqual([posts.at(-1).op, posts.at(-1).patente], ['interpretar', 'AD247MQ']);
    await page.click('#t-confirmar');
    await page.waitForFunction(() => /guardado/.test(document.querySelector('#t-salida').textContent));
    assert.deepStrictEqual([posts.at(-1).op, posts.at(-1).parte_id], ['confirmar', 55]);
    assert.strictEqual(await page.inputValue('#t-texto'), '');

    // Por posición: retirar y montar.
    await page.click('#t-posiciones');
    await page.waitForSelector('#v-gomeria.on .pos[data-pos="0"]');
    await page.click('.pos[data-pos="0"]');
    await page.fill('#g-motivo', 'Corte lateral');
    await page.selectOption('#g-destino', 'baja');
    await page.click('#g-retirar');
    await page.waitForFunction(() => /retirada/.test(document.querySelector('#g-estado').textContent));
    assert.deepStrictEqual([posts.at(-1).accion, posts.at(-1).destino], ['desmontar', 'baja']);
    await page.click('.pos[data-pos="1"]');
    await page.waitForSelector('#g-fuego');
    await page.evaluate(() => window.alEscanear('f200'));
    await page.waitForFunction(() => /montada/.test(document.querySelector('#g-estado').textContent));
    assert.deepStrictEqual([posts.at(-1).accion, posts.at(-1).cubierta_id], ['montar', 900]);

    // Desde el inicio: el QR de un repuesto lleva al stock; el lector sin
    // Enter (todo de golpe) se toma igual.
    await page.click('#volver');
    await page.focus('#i-scan');
    await page.keyboard.insertText('https://app.test/repuestos/FIL-001');
    await page.waitForSelector('#v-stock.on');
    // El QR de la unidad abre su registro.
    await page.click('#volver');
    await page.evaluate(() => window.alEscanear('https://app.test/handheld/u/AD247MQ'));
    await page.waitForSelector('#v-unidad.on .kpi');

    assert.deepStrictEqual(errores, []);
    console.log('handheld_smoke: ok');
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exit(1); });
