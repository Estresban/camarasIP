"""Módulo Watchdog para detectar flujos de cámara caídos o congelados y reconectarlos."""
import threading
import time
import numpy as np


class WatchdogCamaras:
    """Supervisa todas las cámaras en segundo plano y fuerza su reconexión si se cuelgan."""

    def __init__(self, camaras, timeout_seg=8.0, intervalo_revision=3.0):
        self.camaras = camaras
        self.timeout_seg = timeout_seg
        self.intervalo_revision = intervalo_revision
        self.detener = False
        self._estado = {}  # indice -> {"firma": int, "ultimo_cambio": float, "reiniciando": bool}

    def iniciar(self):
        threading.Thread(target=self._bucle_vigilancia, daemon=True).start()
        print(f"[WATCHDOG] Supervisión activa (timeout: {self.timeout_seg}s)")

    def cerrar(self):
        self.detener = True

    def _firma_rapida(self, frame):
        """Calcula una huella ligera del fotograma para detectar si la imagen está congelada."""
        if frame is None:
            return None
        # Muestreamos 1 de cada 32 píxeles para consumir casi 0% de CPU
        muestra = frame[::32, ::32]
        return int(np.sum(muestra, dtype=np.uint64))

    def _bucle_vigilancia(self):
        # Damos 10 segundos de cortesía inicial mientras conectan al arrancar
        time.sleep(10)

        while not self.detener:
            ahora = time.time()

            for idx, cam in enumerate(self.camaras):
                if getattr(cam, "detener", False):
                    continue

                frame_actual = None
                lock = getattr(cam, "lock", None)
                if lock:
                    with lock:
                        if getattr(cam, "frame", None) is not None:
                            frame_actual = cam.frame
                else:
                    frame_actual = getattr(cam, "frame", None)

                firma = self._firma_rapida(frame_actual)
                info = self._estado.setdefault(
                    idx, {"firma": firma, "ultimo_cambio": ahora, "reiniciando": False}
                )

                # Si la firma cambió (y hay imagen válida), la cámara está viva
                if firma is not None and firma != info["firma"]:
                    info["firma"] = firma
                    info["ultimo_cambio"] = ahora
                    info["reiniciando"] = False
                    continue

                # Si lleva más de timeout_seg sin imagen nueva o con el mismo frame congelado
                tiempo_parada = ahora - info["ultimo_cambio"]
                if tiempo_parada >= self.timeout_seg and not info["reiniciando"]:
                    info["reiniciando"] = True
                    info["ultimo_cambio"] = ahora
                    print(f"[WATCHDOG] ⚠️ {cam.nombre} congelada o sin señal ({tiempo_parada:.1f}s). Reconectando...")

                    if hasattr(cam, "forzar_reconexion"):
                        threading.Thread(target=cam.forzar_reconexion, daemon=True).start()

            time.sleep(self.intervalo_revision)
