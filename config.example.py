import hashlib
import json
import os
import sys
import numpy as np


def obtener_ruta_base():
    """Devuelve la carpeta real donde está el .exe (si está compilado) o el script .py."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


RUTA_BASE = obtener_ruta_base()
DIR_DATOS = os.path.join(RUTA_BASE, "camarasIP")
RUTA_CONFIG_JSON = os.path.join(RUTA_BASE, "config.json")

# ==============================================================================
# PLANTILLA DE CONFIGURACIÓN DE CÁMARAS (Renombrar este archivo a config.py)
# ==============================================================================

CONFIG_CAMARAS_RTSP = [
    {
        "nombre": "Camara 1",
        "ip": "192.168.1.101",
        "usuario": "admin",
        "password": "TU_PASSWORD",
        "puerto_rtsp": 554,
        "puerto_onvif": 8899,
        "puerto_netip": 34567,
        "canal": 1,
        "stream": 0,
    },
    {
        "nombre": "Camara 2",
        "ip": "192.168.1.102",
        "usuario": "admin",
        "password": "TU_PASSWORD",
        "puerto_rtsp": 554,
        "puerto_onvif": 8899,
        "puerto_netip": 34567,
        "canal": 1,
        "stream": 0,
    },
    {
        "nombre": "Camara 3",
        "ip": "192.168.1.103",
        "usuario": "admin",
        "password": "TU_PASSWORD",
        "puerto_rtsp": 554,
        "puerto_onvif": 8899,
        "puerto_netip": 34567,
        "canal": 1,
        "stream": 0,
    },
]

CONFIG_PATIO = {
    "nombre": "Camara 4",
    "ip": "192.168.1.104",
    "usuario": "admin",
    "password": "TU_PASSWORD",
    "puerto_netip": 34567,
    "canales": (0, 1),
}

ANCHO_CELDA = 640
ALTO_CELDA = 360
ALTO_LENTE_DVRIP = ALTO_CELDA // 2
ANCHO_TOTAL_BASE = ANCHO_CELDA * 2
ALTO_TOTAL_BASE = ALTO_CELDA * 2

DISPOSITIVO_SALIDA_AUDIO = 3
TELEGRAM_TOKEN = "TU_TOKEN_TELEGRAM"
TELEGRAM_CHAT_ID = "TU_CHAT_ID"

MINUTOS_POR_BLOQUE_VIDEO = 10
SENSIBILIDAD_MOVIMIENTO = 1200
COOLDOWN_CAPTURA_SEG = 5
INTERVALO_FOTOGRAMA_AUTO_SEG = 10

_nombre_grabaciones = "grabaciones"
_nombre_movimiento = "capturas_movimiento"
_nombre_fotogramas = "capturas_fotogramas"

if os.path.exists(RUTA_CONFIG_JSON):
    try:
        with open(RUTA_CONFIG_JSON, "r", encoding="utf-8") as _f:
            _guardados = json.load(_f)
        if isinstance(_guardados, dict):
            CONFIG_CAMARAS_RTSP = _guardados.get("camaras_rtsp", CONFIG_CAMARAS_RTSP)
            if "patio" in _guardados:
                CONFIG_PATIO = _guardados["patio"]
                if "canales" in CONFIG_PATIO:
                    CONFIG_PATIO["canales"] = tuple(CONFIG_PATIO["canales"])
            _params = _guardados.get("parametros", {})
            MINUTOS_POR_BLOQUE_VIDEO = _params.get("minutos_por_bloque_video", MINUTOS_POR_BLOQUE_VIDEO)
            SENSIBILIDAD_MOVIMIENTO = _params.get("sensibilidad_movimiento", SENSIBILIDAD_MOVIMIENTO)
            COOLDOWN_CAPTURA_SEG = _params.get("cooldown_captura_seg", COOLDOWN_CAPTURA_SEG)
            INTERVALO_FOTOGRAMA_AUTO_SEG = _params.get("intervalo_fotograma_auto_seg", INTERVALO_FOTOGRAMA_AUTO_SEG)
            DISPOSITIVO_SALIDA_AUDIO = _guardados.get("dispositivo_salida_audio", DISPOSITIVO_SALIDA_AUDIO)
            TELEGRAM_TOKEN = _guardados.get("telegram_token", TELEGRAM_TOKEN)
            TELEGRAM_CHAT_ID = _guardados.get("telegram_chat_id", TELEGRAM_CHAT_ID)
            _carpetas = _guardados.get("carpetas", {})
            _nombre_grabaciones = _carpetas.get("grabaciones") or _nombre_grabaciones
            _nombre_movimiento = _carpetas.get("capturas_movimiento") or _nombre_movimiento
            _nombre_fotogramas = _carpetas.get("capturas_fotogramas") or _nombre_fotogramas
    except (OSError, json.JSONDecodeError):
        pass


def _resolver_carpeta(nombre_o_ruta):
    if os.path.isabs(nombre_o_ruta):
        return nombre_o_ruta
    return os.path.join(DIR_DATOS, nombre_o_ruta)


CARPETA_GRABACIONES = _resolver_carpeta(_nombre_grabaciones)
CARPETA_CAPTURAS = _resolver_carpeta(_nombre_movimiento)
CARPETA_MOVIMIENTO = CARPETA_CAPTURAS
CARPETA_FOTOGRAMAS = _resolver_carpeta(_nombre_fotogramas)

CARPETAS_SALIDA = (CARPETA_GRABACIONES, CARPETA_CAPTURAS, CARPETA_FOTOGRAMAS)
for carpeta in CARPETAS_SALIDA:
    os.makedirs(carpeta, exist_ok=True)


def hash_xmeye(password):
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    res = ""
    md5_bytes = hashlib.md5(password.encode()).digest()
    for i in range(0, 16, 2):
        val = (md5_bytes[i] + md5_bytes[i + 1]) % 62
        res += chars[val]
    return res


def alaw_a_pcm(datos):
    datos = np.frombuffer(datos, dtype=np.uint8) ^ 0x55
    valor = ((datos & 0x0F).astype(np.int16) << 4) + 8
    segmento = (datos & 0x70) >> 4
    valor += np.where(segmento >= 1, 0x100, 0)
    valor = np.where(segmento > 1, valor << (segmento - 1), valor)
    return np.where((datos & 0x80) != 0, valor, -valor).astype(np.int16)


def pcm16_a_alaw(samples_int16):
    pcm = np.clip(samples_int16.astype(np.int32), -32768, 32767)
    sign = np.where(pcm >= 0, 0x80, 0x00)
    pcm = np.where(pcm < 0, -pcm - 1, pcm)
    exp = np.zeros_like(pcm)
    for bit in range(1, 8):
        cond = pcm >= (256 << (bit - 1))
        exp = np.where(cond, bit, exp)
    mantissa = np.where(exp == 0, (pcm >> 4) & 0x0F, (pcm >> (exp + 3)) & 0x0F)
    alaw = (sign | (exp << 4) | mantissa) ^ 0x55
    return alaw.astype(np.uint8).tobytes()
