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

Usa las mismas API y permisos que Repuestos y Gomería. Abre con el módulo
Repuestos o Gomería; montar y retirar cubiertas pide «gestiona».

## Cómo entra el código

1. **Lector en modo teclado** (lo normal en Zebra, Honeywell, Urovo,
   Chainway, Sunmi): escribe el código en el campo y manda Enter. No hay
   que configurar nada, salvo que el lector agregue el Enter al final.
2. **Lector por broadcast**: la app escucha las acciones más comunes
   (lista en `MainActivity.ACCIONES`). En Zebra DataWedge se puede usar la
   acción `com.titanflota.handheld.SCAN` con entrega por *Broadcast intent*.
3. **Cámara**: botón *Cámara*, lee QR con el detector del sistema o jsQR.

El QR de las etiquetas trae la dirección `/repuestos/CÓDIGO`; también se
acepta el código pelado o el código interno.

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
- Abre `https://app-taller-cu5d.onrender.com/handheld`. La dirección se
  cambia con el botón *Dirección del servidor* de la pantalla de inicio de
  la app, o desde la pantalla de error si no hay conexión.
- La pantalla vive en el servidor: un cambio en `handheld.html` llega a
  todas las terminales sin reinstalar.

## Verificación

- `node tests/handheld_smoke.cjs` (Playwright, API simulada).
