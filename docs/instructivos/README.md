# Guías rápidas

Dos guías de dos hojas A4 verticales cada una, con la estética y el logo
de Titán Fleet Management. No nombran a ninguna empresa cliente: sirven
para cualquiera.

| Archivo | Para quién |
|---|---|
| `guia-taller.pdf` (`guia-taller-1.png`, `-2.png`) | Taller: entrar, escanear la unidad, gomería y stock, en handheld y celular |
| `guia-choferes.pdf` (`guia-choferes-1.png`, `-2.png`) | Choferes: primera vez, escanear el QR, informar la falla, sin señal y seguimiento |

Fuentes: `taller.html`, `choferes.html` y `estilo.css`. En `img/` están las
capturas de las pantallas reales (`handheld.html`, `choferes/` y el
ingreso) con datos de ejemplo, la etiqueta QR real de una unidad, los
logos y las ilustraciones (`operario.svg`, `chofer.svg`). Las pantallas
van dentro de un dibujo de handheld o de celular hecho con CSS.

Para regenerar el PDF: abrir el HTML en Chrome e imprimir en A4, sin
márgenes y con gráficos de fondo.
