from io import open
from os import remove
from os import rename
import threading
from pysnmp.hlapi import *
import rrdtool
import time
import sys
import os.path
from reportlab.pdfgen import canvas
from p3f import *
import xlsxwriter
  
#Variable fijas
filename="devs.txt"
monTime=120     #Periodo por factura
pacLim=100    #Limite de paquetes por periodo
stdCost=10      #Precio a pagar normal
exFactor=0.1    #Tarifa a aplicar por octeto encima del limite
threads = list()

while 1:
    #Informacion de los dispositivos registradis
    print("//////////////////////////////////////////////")
    i=0
    f=open(filename,"r")
    for line in f:
        i+=1
    f.close()
    print("Numero de dispositivos monitoreados: "+str(i))
    print("--") 
    f=open(filename,"r")
    for line in f:
        #Obtencion de variables de la info
        params=getParam(line)#------Params:dirrecion,version,comunidad,puerto
        print(params)
        #Consulta para comprobar conexion
        rCon=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.1.1.0',params[3],1)
        if str(rCon) == "Fallo" or str(rCon) == "Error":
            print("Dispositivo sin Conexion")
        else:
            print("Dispositivo Conectado")
            rCon=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.2.1.0',params[3],0)
            print("Numero de interfaces: "+rCon)
            uptime=int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.1.1.0',params[3],0))/6000
            print("Tiempo de actividad del sistema (min): "+str(uptime))
        print("--")
    f.close()
    makeInv()
    
    #Menu de inicio
    print(".")
    print("1.Agregar Dispositivo\n2.Eliminar Dispositivo\n3.Ajustar cobro de tarifa\n4.Monitorear Dispositivo\n9.SALIR")
    op=int(input())
    print('')

    #Salir
    if op==9:
        break

    #Escribir nuevo dispositivo
    if op == 1:
        print("Ingrese el nombre de host o Dirreccion IP:")
        host=input()
        print("Ingrese la version de SNMP:")
        ver=input()
        print("Ingrese el nombre de la comunidad:")
        com=input()
        print("Ingrese el puerto de conexión:")
        port=input()
        #apend en el archivo
        f=open(filename,'a')
        f.write(host+","+ver+","+com+","+port+","+"0"+"\n")
        f.close()

    #Eliminar dispositivo del archivo
    elif op == 2:
        print("Ingrese el numero en lista del dispositivo a Eliminar")
        nel=int(input())
        
        #eliminar de archivo de texto creando uno nuevo borrando la linea y renombrando
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
        nameBase="d"+str(nel)+".rrd"
        rename("new.txt",filename)
        if os.path.isfile(nameBase):
            remove(nameBase)

    #Cambio de tarifa
    elif op == 3:
        print("Ingrese el la duracion de los plazos para el cobro:")
        monTime=int(input())     #Periodo por factura
        print("Ingrese el numero de paquetes IPV4 a recibir por periodo:")
        pacLim=int(input())    #Limite de paquetes por periodo
        print("Ingrese el costo base del servicio (MXN):")
        stdCost=int(input())      #Precio a pagar normal
        print("Ingrese el precio a aplicar por paquete que sobrepase el plan (MXN):")
        exFactor=float(input()) 

    #Monitoreo de variablle
    elif op == 4:
        #Obtencion  de datos de usuario
        print("Ingrese el numero en lista del dispositivo a monitorear")
        nlist=int(input())
        nameBase="d"+str(nlist)+".rrd"
        nameBasex="d"+str(nlist)+".xml"
        #obtencion datos dispositivo
        params=getParams(nlist)
        print("Empezando el monitoreo")
        #creacion de base rrd
        tstep=int(monTime/20)
        ret = rrdtool.create(nameBase,
                            "--start",'N',
                            "--step",str(tstep),
                            "DS:ipv:COUNTER:"+str(monTime)+":U:U",
                            "RRA:AVERAGE:0.5:1:20")
        #loop de monitoreo
        while 1:
            iniVal=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.4.3.0',params[3],0)
            elapsed_time = 0
            start_time = time.time()
            while 1:
                time.sleep(tstep-1)
                totPac=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.4.3.0',params[3],0)#Paquetes ipv4 recividos
                valor = "N:" + str(totPac)
                #print (valor)
                rrdtool.update(nameBase, valor)
                rrdtool.dump(nameBase,nameBasex)
                current_time = time.time()
                elapsed_time = current_time - start_time
                if elapsed_time > monTime:
                    break
            #generar reporte
            conPaq=int(totPac)-int(iniVal)
            exPaq=conPaq-pacLim
            payment=stdCost
            if exPaq > 0 :
                payment+=exPaq*exFactor
            nameG="GraficaD"+str(nlist)+".png"
            ret1 = rrdtool.graph( nameG,
                     "--start",str(int(start_time)),
                     "--end","N",
                     "--vertical-label=Paquetes",
                     "--title=Consumo de IPV4",
                     "DEF:ipv="+nameBase+":ipv:AVERAGE",
                     "AREA:ipv#00FF00")
            #print("paquetes consumidos: "+str(conPaq
            psize=(596,380)
            nameRep="ReporteD"+str(nlist)+".pdf"
            c = canvas.Canvas(nameRep,psize)
            text = c.beginText(20, 360)
            text.textLine("Reporte de Gastos por servicio de IPv4")
            text.textLine("Dirreccion del cliente: " +params[0])
            text.textLine("Numero de paquetes de los que dispone su plan: " +str(pacLim))
            text.textLine("Numero de paquetes consumidos en este periodo: " +str(conPaq))
            text.textLine("Tarifa a aplica por paquete extra utilizado: " +str(exFactor))
            text.textLine("Total a Pagar: $" +str(payment)+" MXN")
            c.drawText(text)
            c.drawImage(nameG, 20, 20, width=400, height=150)
            c.save()
            print("Reporte generado")
