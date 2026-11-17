"""Módulo independiente para grabación por movimiento con pre-buffer circular."""
from collections import deque
from datetime import datetime
import time
import cv2

from config import ANCHO_CELDA, ALTO_CELDA
from notificaciones import enviar_video_evento
from correo_alertas import enviar_video_correo

class GrabadorEventos:
    """Gestiona un búfer circular en RAM y guarda clips ante detección de movimiento."""

    def __init__(self, nombre_camara, seg_prebuffer=5, seg_postevento=15, fps=20.0):
        self.nombre = nombre_camara
        self.fps = fps
        self.seg_postevento = seg_postevento
        self.activa = False
        self.grabando_ahora = False

        # Búfer circular en memoria (5 seg * 20 fps = 100 fotogramas)
        self.prebuffer = deque(maxlen=int(seg_prebuffer * fps))
        self.writer = None
        self.ruta_actual = None
        self.fin_grabacion = 0

    def alternar(self):
        """Activa o desactiva el modo de espera con pre-buffer."""
        self.activa = not self.activa
        if not self.activa:
            self.detener_y_limpiar()
        estado = "ACTIVADA" if self.activa else "DESACTIVADA"
        print(f"[{self.nombre}] Grabación por movimiento (Pre-buffer): {estado}")
        return self.activa

    def procesar_frame(self, frame, hay_movimiento):
        """Debe llamarse en cada fotograma recibido por la cámara."""
        if not self.activa:
            return

        ahora = time.time()

        # Si detecta movimiento, inicia el clip volcando el pre-buffer o prolonga 15s
        if hay_movimiento:
            self.fin_grabacion = ahora + self.seg_postevento
            if self.writer is None:
                fecha_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                self.ruta_actual = f"grabaciones/EVENTO_{self.nombre.replace(' ', '_')}_{fecha_str}.mp4"
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                self.writer = cv2.VideoWriter(self.ruta_actual, fourcc, self.fps, (ANCHO_CELDA, ALTO_CELDA))

                for f_previo in self.prebuffer:
                    self.writer.write(f_previo)
                self.prebuffer.clear()

                self.grabando_ahora = True
                print(f"[{self.nombre}] Grabando clip con pre-buffer -> {self.ruta_actual}")

        # Escritura activa del clip o almacenamiento en el búfer circular
        if self.writer is not None:
            if ahora <= self.fin_grabacion:
                self.writer.write(frame)
            else:
                self.writer.release()
                self.writer = None
                self.grabando_ahora = False
                print(f"[{self.nombre}] Clip de evento finalizado: {self.ruta_actual}")
                if self.ruta_actual:
                    enviar_video_evento(self.ruta_actual, self.nombre)
                    enviar_video_correo(self.ruta_actual, self.nombre)
                    self.ruta_actual = None
        else:
            self.prebuffer.append(frame.copy())

    def detener_y_limpiar(self):
        """Libera el archivo de vídeo y vacía la RAM de forma segura."""
        self.prebuffer.clear()
        self.grabando_ahora = False
        if self.writer is not None:
            self.writer.release()
            self.writer = None
            self.ruta_actual = None
