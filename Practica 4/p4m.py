from io import open
from os import remove
from os import rename
from telnetlib import Telnet
from ftplib import FTP
from pysnmp.hlapi import *
from reportlab.pdfgen import canvas
from p4f import *
import threading
import rrdtool
import time
import sys
import os.path
  
#Variable fijas
devsfile="devs.txt"
routersfile="routers.txt"
monTime=120     #Periodo por factura
pacLim=100    #Limite de paquetes por periodo
stdCost=10      #Precio a pagar normal
exFactor=0.1    #Tarifa a aplicar por octeto encima del limite

while 1:
    #Informacion de los dispositivos registradis
    print("//////////////////////////////////////////////")
    #Menu de inicio
    print(".")
    print("1.Agregar Dispositivo\n2.Eliminar Dispositivo\n3.Inventario\n4.Generar archivo de configuracion\n5.Extraer archivo de Configuracion\n6.Subir archivo de configuracion\n9.SALIR")
    op=int(input())

    #Salir
    if op==9:
        break

    #Escribir nuevo dispositivo
    if op == 1:
        print("¿Que es el dispositivo?\n1.Router\n2.PC")
        rot=int(input())
        #Agregar PC
        if rot != 1:
            print("Ingrese el nombre de host o Dirreccion IP:")
            host=input()
            print("Ingrese la version de SNMP:")
            ver=input()
            print("Ingrese el nombre de la comunidad:")
            com=input()
            print("Ingrese el puerto de conexión:")
            port=input()
            f=open(devsfile,'a')
            f.write(host+","+ver+","+com+","+port+"\n")
            f.close()
        #Agregar router
        else:
            print("Ingrese la Dirreccion IP:")
            host=input()
            print("Nombre de usuario para operaciones:")
            usr=input()
            print("Contraseña de usuario:")
            psw=input()
            f=open(routersfile,'a')
            f.write(host+","+usr+","+psw+"\n")
            f.close()

    #Eliminar dispositivo del archivo
    elif op == 2:
        print("¿Que es el dispositivo?\n1.Router\n2.PC")
        rot=int(input())
        print("Ingrese el numero en lista del dispositivo a Eliminar")
        nel=int(input())
        #eliminar de archivo de texto creando uno nuevo borrando la linea y renombrando
        filename=devsfile
        if rot == 1:
            filename=routersfile
        f=open(filename,"r")
        fn=open("new.txt","w")
        i=1
        for line in f:
            if i != nel:
                fn.write(line)
            i=i+1
        fn.close()
        f.close()
        remove(filename)
        rename("new.txt",filename)

    #Mostrar y generar archivo de inventario
    elif op == 3:
        print("DISPOSITIVOS:")
        printFile(devsfile)
        print("ROUTERS:")
        printFile(routersfile)
        makeInv()
        print("Archivo de inventario Invent.xlsx generado")

    #Generar archiuvo CONF
    elif op == 4:
        #Obtencion de datos router
        nlist=int(input("Ingrese el numero de lista del router:"))
        params=getParamsR(nlist)
        params[2] =str(params[2]).rstrip("\n")
        #login telnet
        tn = Telnet(params[0])
        tn.read_until(b"User: ")
        cmd = params[1] + '\n\r'
        tn.write(cmd.encode('ascii'))
        tn.read_until(b"Password: ")
        cmd = params[2] + '\n\r'
        tn.write(cmd.encode('ascii'))
        #comandos telnet
        cmd = "en" + '\n\r'
        tn.write(cmd.encode('ascii'))
        cmd = "copy running-config startup-config" + '\n\r'
        tn.write(cmd.encode('ascii'))
        tn.write(b"exit\n")
        print("Archivo startup-config generado")
        
    #Extraer archivo CONF
    elif op == 5:
        #Obtencion de datos router
        nlist=int(input("Ingrese el numero de lista del router:"))
        params=getParamsR(nlist)
        params[2] =str(params[2]).rstrip("\n")
        #login FTP
        ftp = FTP(params[0], params[1], params[2])
        ftp.retrlines("LIST")
        fr="startup-config"
        with open(fr, 'wb') as f:
            ftp.retrbinary('RETR ' + fr, f.write)
        ftp.quit()
        rename(fr,"cR"+str(nlist))
        print("Archivo de configuracion almacenado en cR"+str(nlist))
        
    #Subir archivo de CONF
    elif op == 6:
        #Obtencion de datos router
        nlist=int(input("Ingrese el numero de lista del router destino:"))
        params=getParamsR(nlist)
        params[2] =str(params[2]).rstrip("\n")
        arC=input("Ingrese el nombre del archivo a subir:")
        #Subida mediante frp
        ftp = FTP(params[0], params[1], params[2])
        fileC = open(str(arC),'rb')
        ftp.storbinary('STOR '+str(arC), fileC)
        fileC.close()
        ftp.quit()
        #configuracion mediante telnet
        tn = Telnet(params[0])
        tn.read_until(b"User: ")
        cmd = params[1] + '\n\r'
        tn.write(cmd.encode('ascii'))
        tn.read_until(b"Password: ")
        cmd = params[2] + '\n\r'
        tn.write(cmd.encode('ascii'))
        cmd = "en" + '\n\r'
        tn.write(cmd.encode('ascii'))
        cmd = "copy "+str(arC)+" startup-config" + '\n\r'
        tn.write(cmd.encode('ascii'))
        tn.write(b"exit\n")
        print("Archivo definido como configuracion incial")
