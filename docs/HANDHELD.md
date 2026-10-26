# Handheld: terminal con lector

Pantalla `/handheld` y app Android (`android/`) para la terminal del
depósito y la gomería.

## Qué hace

El inicio tiene tres cosas: el campo para escanear el QR de la unidad,
**Movimiento de gomería** y **Movimiento de stock**.

- **Registro de la unidad** (`/handheld/u/PATENTE`, lo que abre el QR
  pegado en el camión): datos, km actual y de los últimos 30 días, litros
  y L/100 km de los últimos seis meses, documentos vencidos o por vencer,
  órdenes con su costo, cubiertas puestas y últimos movimientos de
  gomería. Desde ahí: **Movimiento de gomería** y **Movimiento de stock**
  para esa unidad, y **Orden interna** / **Servicio externo** (abren
  `/movil` con la unidad elegida). Los datos salen de
  `/api/handheld/unidad`: la ficha de Flota más el combustible.
- **Movimiento de gomería**: el parte escrito o dictado, como en `/movil`.
  Lo interpreta la API de Claude (`/api/interpretar`), se muestra la
  propuesta y se guarda solo al confirmar. El dictado se suma al texto y
  no se manda solo: el reconocedor corta en cada pausa y se puede seguir
  dictando. Lo escrito queda guardado en el equipo hasta confirmar, así una
  recarga no lo borra. Abajo, **Retirar o montar por posición**.
- **Movimiento de stock**: en **Salida** (la opción de entrada) se fija
  la unidad que recibe y cada QR de repuesto escaneado sale de a uno para
  esa unidad, al instante; si no hay stock registrado pide confirmar.
  **Entrada** y **Ajuste**: se escanea, se pone la cantidad y se registra.
  Quien tiene «gestiona» puede anular desde la lista.
- **QR para imprimir** (`/handheld/qr`, solo con «gestiona», desde la
  computadora): uno grande de «Movimiento de gomería» y uno por unidad de
  95 × 68 mm (8 por A4) con el logo arriba y en el centro del QR (corrección
  de errores H). Sirven con la handheld y con la cámara de un celular.

Usa las mismas API y permisos que Repuestos y Gomería; la pantalla abre
con el módulo Repuestos o Gomería. Retirar y montar por posición pide
«gestiona».

## Cómo entra el código

1. **Lector en modo teclado** (lo normal en Zebra, Honeywell, Urovo,
   Chainway, Sunmi): escribe el código en el campo y manda Enter. No hay
   que configurar nada, salvo que el lector agregue el Enter al final.
   Si el lector no manda Enter, una pausa de 300 ms cierra la lectura,
   solo si los caracteres llegaron a ritmo de lector (menos de 40 ms cada
   uno): lo tipeado a mano espera el Enter.
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

Todas las consultas van con `credentials: 'same-origin'`: los WebView
anteriores a Chrome 72 no mandan la cookie de sesión en un `fetch` si no
se les pide, y el servidor contestaba «sesión cerrada».

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
