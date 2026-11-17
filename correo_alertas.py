
import os
import time
import json
import smtplib
import threading
import cv2

from datetime import datetime
from email.message import EmailMessage

from config import (
    EMAIL_ACTIVO,
    EMAIL_REMITENTE,
    EMAIL_PASSWORD,
    EMAIL_DESTINATARIO,
    EMAIL_SMTP_SERVIDOR,
    EMAIL_SMTP_PUERTO,
    EMAIL_INTERVALO_ALERTAS,
    EMAIL_ADJUNTAR_FOTO,
)

email_alertas_activas = EMAIL_ACTIVO

# Último envío realizado para cada cámara
_ultimos_envios = {}
_lock_correo = threading.Lock()

def alternar_alertas_correo():
    """Activa o desactiva el envío de alertas por correo en tiempo real."""
    global email_alertas_activas
    email_alertas_activas = not email_alertas_activas
    estado = "ACTIVADAS" if email_alertas_activas else "DESACTIVADAS"
    print(f"[EMAIL] Alertas por correo {estado}")
    
    
def enviar_correo_evento(camara, evento, imagen=None):
    """
    Envía un correo con los datos del evento y una fotografía opcional.
    """

    if not email_alertas_activas:
        return False

    try:
        ahora = datetime.now()
        nombre = getattr(camara, "nombre", "Cámara desconocida")

        asunto = f"ALERTA CCTV - {nombre}"

        mensaje = EmailMessage()
        mensaje["Subject"] = asunto
        mensaje["From"] = EMAIL_REMITENTE
        mensaje["To"] = EMAIL_DESTINATARIO

        cuerpo = (
            "Se ha recibido un evento de videovigilancia.\n\n"
            f"Cámara: {nombre}\n"
            f"Fecha: {ahora.strftime('%d/%m/%Y')}\n"
            f"Hora: {ahora.strftime('%H:%M:%S')}\n\n"
            f"Evento recibido:\n{evento}\n"
        )

        mensaje.set_content(cuerpo)

        # Adjuntar fotografía JPEG
        if EMAIL_ADJUNTAR_FOTO and imagen is not None:
            exito, buffer = cv2.imencode(
                ".jpg",
                imagen,
                [int(cv2.IMWRITE_JPEG_QUALITY), 85]
            )

            if exito:
                mensaje.add_attachment(
                    buffer.tobytes(),
                    maintype="image",
                    subtype="jpeg",
                    filename=f"{nombre}_{ahora:%Y%m%d_%H%M%S}.jpg"
                )

        # Envío SMTP seguro
        with smtplib.SMTP_SSL(
            EMAIL_SMTP_SERVIDOR,
            EMAIL_SMTP_PUERTO,
            timeout=20
        ) as servidor:

            servidor.login(
                EMAIL_REMITENTE,
                EMAIL_PASSWORD
            )

            servidor.send_message(mensaje)

        print(f"[EMAIL] Alerta enviada: {nombre}")
        return True

    except Exception as exc:
        print(f"[EMAIL] Error enviando correo: {exc}")
        return False


def procesar_evento_correo(camara, datos_evento, numero_secuencia):
    """
    Callback que recibe las alarmas DVRIP de cada cámara.
    """

    nombre = getattr(camara, "nombre", "Cámara desconocida")

    # Limitar frecuencia de correos por cámara
    ahora = time.time()

    with _lock_correo:
        ultimo = _ultimos_envios.get(nombre, 0)

        if ahora - ultimo < EMAIL_INTERVALO_ALERTAS:
            return

        _ultimos_envios[nombre] = ahora

    # Registrar el evento recibido para conocer su estructura
    try:
        evento_texto = json.dumps(
            datos_evento,
            ensure_ascii=False,
            default=str
        )
    except Exception:
        evento_texto = str(datos_evento)

    print(f"[EVENTO DVRIP] {nombre}: {evento_texto}")

    # Obtener la última imagen disponible
    imagen = None

    if EMAIL_ADJUNTAR_FOTO:
        try:
            with camara.lock:
                if getattr(camara, "frame", None) is not None:
                    imagen = camara.frame.copy()
        except Exception as exc:
            print(f"[EMAIL] No se pudo obtener imagen: {exc}")

    # Enviar en segundo plano para no bloquear la recepción de alarmas
    threading.Thread(
        target=enviar_correo_evento,
        args=(camara, evento_texto, imagen),
        daemon=True
    ).start()


def crear_callback_correo(camara):
    """
    Crea un callback independiente para cada cámara.
    """

    def callback(datos_evento, numero_secuencia):
        procesar_evento_correo(
            camara,
            datos_evento,
            numero_secuencia
        )

    return callback

def enviar_alerta_correo_rtsp(nombre_camara, imagen):
    """
    Envía alerta por correo desde las cámaras RTSP respetando el intervalo configurado.
    """
    if not email_alertas_activas:
        return

    ahora = time.time()
    with _lock_correo:
        ultimo = _ultimos_envios.get(nombre_camara, 0)
        if ahora - ultimo < EMAIL_INTERVALO_ALERTAS:
            return
        _ultimos_envios[nombre_camara] = ahora

    # Creamos un objeto ligero con el atributo 'nombre' que espera enviar_correo_evento
    camara_info = type("CamaraRTSP", (), {"nombre": nombre_camara})()
    copia_imagen = imagen.copy() if (EMAIL_ADJUNTAR_FOTO and imagen is not None) else None

    threading.Thread(
        target=enviar_correo_evento,
        args=(camara_info, "Detección de movimiento (RTSP)", copia_imagen),
        daemon=True
    ).start()
    
def _enviar_video_correo_hilo(ruta_video, nombre_camara):
    """Envía el archivo .mp4 adjunto por SMTP en segundo plano."""
    try:
        ahora = datetime.now()
        mensaje = EmailMessage()
        mensaje["Subject"] = f"VÍDEO ALERTA CCTV - {nombre_camara}"
        mensaje["From"] = EMAIL_REMITENTE
        mensaje["To"] = EMAIL_DESTINATARIO

        cuerpo = (
            "Se ha grabado un clip de vídeo tras detectar movimiento.\n\n"
            f"Cámara: {nombre_camara}\n"
            f"Fecha: {ahora.strftime('%d/%m/%Y')}\n"
            f"Hora: {ahora.strftime('%H:%M:%S')}\n"
        )
        mensaje.set_content(cuerpo)

        with open(ruta_video, "rb") as f:
            datos_mp4 = f.read()

        nombre_archivo = os.path.basename(ruta_video)
        mensaje.add_attachment(
            datos_mp4,
            maintype="video",
            subtype="mp4",
            filename=nombre_archivo
        )

        with smtplib.SMTP_SSL(EMAIL_SMTP_SERVIDOR, EMAIL_SMTP_PUERTO, timeout=30) as servidor:
            servidor.login(EMAIL_REMITENTE, EMAIL_PASSWORD)
            servidor.send_message(mensaje)

        print(f"[EMAIL] Clip de vídeo enviado: {ruta_video}")
    except Exception as exc:
        print(f"[EMAIL] Error enviando vídeo por correo: {exc}")


def enviar_video_correo(ruta_video, nombre_camara):
    """Lanza el envío del clip .mp4 por correo si las alertas de email están activas."""
    if not email_alertas_activas:
        return
    threading.Thread(
        target=_enviar_video_correo_hilo,
        args=(ruta_video, nombre_camara),
        daemon=True
    ).start()
