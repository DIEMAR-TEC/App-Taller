# Handheld: terminal con lector

Pantalla `/handheld` y app Android (`android/`) para la terminal del
depósito y la gomería.

## Qué hace

- **Baja de repuestos.** Se fija la patente de destino (a mano o
  escaneando el QR de la unidad) y cada QR de repuesto escaneado registra
  una **salida de 1 unidad** para esa patente, al instante. Si el repuesto
  no tiene stock registrado, o si está marcado *Confirmar cada baja*, pide
  confirmación. Quien tiene el permiso «gestiona» puede anular una baja de
  la lista. Las salidas pasan al gasto de la unidad igual que las cargadas
  en `/repuestos`.
- **Movimiento de stock.** Entrada (con costo opcional), salida o ajuste,
  con cantidad.
- **Gomería.** Se escanea la unidad (patente, interno o el QR
  `/gomeria/u/PATENTE`), se toca una posición y se **retira** (destino y
  motivo) o se **monta** (escaneando o tipeando el número de fuego).

- **Registrar trabajo de gomería.** El parte escrito o dictado, como en
  `/movil`: lo interpreta la API de Claude (`/api/interpretar`), se muestra
  la propuesta y se guarda solo al confirmar. Al terminar de dictar se
  interpreta solo. El dictado usa el reconocedor de voz de Android (en la
  APK) o el de Chrome (en el navegador); si el equipo no tiene ninguno, el
  botón no aparece o avisa.
- **Ficha de la unidad** (`/handheld/u/PATENTE`, la historia clínica):
  datos de la unidad, km actual y de los últimos 30 días, litros y L/100 km
  de los últimos seis meses, documentos vencidos o por vencer, órdenes de
  trabajo con su costo, cubiertas puestas y últimos movimientos de gomería.
  Desde ahí: **Cubiertas** (retirar y montar), **Registrar trabajo**,
  **Orden interna** y **Servicio externo** (abren `/movil` con la unidad
  elegida). Los datos salen de `/api/handheld/unidad`, que arma la misma
  ficha de Flota más el combustible.
- **QR para imprimir** (`/handheld/qr`, solo con el permiso «gestiona»,
  desde la computadora; no tiene acceso desde la handheld): uno grande de «Registrar trabajo»
  y uno por unidad que abre su ficha. Sirven con la handheld y con la
  cámara de cualquier celular. Los QR viejos de gomería (`/gomeria/u/…`)
  escaneados con la handheld también abren la ficha.

Desde el inicio, cualquier código escaneado va a donde corresponde: el QR
de un repuesto a la baja, el de una unidad a su ficha y el de registrar
trabajo al parte.

Usa las mismas API y permisos que Repuestos y Gomería. Abre con el módulo
Repuestos o Gomería; montar y retirar cubiertas pide «gestiona».

## Cómo entra el código

1. **Lector en modo teclado** (lo normal en Zebra, Honeywell, Urovo,
   Chainway, Sunmi): escribe el código en el campo y manda Enter. No hay
   que configurar nada, salvo que el lector agregue el Enter al final.
   Si el lector no manda Enter, una pausa de 300 ms cierra la lectura.
2. **Zebra**: al abrir, la APK crea en DataWedge el perfil
   `TitanHandheld` asociado a la app, con salida por broadcast
   (`com.titanflota.handheld.SCAN`) y sin teclado. No hace falta tocar
   DataWedge.
3. **Lector por broadcast** de otras marcas: la app escucha las acciones más comunes
   (lista en `MainActivity.ACCIONES`). En Zebra DataWedge se puede usar la
   acción `com.titanflota.handheld.SCAN` con entrega por *Broadcast intent*.
4. **Cámara**: botón *Cámara*, lee QR con el detector del sistema o jsQR.

El QR de las etiquetas trae la dirección `/repuestos/CÓDIGO`; también se
acepta el código pelado o el código interno.

Si el navegador del sistema (Android System WebView) es demasiado viejo
para la pantalla, se muestra un aviso con su versión.

## La APK

- La compila GitHub Actions (`.github/workflows/apk.yml`) cada vez que
  cambia `android/`, o a mano desde la pestaña Actions.
- Queda para bajar en la release **handheld-apk** del repositorio
  (`titan-handheld.apk`) y como artefacto de la corrida.
- Instalación: copiar la APK a la terminal, abrirla y permitir *instalar
  apps de origen desconocido*.
- Firma: con los secretos del repositorio `HANDHELD_KEYSTORE` (el
  keystore en base64, alias `handheld`) y `HANDHELD_CLAVE`, todas las
  compilaciones salen con la misma firma y la versión nueva se instala
  encima. Sin esos secretos cada compilación tiene firma propia y para
  actualizar hay que desinstalar la anterior.
- Abre `https://app.titanfleetmanagement.com/handheld`. La dirección es fija:
  la terminal la usan los empleados y no hay forma de cambiarla desde la app.
- La pantalla vive en el servidor: un cambio en `handheld.html` llega a
  todas las terminales sin reinstalar.

## Verificación

- `node tests/handheld_smoke.cjs` (Playwright, API simulada).
