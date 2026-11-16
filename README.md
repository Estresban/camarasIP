# 📹 Sistema de Videovigilancia Multi-Cámara (RTSP + DVRIP / NetIP)

Aplicación de escritorio en Python para la monitorización, grabación y control en tiempo real de cámaras IP mediante los protocolos **RTSP/ONVIF** y **DVRIP/NetIP (XMeye)**. Incluye soporte para cámaras de doble lente, audio bidireccional, panel de control gráfico personalizado y gestión remota con alertas fotográficas mediante **Telegram**.

---

## 🚀 Funcionalidades Principales

* **Vista en Cuadrícula 2x2:** Visualización simultánea en directo de hasta 4 cámaras (soporte mixto para cámaras RTSP individuales y cámaras DVRIP de doble lente apilada).
* **Panel Lateral Interactivo:** Interfaz dibujada con OpenCV con iconos vectoriales, esquinas redondeadas, efecto *hover* y estados visuales (activo en verde / desactivado con tachado).
* **Control PTZ y Zoom Digital:** Movimiento horizontal/vertical y zoom digital desde el panel lateral, flechas de dirección o teclas `W, A, S, D`.
* **Grabación y Analítica de Movimiento:**
  * Grabación continua en bloques `.mp4` de duración configurable.
  * Detección de movimiento con sensibilidad ajustable y tiempo de espera (*cooldown*) para evitar capturas redundantes.
  * Capturas periódicas programadas y fotografía manual instantánea.
* **Audio Bidireccional:** Escucha en tiempo real del micrófono de la cámara (decodificación G.711 A-law a PCM) y envío de voz desde el PC.
* **Control de Iluminación LED:** Cambio directo entre **Luz Blanca**, **Infrarrojos (IR)** y **Modo Automático** mediante protocolo NetIP.
* **Control Remoto y Alertas en Telegram:**
  * Notificación push instantánea con fotografía al detectar movimiento.
  * Teclado táctil permanente en el chat de Telegram para pedir fotos, activar grabaciones, cambiar luces o consultar el estado por cámara (`/foto1..4`, `/grabar1..4`, `/deteccion1..4`, `/luz1..4`).
* **Editor Visual de Configuración:** Ventana gráfica integrada (Tkinter) para gestionar direcciones IP, credenciales, puertos, carpetas y datos de Telegram sin tocar el código, persistiendo los datos en `config.json`.

---

## 📂 Estructura del Proyecto

```text
videovigilancia/
├── main.py              # Punto de entrada, interfaz OpenCV y gestión de eventos
├── config.py            # Rutas dinámicas, parámetros base y carga de config.json
├── configuracion.py     # Interfaz gráfica (Tkinter) para editar ajustes
├── notificaciones.py    # Módulo de alertas y bot interactivo de Telegram
├── camara_rtsp.py       # Controlador para cámaras RTSP / ONVIF / NetIP
├── camara_dvrip.py      # Controlador para cámaras DVRIP (doble lente)
├── config.json          # (Autogenerado) Configuración personalizada del usuario
└── camarasIP/           # (Autogenerado) Almacenamiento de vídeos e imágenes
    ├── grabaciones/
    ├── capturas_movimiento/
    └── capturas_fotogramas/
```

---

## 🛠️ Instalación y Ejecución

### 1. Requisitos previos
* **Python 3.9** o superior.
* Sistema operativo **Windows** o **Linux**.

### 2. Instalación de dependencias
Ejecuta el siguiente comando en la terminal dentro de la carpeta del proyecto:

```bash
pip install opencv-python numpy sounddevice
```
*(Opcional: Si tus cámaras RTSP utilizan movimiento PTZ mediante ONVIF, instala también `onvif-zeep`).*

### 3. Arranque
```bash
python main.py
```

---

## ⚙️ Configuración Inicial

1. Inicia la aplicación y pulsa el botón **AJUSTES** en la zona inferior del panel derecho.
2. En la pestaña **Cámaras**, introduce la dirección IP, usuario, contraseña y puertos (`554` RTSP, `8899` ONVIF, `34567` NetIP) de tus dispositivos.
3. En la pestaña **General**, configura:
   * El índice del dispositivo de salida de audio de tu equipo.
   * El **Token del Bot de Telegram** (creado con `@BotFather`) y tu **Chat ID** (obtenido mediante `@userinfobot`).
4. Pulsa **Guardar** y reinicia el programa para aplicar la nueva configuración.

---

## ⌨️ Controles y Atajos de Teclado

| Control | Acción |
| :--- | :--- |
| **Clic sobre una cámara** | Seleccionar cámara activa |
| **Flechas / `W A S D`** | Mover PTZ (Arriba, Izquierda, Abajo, Derecha) |
| **`+` / `-` o `Z` / `X`** | Aumentar o reducir zoom digital |
| **`M`** | Activar / desactivar detección de movimiento |
| **`R`** | Iniciar / detener grabación de vídeo |
| **`F`** | Activar / desactivar captura automática periódica |
| **`Espacio`** | Capturar fotografía manual |
| **`V`** | Activar / desactivar escucha de audio |
| **`T`** | Activar / desactivar micrófono |
| **`1` / `2` / `3`** | Cambiar iluminación a Luz Blanca / IR / Auto |
| **`Q` / `Esc` / Botón `X`** | Cerrar el programa y liberar cámaras de forma segura |

---

## 📱 Comandos Remotos en Telegram

Envía `/start` a tu bot de Telegram para desplegar la botonera táctil en pantalla, o escribe directamente cualquiera de los siguientes comandos:

* `/estado` — Resumen del estado de grabación, detección e iluminación de cada cámara.
* `/foto` o `/foto1`..`/foto4` — Envía una captura en directo de todas las cámaras o de una en concreto.
* `/grabar` o `/grabar1`..`/grabar4` — Inicia o detiene la grabación.
* `/deteccion` o `/deteccion1`..`/deteccion4` — Activa o desactiva la detección de movimiento.
* `/luz1`..`/luz4` — Alterna la iluminación de la cámara entre Auto, Blanca e IR.
* `/alertas` — Activa o silencia el envío automático de alertas al móvil.

---

## 📦 Empaquetado a Ejecutable (.exe)

Para compilar el proyecto en una aplicación independiente para Windows sin requerir Python instalado:

```bash
pip install pyinstaller
pyinstaller --onedir --windowed --name "Videovigilancia" main.py
```

El programa compilado quedará listo en `dist/Videovigilancia/`. Si generas un instalador con **Inno Setup**, recuerda asignar permisos de modificación (`Permissions: users-modify`) a la carpeta de destino `{app}` para permitir la escritura de `config.json` y de las grabaciones.