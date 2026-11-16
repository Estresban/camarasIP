'''from dvrip import DVRIPCam

# Conecta al puerto nativo 34567 de la cámara del garaje
cam = DVRIPCam("x.x.x.x", user="xxxx", password="xxxx")

if cam.login():
    print("¡Conectado al puerto 34567 de la cámara del garaje!")
    
    # Activa el servicio ONVIF en el puerto 8899
    cam.set_info("NetWork.Onvif", {"Enable": True, "Port": 8899})
    
    # Activa el servicio RTSP en el puerto 554
    cam.set_info("NetWork.RTSP", {"Enable": True, "Port": 554})
    
    print("Servicios ONVIF y RTSP activados. Reiniciando cámara...")
    cam.reboot()
    cam.close()
else:
    print("Error de inicio de sesión en el puerto 34567. Verifica la contraseña.")
    
'''
###########################################################
###########################################################
# PRUEBA 1   Comprobacion de puertos 
###########################################################
###########################################################


from dvrip import DVRIPCam

# Prueba con tu contraseña o déjala vacía ("") si no tiene clave
cam = DVRIPCam("192.168.1.23", user="xxx", password="xxx")

if cam.login():
    print("Conexión exitosa al puerto 34567.")
    print("Configuración ONVIF actual:", cam.get_info("NetWork.Onvif"))
    print("Configuración RTSP actual:", cam.get_info("NetWork.RTSP"))
    cam.close()
else:
    print("No se pudo iniciar sesión. Revisa el usuario y la contraseña.")

import socket

ip = "192.168.1.2"
for puerto in (554, 8899, 80, 34567):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    abierto = s.connect_ex((ip, puerto)) == 0
    print(f"Puerto {puerto}: {'ABIERTO' if abierto else 'CERRADO'}")
    s.close()