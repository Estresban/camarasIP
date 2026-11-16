import http.client
import json
import re
import threading
import time
import urllib.parse
import cv2

from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

alertas_activas = True
camara_telegram_idx = 0  # Índice de la cámara seleccionada desde Telegram (0 = Cámara 1)

# Teclado táctil completo con selector de cámara, cruceta PTZ y controles
TECLADO_TELEGRAM = {
    "keyboard": [
        [{"text": "📹 Cám 1"}, {"text": "📹 Cám 2"}, {"text": "📹 Cám 3"}, {"text": "📹 Cám 4"}],
        [{"text": "🔍 Zoom -"}, {"text": "⬆️ Arriba"}, {"text": "🔍 Zoom +"}],
        [{"text": "⬅️ Izquierda"}, {"text": "📸 Foto Actual"}, {"text": "➡️ Derecha"}],
        [{"text": "💡 Luz"}, {"text": "⬇️ Abajo"}, {"text": "🎥 Grabar"}],
        [{"text": "📸 Foto 1"}, {"text": "📸 Foto 2"}, {"text": "📸 Foto 3"}, {"text": "📸 Foto 4"}],
        [{"text": "🎥 Grabar 1"}, {"text": "🎥 Grabar 2"}, {"text": "🎥 Grabar 3"}, {"text": "🎥 Grabar 4"}],
        [{"text": "👁️ Detec 1"}, {"text": "👁️ Detec 2"}, {"text": "👁️ Detec 3"}, {"text": "👁️ Detec 4"}],
        [{"text": "💡 Luz 1"}, {"text": "💡 Luz 2"}, {"text": "💡 Luz 3"}, {"text": "💡 Luz 4"}],
        [{"text": "📷 Todas Fotos"}, {"text": "🔔 Alertas ON/OFF"}, {"text": "📊 Estado"}],
    ],
    "resize_keyboard": False,
    "is_persistent": True,
}

# Equivalencia exacta entre cada botón y su comando interno
MAPEO_BOTONES = {
    "📹 cám 1": "/sel1",
    "📹 cám 2": "/sel2",
    "📹 cám 3": "/sel3",
    "📹 cám 4": "/sel4",
    "⬆️ arriba": "/ptz_arriba",
    "⬇️ abajo": "/ptz_abajo",
    "⬅️ izquierda": "/ptz_izquierda",
    "➡️ derecha": "/ptz_derecha",
    "🔍 zoom +": "/zoom_mas",
    "🔍 zoom -": "/zoom_menos",
    "📸 foto actual": "/foto_actual",
    "💡 luz": "/luz_actual",
    "🎥 grabar": "/grabar_actual",
    "📸 foto 1": "/foto1",
    "📸 foto 2": "/foto2",
    "📸 foto 3": "/foto3",
    "📸 foto 4": "/foto4",
    "🎥 grabar 1": "/grabar1",
    "🎥 grabar 2": "/grabar2",
    "🎥 grabar 3": "/grabar3",
    "🎥 grabar 4": "/grabar4",
    "👁️ detec 1": "/deteccion1",
    "👁️ detec 2": "/deteccion2",
    "👁️ detec 3": "/deteccion3",
    "👁️ detec 4": "/deteccion4",
    "💡 luz 1": "/luz1",
    "💡 luz 2": "/luz2",
    "💡 luz 3": "/luz3",
    "💡 luz 4": "/luz4",
    "📷 todas fotos": "/foto",
    "🔔 alertas on/off": "/alertas",
    "📊 estado": "/estado",
}



def alternar_alertas():
    """Activa o desactiva el envío de notificaciones a Telegram."""
    global alertas_activas
    alertas_activas = not alertas_activas
    estado = "ACTIVADAS" if alertas_activas else "DESACTIVADAS"
    print(f"[ALERTA] Notificaciones Telegram {estado}")


def enviar_mensaje_telegram(texto, incluir_teclado=True):
    """Envía un mensaje de texto con la botonera táctil adjunta."""
    token = str(TELEGRAM_TOKEN).strip()
    chat_id = str(TELEGRAM_CHAT_ID).strip()
    if not token or not chat_id:
        return

    try:
        datos = {"chat_id": chat_id, "text": texto}
        if incluir_teclado:
            datos["reply_markup"] = json.dumps(TECLADO_TELEGRAM)

        params = urllib.parse.urlencode(datos)
        conn = http.client.HTTPSConnection("api.telegram.org", timeout=10)
        conn.request("GET", f"/bot{token}/sendMessage?{params}")
        resp = conn.getresponse()
        resp.read()
        conn.close()
    except Exception as exc:
        print(f"[ALERTA] Error enviando texto a Telegram: {exc}")


def _enviar_foto_telegram(imagen_bgr, texto):
    """Envía una fotografía por HTTPS usando http.client."""
    token = str(TELEGRAM_TOKEN).strip()
    chat_id = str(TELEGRAM_CHAT_ID).strip()
    if not token or not chat_id:
        return

    try:
        exito, buffer = cv2.imencode(".jpg", imagen_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not exito:
            return
        datos_jpeg = buffer.tobytes()

        boundary = "----BoundaryAlertaCamara7MA4YWxkTrZu0gW"
        cuerpo = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            f"{chat_id}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="caption"\r\n\r\n'
            f"{texto}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="photo"; filename="alerta.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        ).encode("utf-8") + datos_jpeg + f"\r\n--{boundary}--\r\n".encode("utf-8")

        ruta = f"/bot{token}/sendPhoto"
        cabeceras = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(cuerpo)),
        }

        conn = http.client.HTTPSConnection("api.telegram.org", timeout=10)
        conn.request("POST", ruta, body=cuerpo, headers=cabeceras)
        resp = conn.getresponse()
        resp.read()
        conn.close()
    except Exception as exc:
        print(f"[ALERTA] Error enviando foto a Telegram: {exc}")


def enviar_alerta_movimiento(imagen_bgr, nombre_camara):
    """Lanza la alerta en segundo plano solo si las alertas están activadas."""
    if not alertas_activas:
        return
    copia = imagen_bgr.copy()
    mensaje = f"🚨 Movimiento detectado en: {nombre_camara}"
    threading.Thread(target=_enviar_foto_telegram, args=(copia, mensaje), daemon=True).start()


def _enviar_captura_camara(camara, prefijo="📷"):
    """Extrae el fotograma actual de una cámara y lo envía a Telegram."""
    with camara.lock:
        frame = camara.frame.copy() if getattr(camara, "frame", None) is not None else None
    if frame is not None:
        _enviar_foto_telegram(frame, f"{prefijo} {camara.nombre}")
    else:
        enviar_mensaje_telegram(f"⚠️ {camara.nombre} aún no tiene imagen disponible.")


def _procesar_comando(texto, camaras):
    """Procesa selección de cámara, movimientos PTZ, zoom y controles."""
    global camara_telegram_idx
    entrada = texto.strip().lower()
    cmd = MAPEO_BOTONES.get(entrada, entrada)

    if not camaras:
        enviar_mensaje_telegram("⚠️ No hay cámaras conectadas en el sistema.")
        return

    # Asegurar que el índice seleccionado sigue siendo válido
    if camara_telegram_idx >= len(camaras):
        camara_telegram_idx = 0
    cam_activa = camaras[camara_telegram_idx]

    if cmd in ("/start", "/ayuda", "/help"):
        lista_cams = "\n".join(
            f"  {'👉' if i == camara_telegram_idx else '▫️'} {i + 1}. {c.nombre}"
            for i, c in enumerate(camaras)
        )
        ayuda = (
            "🛡️ CONTROL REMOTO PTZ Y CÁMARAS\n\n"
            f"Cámara activa: *{cam_activa.nombre}*\n"
            f"{lista_cams}\n\n"
            "• Pulsa *Cám 1..4* para elegir qué cámara mover.\n"
            "• Usa la cruceta (*Arriba, Abajo, Izquierda, Derecha*) para girar la cámara y recibir foto al instante."
        )
        enviar_mensaje_telegram(ayuda)
        return

    # 1. Seleccionar cámara activa (/sel1..4)
    match_sel = re.match(r"^/sel(\d+)$", cmd)
    if match_sel:
        idx = int(match_sel.group(1)) - 1
        if 0 <= idx < len(camaras):
            camara_telegram_idx = idx
            cam_activa = camaras[idx]
            _enviar_captura_camara(cam_activa, prefijo=f"✅ Seleccionada [{idx + 1}]")
        else:
            enviar_mensaje_telegram(f"⚠️ La cámara {idx + 1} no existe (hay {len(camaras)}).")
        return

    # 2. Movimiento PTZ sobre la cámara seleccionada (ejes ya corregidos)
    movimientos_ptz = {
        "/ptz_arriba": (0.0, 0.5, 0.0, "⬆️ Arriba"),
        "/ptz_abajo": (0.0, -0.5, 0.0, "⬇️ Abajo"),
        "/ptz_izquierda": (0.5, 0.0, 0.0, "⬅️ Izquierda"),
        "/ptz_derecha": (-0.5, 0.0, 0.0, "➡️ Derecha"),
    }
    if cmd in movimientos_ptz:
        vx, vy, vz, etiqueta = movimientos_ptz[cmd]
        if hasattr(cam_activa, "mover_ptz"):
            cam_activa.mover_ptz(vx, vy, vz)
        
        else:
            enviar_mensaje_telegram(f"⚠️ {cam_activa.nombre} no soporta movimiento PTZ.")
        return

    # 3. Zoom digital sobre la cámara seleccionada
    if cmd in ("/zoom_mas", "/zoom_menos"):
        paso = 0.2 if cmd == "/zoom_mas" else -0.2
        if hasattr(cam_activa, "cambiar_zoom"):
            cam_activa.cambiar_zoom(paso)
            zoom_actual = getattr(cam_activa, "zoom_digital", 1.0)
            _enviar_captura_camara(cam_activa, prefijo=f"🔍 Zoom {zoom_actual:.1f}x |")
        else:
            enviar_mensaje_telegram(f"⚠️ {cam_activa.nombre} no soporta zoom.")
        return

    # 4. Atajos sobre la cámara seleccionada actualmente
    if cmd == "/foto_actual":
        _enviar_captura_camara(cam_activa, prefijo="📸")
        return
    if cmd == "/luz_actual":
        cmd = f"/luz{camara_telegram_idx + 1}"
    elif cmd == "/grabar_actual":
        cmd = f"/grabar{camara_telegram_idx + 1}"

    if cmd == "/estado":
        lineas = [
            f"📊 ESTADO DEL SISTEMA",
            f"• Cámara activa PTZ: [{camara_telegram_idx + 1}] {cam_activa.nombre}",
            f"• Alertas móvil: {'🟢 ON' if alertas_activas else '⚪ OFF'}\n",
        ]
        for i, c in enumerate(camaras):
            grab = "🔴 REC" if getattr(c, "grabando", False) else "⚪ OFF"
            det = "🟢 ON" if getattr(c, "deteccion_activa", False) else "⚪ OFF"
            luz = getattr(c, "modo_luz_actual", "AUTO")
            marca = "👉 " if i == camara_telegram_idx else ""
            lineas.append(f"{marca}{i + 1}. {c.nombre}: Grab {grab} | Det {det} | Luz {luz}")
        enviar_mensaje_telegram("\n".join(lineas))
        return

    if cmd == "/alertas":
        alternar_alertas()
        enviar_mensaje_telegram(f"🔔 Alertas al móvil: {'ACTIVADAS 🟢' if alertas_activas else 'SILENCIADAS ⚪'}.")
        return

    # 5. Comandos individuales o globales (/foto1..4, /grabar1..4, /deteccion1..4, /luz1..4)
    coincidencia = re.match(r"^/(foto|grabar|deteccion|luz)(\d+)?$", cmd)
    if not coincidencia:
        enviar_mensaje_telegram("❓ Comando no reconocido. Pulsa /start para actualizar los botones.")
        return

    accion, num_str = coincidencia.groups()
    if num_str is not None:
        idx = int(num_str) - 1
        if idx < 0 or idx >= len(camaras):
            enviar_mensaje_telegram(f"⚠️ La cámara {num_str} no existe (hay {len(camaras)} cámaras).")
            return
        objetivos = [camaras[idx]]
    else:
        objetivos = camaras

    if accion == "foto":
        for c in objetivos:
            _enviar_captura_camara(c, prefijo="📷")

    elif accion == "grabar":
        respuestas = []
        for c in objetivos:
            if hasattr(c, "alternar_grabacion"):
                c.alternar_grabacion()
                estado = "INICIADA 🔴" if getattr(c, "grabando", False) else "DETENIDA ⏹️"
                respuestas.append(f"🎥 {c.nombre}: Grabación {estado}")
        enviar_mensaje_telegram("\n".join(respuestas))

    elif accion == "deteccion":
        respuestas = []
        for c in objetivos:
            if hasattr(c, "alternar_deteccion"):
                c.alternar_deteccion()
                estado = "ACTIVADA 🟢" if getattr(c, "deteccion_activa", False) else "DESACTIVADA ⚪"
                respuestas.append(f"👁️ {c.nombre}: Detección {estado}")
        enviar_mensaje_telegram("\n".join(respuestas))

    elif accion == "luz":
        ciclo = {"AUTO": "BLANCA", "BLANCA": "IR", "IR": "AUTO"}
        nombres_bonitos = {
            "BLANCA": "Luz BLANCA ☀️",
            "IR": "Infrarrojos (IR) 🌙",
            "AUTO": "Luz AUTOMÁTICA 🔄",
        }
        respuestas = []
        for c in objetivos:
            if hasattr(c, "cambiar_luz_led"):
                actual = str(getattr(c, "modo_luz_actual", "AUTO")).upper()
                if actual not in ciclo:
                    actual = "AUTO"
                siguiente = ciclo[actual]
                c.cambiar_luz_led(siguiente)
                respuestas.append(f"💡 {c.nombre}: {nombres_bonitos[siguiente]}")
            else:
                respuestas.append(f"⚠️ {c.nombre}: No soporta control de luz.")
        enviar_mensaje_telegram("\n".join(respuestas))


def iniciar_bot_comandos(camaras):
    """Hilo en segundo plano que escucha botones y comandos de Telegram."""
    token = str(TELEGRAM_TOKEN).strip()
    chat_autorizado = str(TELEGRAM_CHAT_ID).strip()
    if not token or not chat_autorizado:
        return

    def bucle_escucha():
        ultimo_update_id = 0
        print("[TELEGRAM] Bot PTZ con teclado táctil escuchando órdenes...")
        while True:
            try:
                ruta = f"/bot{token}/getUpdates?offset={ultimo_update_id + 1}&timeout=20"
                conn = http.client.HTTPSConnection("api.telegram.org", timeout=25)
                conn.request("GET", ruta)
                resp = conn.getresponse()
                datos = json.loads(resp.read().decode("utf-8", errors="ignore"))
                conn.close()
                if datos.get("ok"):
                    for update in datos.get("result", []):
                        ultimo_update_id = update["update_id"]
                        msg = update.get("message", {})
                        remitente_id = str(msg.get("chat", {}).get("id", ""))
                        texto = msg.get("text", "")
                        if remitente_id == chat_autorizado and texto:
                            _procesar_comando(texto, camaras)
            except Exception:
                time.sleep(3)

    threading.Thread(target=bucle_escucha, daemon=True).start()
