"""Ventana independiente para editar la configuración del sistema."""
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import sys

from config import (
    RUTA_BASE, DIR_DATOS,
    CONFIG_CAMARAS_RTSP, CONFIG_PATIO, MINUTOS_POR_BLOQUE_VIDEO,
    SENSIBILIDAD_MOVIMIENTO, COOLDOWN_CAPTURA_SEG,
    INTERVALO_FOTOGRAMA_AUTO_SEG, DISPOSITIVO_SALIDA_AUDIO,
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID,
    EMAIL_ACTIVO, EMAIL_REMITENTE, EMAIL_PASSWORD,
    EMAIL_DESTINATARIO, EMAIL_SMTP_SERVIDOR, EMAIL_SMTP_PUERTO,
    EMAIL_INTERVALO_ALERTAS, EMAIL_ADJUNTAR_FOTO,
)

ARCHIVO_CONFIG = os.path.join(RUTA_BASE, "config.json")
ARCHIVO_HISTORIAL = os.path.join(DIR_DATOS, "historial.txt")


def leer_guardados():
    try:
        with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as archivo:
            datos = json.load(archivo)
            return datos if isinstance(datos, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def iniciar():
    guardados = leer_guardados()
    camaras_guardadas = guardados.get("camaras_rtsp", CONFIG_CAMARAS_RTSP)
    patio_guardado = guardados.get("patio", CONFIG_PATIO)

    root = tk.Tk()
    root.title("Configuración - Videovigilancia")
    root.geometry("720x650")
    root.minsize(650, 560)
    root.configure(bg="#202832")

    estilo = ttk.Style(root)
    try:
        estilo.theme_use("clam")
    except tk.TclError:
        pass
    estilo.configure("TFrame", background="#202832")
    estilo.configure("TLabel", background="#202832", foreground="#f1f4f8")
    estilo.configure("TButton", padding=7)
    estilo.configure("TNotebook", background="#202832")
    estilo.configure("TNotebook.Tab", padding=(12, 7))

    encabezado = ttk.Label(root, text="CONFIGURACIÓN DEL SISTEMA",
                           font=("Segoe UI", 16, "bold"))
    encabezado.pack(anchor="w", padx=18, pady=(16, 4))
    ttk.Label(root, text="Los cambios de conexión se aplicarán al reiniciar el programa.",
              foreground="#b9c5d3").pack(anchor="w", padx=18, pady=(0, 12))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=16, pady=6)

    tab_camaras = ttk.Frame(notebook, padding=12)
    tab_grabacion = ttk.Frame(notebook, padding=16)
    tab_general = ttk.Frame(notebook, padding=16)
    tab_correo = ttk.Frame(notebook, padding=16)
    tab_historial = ttk.Frame(notebook, padding=16)
    notebook.add(tab_historial, text="Historial")
    notebook.add(tab_camaras, text="Cámaras")
    notebook.add(tab_grabacion, text="Grabación y detección")
    notebook.add(tab_general, text="General")
    notebook.add(tab_correo, text="Correo electrónico")

    campos_camaras = []

    def campo(parent, etiqueta, valor, ocultar=False, ancho=34):
        fila = ttk.Frame(parent)
        fila.pack(fill="x", pady=3)
        ttk.Label(fila, text=etiqueta, width=18).pack(side="left")
        entrada = ttk.Entry(fila, width=ancho, show="*" if ocultar else "")
        entrada.pack(side="left", fill="x", expand=True)
        entrada.insert(0, str(valor))
        return entrada

    # Desplazamiento vertical para que quepan todas las cámaras.
    lienzo = tk.Canvas(tab_camaras, bg="#202832", highlightthickness=0)
    barra = ttk.Scrollbar(tab_camaras, orient="vertical", command=lienzo.yview)
    contenido = ttk.Frame(lienzo, padding=(4, 4, 12, 4))
    contenido.bind("<Configure>", lambda _e: lienzo.configure(scrollregion=lienzo.bbox("all")))
    lienzo.create_window((0, 0), window=contenido, anchor="nw")
    lienzo.configure(yscrollcommand=barra.set)
    lienzo.pack(side="left", fill="both", expand=True)
    barra.pack(side="right", fill="y")

    for i, cfg in enumerate(camaras_guardadas):
        grupo = ttk.LabelFrame(contenido, text=f"Cámara RTSP {i + 1}", padding=9)
        grupo.pack(fill="x", pady=6)
        entradas = {}
        for clave, etiqueta, secreto in (
            ("nombre", "Nombre", False), ("ip", "Dirección IP", False),
            ("usuario", "Usuario", False), ("password", "Contraseña", True),
            ("puerto_rtsp", "Puerto RTSP", False), ("puerto_onvif", "Puerto ONVIF", False),
            ("puerto_netip", "Puerto NetIP", False), ("canal", "Canal", False),
            ("stream", "Stream", False),
        ):
            entradas[clave] = campo(grupo, etiqueta, cfg.get(clave, ""), secreto)
        campos_camaras.append(entradas)

    grupo_patio = ttk.LabelFrame(contenido, text="Cámara DVRIP - Patio", padding=9)
    grupo_patio.pack(fill="x", pady=6)
    entradas_patio = {}
    for clave, etiqueta, secreto in (
        ("nombre", "Nombre", False), ("ip", "Dirección IP", False),
        ("usuario", "Usuario", False), ("password", "Contraseña", True),
        ("puerto_netip", "Puerto NetIP", False),
    ):
        entradas_patio[clave] = campo(grupo_patio, etiqueta, patio_guardado.get(clave, ""), secreto)

    canales = campo(grupo_patio, "Canales (separados por coma)",
                    ",".join(map(str, patio_guardado.get("canales", (0, 1)))))

    # Parámetros de grabación y detección.
    valores_grab = guardados.get("parametros", {})
    entradas_grab = {}
    for clave, etiqueta, defecto in (
        ("minutos_por_bloque_video", "Minutos por vídeo", valores_grab.get("minutos_por_bloque_video", MINUTOS_POR_BLOQUE_VIDEO)),
        ("sensibilidad_movimiento", "Sensibilidad movimiento", valores_grab.get("sensibilidad_movimiento", SENSIBILIDAD_MOVIMIENTO)),
        ("cooldown_captura_seg", "Espera entre capturas (s)", valores_grab.get("cooldown_captura_seg", COOLDOWN_CAPTURA_SEG)),
        ("intervalo_fotograma_auto_seg", "Intervalo captura auto (s)", valores_grab.get("intervalo_fotograma_auto_seg", INTERVALO_FOTOGRAMA_AUTO_SEG)),
    ):
        entradas_grab[clave] = campo(tab_grabacion, etiqueta, defecto)

    carpetas_actuales = guardados.get("carpetas", {})
    entradas_carpetas = {}
    for clave, etiqueta, defecto in (
        ("grabaciones", "Carpeta de vídeos", "grabaciones"),
        ("capturas_movimiento", "Capturas movimiento", "capturas_movimiento"),
        ("capturas_fotogramas", "Fotogramas", "capturas_fotogramas"),
    ):
        entradas_carpetas[clave] = campo(tab_grabacion, etiqueta, carpetas_actuales.get(clave, defecto), ancho=38)

    audio_guardado = guardados.get("dispositivo_salida_audio", DISPOSITIVO_SALIDA_AUDIO)
    entrada_audio = campo(tab_general, "Dispositivo salida audio", audio_guardado)
    token_guardado = guardados.get("telegram_token", TELEGRAM_TOKEN)
    chat_guardado = guardados.get("telegram_chat_id", TELEGRAM_CHAT_ID)
    entrada_token = campo(tab_general, "Token Bot Telegram", token_guardado, ocultar=True, ancho=38)
    entrada_chat = campo(tab_general, "Chat ID Telegram", chat_guardado, ancho=38)

    ttk.Label(tab_general, text="Los cambios se guardan en config.json y se cargan al iniciar la aplicación.",
              foreground="#b9c5d3", wraplength=560).pack(anchor="w", pady=(14, 4))

    # --- PESTAÑA: CORREO ELECTRÓNICO ---
    email_guardado = guardados.get("email", {})

    var_email_activo = tk.BooleanVar(value=email_guardado.get("activo", EMAIL_ACTIVO))
    var_email_adjuntar = tk.BooleanVar(value=email_guardado.get("adjuntar_foto", EMAIL_ADJUNTAR_FOTO))

    fila_checks = ttk.Frame(tab_correo)
    fila_checks.pack(fill="x", pady=(4, 10))
    ttk.Checkbutton(fila_checks, text="Activar alertas por correo electrónico",
                    variable=var_email_activo).pack(side="left", padx=(0, 20))
    ttk.Checkbutton(fila_checks, text="Adjuntar captura JPEG",
                    variable=var_email_adjuntar).pack(side="left")
    
    entrada_email_rem = campo(tab_correo, "Correo remitente",
                              email_guardado.get("remitente", EMAIL_REMITENTE), ancho=38)
    entrada_email_pass = campo(tab_correo, "Contraseña aplicación",
                               email_guardado.get("password", EMAIL_PASSWORD), ocultar=True, ancho=38)
    entrada_email_dest = campo(tab_correo, "Correo destinatario",
                               email_guardado.get("destinatario", EMAIL_DESTINATARIO), ancho=38)
    entrada_email_smtp = campo(tab_correo, "Servidor SMTP",
                               email_guardado.get("smtp_servidor", EMAIL_SMTP_SERVIDOR), ancho=38)
    entrada_email_puerto = campo(tab_correo, "Puerto SMTP (SSL)",
                                 email_guardado.get("smtp_puerto", EMAIL_SMTP_PUERTO), ancho=38)
    entrada_email_interv = campo(tab_correo, "Espera entre correos (s)",
                                 email_guardado.get("intervalo_alertas", EMAIL_INTERVALO_ALERTAS), ancho=38)

    ttk.Label(
        tab_correo,
        text="Nota: Si usas Gmail, debes generar una 'Contraseña de aplicación' de 16 letras en tu cuenta de Google.",
        foreground="#b9c5d3",
        wraplength=580
    ).pack(anchor="w", pady=(14, 4))

    # --- PESTAÑA: HISTORIAL DE DETECCIONES ---
    barra_top_hist = ttk.Frame(tab_historial)
    barra_top_hist.pack(fill="x", pady=(0, 8))
    ttk.Label(barra_top_hist, text="Registro de detecciones (más recientes arriba):",
              font=("Segoe UI", 10, "bold")).pack(side="left")

    # Empaquetamos primero los botones inferiores para que nunca queden desplazados
    fila_btns_hist = ttk.Frame(tab_historial)
    fila_btns_hist.pack(side="bottom", fill="x", pady=(8, 0))

    marco_texto = ttk.Frame(tab_historial)
    marco_texto.pack(fill="both", expand=True)

    scroll_hist = ttk.Scrollbar(marco_texto, orient="vertical")
    scroll_hist.pack(side="right", fill="y")

    caja_historial = tk.Text(
        marco_texto,
        height=14,
        wrap="word",
        bg="#161c23",
        fg="#f1f4f8",
        font=("Consolas", 10),
        relief="flat",
        padx=10,
        pady=10,
        yscrollcommand=scroll_hist.set,
        state="disabled",
    )
    caja_historial.pack(side="left", fill="both", expand=True)
    scroll_hist.config(command=caja_historial.yview)

    def cargar_historial():
        caja_historial.config(state="normal")
        caja_historial.delete("1.0", tk.END)
        try:
            if os.path.exists(ARCHIVO_HISTORIAL):
                with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
                    lineas = [l.strip() for l in f if l.strip()]
                if lineas:
                    caja_historial.insert(tk.END, "\n".join(reversed(lineas)))
                else:
                    caja_historial.insert(tk.END, "El historial está vacío.")
            else:
                caja_historial.insert(tk.END, "Aún no se ha registrado ninguna detección.")
        except OSError as exc:
            caja_historial.insert(tk.END, f"Error leyendo historial.txt: {exc}")
        caja_historial.config(state="disabled")

    def limpiar_historial():
        if not messagebox.askyesno("Borrar historial", "¿Seguro que quieres vaciar todo el historial de detecciones?", parent=root):
            return
        try:
            with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
                f.write("")
            cargar_historial()
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=root)

    def abrir_carpeta_capturas():
        nombre_carpeta = entradas_carpetas["capturas_movimiento"].get().strip() or "capturas_movimiento"
        ruta_carpeta = os.path.join(DIR_DATOS, nombre_carpeta)
        os.makedirs(ruta_carpeta, exist_ok=True)
        try:
            if sys.platform.startswith("win"):
                os.startfile(ruta_carpeta)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", ruta_carpeta])
            else:
                subprocess.Popen(["xdg-open", ruta_carpeta])
        except OSError as exc:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{exc}", parent=root)

    fila_btns_hist = ttk.Frame(tab_historial)
    fila_btns_hist.pack(fill="x", pady=(8, 0))
    ttk.Button(fila_btns_hist, text="Actualizar", command=cargar_historial).pack(side="left")
    ttk.Button(fila_btns_hist, text="Abrir carpeta de capturas", command=abrir_carpeta_capturas).pack(side="left", padx=(8, 0))
    ttk.Button(fila_btns_hist, text="Borrar historial", command=limpiar_historial).pack(side="right")

    cargar_historial()


    def entero(entrada, nombre):
        try:
            return int(entrada.get().strip())
        except ValueError:
            raise ValueError(f"El campo '{nombre}' debe ser un número entero.")

    def guardar():
        try:
            lista_camaras = []
            for i, entradas in enumerate(campos_camaras):
                original = dict(camaras_guardadas[i])
                for clave, entrada in entradas.items():
                    original[clave] = entrada.get().strip()
                for clave in ("puerto_rtsp", "puerto_onvif", "puerto_netip", "canal", "stream"):
                    original[clave] = entero(entradas[clave], clave)
                lista_camaras.append(original)

            patio = dict(patio_guardado)
            for clave, entrada in entradas_patio.items():
                patio[clave] = entrada.get().strip()
            patio["puerto_netip"] = entero(entradas_patio["puerto_netip"], "Puerto NetIP patio")
            try:
                patio["canales"] = tuple(int(x.strip()) for x in canales.get().split(",") if x.strip())
            except ValueError:
                raise ValueError("Los canales del Patio deben ser números separados por comas.")
            if not patio["canales"]:
                raise ValueError("Debe indicarse al menos un canal para el Patio.")

            parametros = {k: entero(v, k) for k, v in entradas_grab.items()}
            dispositivo = entero(entrada_audio, "Dispositivo salida audio")

            datos_email = {
                "activo": bool(var_email_activo.get()),
                "adjuntar_foto": bool(var_email_adjuntar.get()),
                "remitente": entrada_email_rem.get().strip(),
                "password": entrada_email_pass.get().strip(),
                "destinatario": entrada_email_dest.get().strip(),
                "smtp_servidor": entrada_email_smtp.get().strip(),
                "smtp_puerto": entero(entrada_email_puerto, "Puerto SMTP (SSL)"),
                "intervalo_alertas": entero(entrada_email_interv, "Espera entre correos (s)"),
            }

            datos = {
                "camaras_rtsp": lista_camaras,
                "patio": patio,
                "parametros": parametros,
                "carpetas": {k: v.get().strip() for k, v in entradas_carpetas.items()},
                "dispositivo_salida_audio": dispositivo,
                "telegram_token": entrada_token.get().strip(),
                "telegram_chat_id": entrada_chat.get().strip(),
                "email": datos_email,
            }
            
            with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as archivo:
                json.dump(datos, archivo, ensure_ascii=False, indent=4)
            messagebox.showinfo("Configuración guardada",
                                "Los cambios se han guardado. Reinicia la videovigilancia para aplicarlos.",
                                parent=root)
        except (ValueError, OSError) as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=root)

    def restaurar():
        if not messagebox.askyesno("Restaurar", "¿Quieres descartar los cambios guardados y volver a los valores de config.py?", parent=root):
            return
        try:
            if os.path.exists(ARCHIVO_CONFIG):
                os.remove(ARCHIVO_CONFIG)
            messagebox.showinfo("Restaurado", "Se han eliminado los ajustes personalizados. Reinicia la aplicación.", parent=root)
            root.destroy()
        except OSError as exc:
            messagebox.showerror("Error", str(exc), parent=root)

    pie = ttk.Frame(root, padding=(16, 10))
    pie.pack(fill="x")
    ttk.Button(pie, text="Restaurar valores", command=restaurar).pack(side="left")
    ttk.Button(pie, text="Cancelar", command=root.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(pie, text="Guardar", command=guardar).pack(side="right")
    root.mainloop()


if __name__ == "__main__":
    iniciar()
