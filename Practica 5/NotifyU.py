import sys

host = input()
ip = input()
varbind = []
while 1:
    try:
        varbind.append(input())
    except EOFError:
        print("Fin de lectura")
        break

print("Notificacion de linkUp (Conexion Levantada):")
print(host, ip, varbind)