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

print("Notificacion de Error de autenticacion:")
print(host, ip, varbind)