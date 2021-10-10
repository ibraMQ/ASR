from io import open
from os import remove
from os import rename
from pysnmp.hlapi import *
import rrdtool
import time
import sys
import os.path
import threading
from reportlab.pdfgen import canvas
from p2f import *
  
#Variable fijas
s_disp=True
int_disp=0
filename="devs.txt"
fileproc="proc_id.txt"
threads = list()

#funcion hilo de monitoreo
def worker(procs,nlist):
    params=getParams(int(nlist))
    #recopilacion de datos para calculo de linea base
    tperiod=60*60*2#2hrs
    nameB="bd"+str(nlist)+"p"
    start_time = time.time()
    pMem=0
    tMem=0
    lin=True
    rams=[0]
    rends=[[0]]
    for x in range(1,len(procs)):
        rends.append([0])
    blockSize=0
    opsis=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.1.1.0',params[3],1)#info del stemas operativosi
    if "Windows" in opsis:
        lin=False
        blockSize=int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.2.3.1.4.2.0',params[3],1))
        tMem=int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.2.3.1.5.2.0',params[3],1))
    else:
        tMem=int(consultaSNMP(params[2],params[0],'1.3.6.1.4.1.2021.4.5.0',params[3],0))
    while 1:
        for x in range(1,len(procs)):
            carga_CPU = int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.3.3.1.2.'+procs[x],params[3],0))
            valor = "N:" + str(carga_CPU)
            rrdtool.update(nameB+str(x)+'.rrd', valor)
            rrdtool.dump(nameB+str(x)+'.rrd',nameB+str(x)+'.xml')
            rends[x].append(carga_CPU)
        if lin == True:
            #Conculta Ram linux
            useMem=consultaSNMP(params[2],params[0],'1.3.6.1.4.1.2021.4.6.0',params[3],0)
            pMem=int(useMem)*100/int(tMem)
            rams.append(pMem)
        else:
            #Conculta Ram windows
            useMem=int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.2.3.1.6.2.0',params[3],1))
            pMem=int(useMem)*100/int(tMem)
            rams.append(pMem)
        valor = "N:" + str(int(pMem))
        rrdtool.update("ramd"+str(nlist)+".rrd", valor)
        rrdtool.dump("ramd"+str(nlist)+".rrd","ramd"+str(nlist)+".xml")
        time.sleep(0.99)
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time > tperiod:
            print("Recopilacion Finalizada")
            break
    #analisis de datos de base para determinal umbrales
    #print(rams)
    #print(rends)
    umbralsP=[]
    umbralRam=50
    aux=0
    auxC=0
    for x in rams:
        if x > 5.0:
            aux+=x
            auxC+=1
    umbralRam=aux/auxC
    aux=0
    auxC=0
    for x in range(1,len(procs)):
        for y in rends[x]:
            if y > 5:
                aux+=y
                auxC+=1
        umbralsP.append(aux/auxC)
        aux=0
        auxC=0
    print(umbralRam)
    print(umbralsP)
    #Monitoreo del dispositivo
    print("----------\nEmpezando Monitoreo del dispositivo "+str(nlist)+"\n------------")
    #Bases para el monitoreo
    tstep=60
    tperiod=1440
    ret=rrdtool.create("ramd"+str(nlist)+"m.rrd",
                        "--start",'N',
                        "--step",str(tstep),
                        "DS:ramp:GAUGE:"+str(tperiod)+":U:U",
                        "RRA:AVERAGE:0.5:1:24")
    for x in range(1,len(procs)):
        ret = rrdtool.create(nameB+str(x)+"m.rrd",
                            "--start",'N',
                            "--step",str(tstep),
                            "DS:cap:GAUGE:"+str(tperiod)+":U:U",
                            "RRA:AVERAGE:0.5:1:24")
    #Monitoreo de umbrales
    sisOp=""
    if lin == True:
        sisOp="Linux"
    else:
        sisOp="Windows"
    wTime=60*3
    lAlarm=time.time()
    while 1:
        timeN=time.thread_time()
        current_time = time.time()
        elapsed_time = current_time - lAlarm
        for x in range(1,len(procs)):
            carga_CPU = int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.3.3.1.2.'+procs[x],params[3],0))
            valor = "N:" + str(carga_CPU)
            rrdtool.update(nameB+str(x)+'m.rrd', valor)
            rrdtool.dump(nameB+str(x)+'m.rrd',nameB+str(x)+'m.xml')
            print(carga_CPU)#-------------------------------
            if carga_CPU > umbralsP[x-1]:
                if elapsed_time > wTime:
                    #Envio de alerta
                    print("Carga alta en Procesador")
                    time.sleep(20)
                    start_time=time.time()-3*60
                    ret1 = rrdtool.graph( "deteccion.png",
                        "--start",str(int(start_time)),
                        "--end","N",
                        "--vertical-label=Carga de trabajo (%)",
                        '--lower-limit', '0',
                        '--upper-limit', '100',
                        "--title=Carga alta en procesador",
                        "DEF:cap="+nameB+str(x)+"m.rrd"+":cap:AVERAGE",
                        "CDEF:umbral=cap,0,*,"+str(umbralsP[x-1])+",+",
                        "AREA:cap#00FF00",
                        "LINE3:umbral#0000FF")
                    body="Maquina: "+params[0]+" Sistema Operativo: "+sisOp+"\nCARGA DE TRABAJO EN PROCESADOR ALTA\nValor Maximo Permitido: "+str(umbralsP[x-1])+"\nValor Registrado: "+str(carga_CPU)
                    send_alert_attached("Carga alta en Procesador del Dispositivo "+str(nlist),body)
                    lAlarm=time.time()
        if lin == True:
            #Conculta Ram linux
            useMem=consultaSNMP(params[2],params[0],'1.3.6.1.4.1.2021.4.6.0',params[3],0)
            pMem=int(useMem)*100/int(tMem)
            print(pMem)#--------------------------------------
        else:
            #Conculta Ram windows
            useMem=int(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.2.3.1.6.2.0',params[3],1))
            pMem=int(useMem)*100/int(tMem)
        valor = "N:" + str(int(pMem))
        rrdtool.update("ramd"+str(nlist)+"m.rrd", valor)
        rrdtool.dump("ramd"+str(nlist)+"m.rrd","ramd"+str(nlist)+"m.xml")
        if pMem > umbralRam:
            if elapsed_time > wTime:
                #Envio de alerta
                print("Carga alta de RAM")
                time.sleep(10)
                start_time=time.time()-3*60
                ret1 = rrdtool.graph( "deteccion.png",
                        "--start",str(int(start_time)),
                        "--end","N",
                        "--vertical-label=Carga de trabajo (%)",
                        '--lower-limit', '0',
                        '--upper-limit', '100',
                        "--title=Carga alta en procesador",
                        "DEF:ramp="+"ramd"+str(nlist)+"m.rrd"+":ramp:AVERAGE",
                        "CDEF:umbral=ramp,0,*,"+str(umbralRam)+",+",
                        "AREA:ramp#00FF00",
                        "LINE3:umbral#0000FF")
                body="Maquina: "+params[0]+" Sistema Operativo: "+sisOp+"\nCARGA DE TRABAJO EN RAM ALTA\nValor Maximo Permitido: "+str(umbralRam)+"\nValor Registrado: "+str(pMem)
                send_alert_attached("Carga alta en RAM del Dispositivo "+str(nlist),body)
                lAlarm=time.time()
        print(elapsed_time)#-------------------------------
        print("-------")
        time.sleep(20)
    return

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
            sistime=bytes(consultaSNMP(params[2],params[0],'1.3.6.1.2.1.25.1.2.0',params[3],0),"utf-8")
        print("--")
    f.close()
    
    #Menu de inicio
    print(".")
    print("1.Agregar Dispositivo\n2.Eliminar Dispositivo\n3.Reporte de Informacion de Dispositivo\n4.Interfaces de red\n5.Determinar umbral de trabajo\n6.SALIR")
    op=int(input())
    print('')

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
        rename("new.txt",filename)
        #Variables para nombres de archivos a eliminar
        nameRep="Dispositivo"+str(nel)+".pdf"
        nameG1="d1"+str(nel)+".png"
        nameG2="d2"+str(nel)+".png"
        nameG3="d3"+str(nel)+".png"
        nameG4="d4"+str(nel)+".png"
        nameG5="d5"+str(nel)+".png"
        nameBase="d"+str(nel)+".rrd"
        nameBasex="d"+str(nel)+".xml"
        #eLIMINAR GRAFICAS Y REPORTE
        if os.path.isfile(nameRep):
            remove(nameRep)
        if os.path.isfile(nameBase):
            remove(nameBase)
        if os.path.isfile(nameBasex):
            remove(nameBasex)
        if os.path.isfile(nameG1):
            remove(nameG1)
        if os.path.isfile(nameG2):
            remove(nameG2)
        if os.path.isfile(nameG3):
            remove(nameG3)
        if os.path.isfile(nameG4):
            remove(nameG4)
        if os.path.isfile(nameG5):
            remove(nameG5)

    #Generar reporte
    elif op == 3:
        #Obtencion  de datos de usuario
        print("Ingrese el numero en lista del dispositivo a monitorear")
        nlist=int(input())
        print("Ingrese el numero de interfaz a monitorear")
        nint=int(input())
        print("Ingrese el numero de segundos monitorear")
        tperiod=int(input())
        #Variables para nombres de archivos
        nameRep="Dispositivo"+str(nlist)+".pdf"
        nameG1="d1"+str(nlist)+".png"
        nameG2="d2"+str(nlist)+".png"
        nameG3="d3"+str(nlist)+".png"
        nameG4="d4"+str(nlist)+".png"
        nameG5="d5"+str(nlist)+".png"
        nameBase="d"+str(nlist)+".rrd"
        nameBasex="d"+str(nlist)+".xml"
        #obtencion datos dispositivo
        f=open(filename,"r")
        i=1
        straux=""
        for line in f:
            if i == nlist:
                straux=line
            i=i+1
        f.close()
        params=getParam(straux)
        #creacion de base de datos rrd
        tstep=int(tperiod/20)
        ret = rrdtool.create(nameBase,
                            "--start",'N',
                            "--step",str(tstep),
                            "DS:unicast:COUNTER:"+str(tperiod)+":U:U",
                            "DS:ipv:COUNTER:"+str(tperiod)+":U:U",
                            "DS:icmp:COUNTER:"+str(tperiod)+":U:U",
                            "DS:segment:COUNTER:"+str(tperiod)+":U:U",
                            "DS:datagram:COUNTER:"+str(tperiod)+":U:U",
                            "RRA:AVERAGE:0.5:1:20",
                            "RRA:AVERAGE:0.5:1:20",
                            "RRA:AVERAGE:0.5:1:20",
                            "RRA:AVERAGE:0.5:1:20",
                            "RRA:AVERAGE:0.5:1:20")
        if ret:
            print (rrdtool.error())
        #Poblacion de la base
        else:
            rrdtool.dump(nameBase,nameBasex)
            start_time = time.time()
            while 1:
                rCon1=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.2.2.1.11.'+str(nint),params[3],0)#Paquetes unicas de una interfas??
                rCon2=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.4.3.0',params[3],0)#todos recividos ipv4//
                rCon3=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.5.21.0',params[3],0)#icmp echoes enviados???+22
                rCon4=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.6.10.0',params[3],0)#todos segmentos recividos//
                rCon5=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.7.1.0',params[3],0)#datagrams entregados por udp//
                valor = "N:" + str(rCon1) + ':' + str(rCon2)+ ':' + str(rCon3)+ ':' + str(rCon4)+ ':' + str(rCon5)
                #print (valor)
                rrdtool.update(nameBase, valor)
                rrdtool.dump(nameBase,nameBasex)
                time.sleep(0.99)
                current_time = time.time()
                elapsed_time = current_time - start_time
                if elapsed_time > tperiod:
                    break
            #Graficacion
            ret1 = rrdtool.graph( nameG1,
                     "--start",str(int(start_time)),
                     "--end","N",
                     "--vertical-label=Paquetes/s",
                     "--title=Paquetes Unicast\nRecividos",
                     "DEF:unicast="+nameBase+":unicast:AVERAGE",
                     "AREA:unicast#00FF00")
            ret2 = rrdtool.graph( nameG2,
                     "--start",str(int(start_time)),
                     "--end","N",
                     "--vertical-label=Paquetes/s",
                     "--title=Todos los Paquetes IPv4\nRecividos",
                     "DEF:ipv="+nameBase+":ipv:AVERAGE",
                     "LINE3:ipv#0000FF")
            ret3 = rrdtool.graph( nameG3,
                     "--start",str(int(start_time)),
                     "--end","N",
                     "--vertical-label=Mensajes/s",
                     "--title=Mensajes ICMP Echoes\nEnviados",
                     "DEF:icmp="+nameBase+":icmp:AVERAGE",
                     "AREA:icmp#00FF00")
            ret4 = rrdtool.graph( nameG4,
                     "--start",str(int(start_time)),
                     "--end","N",
                     "--vertical-label=Segmentos/s",
                     "--title=Todos los Segmentos\nRecividos",
                     "DEF:segment="+nameBase+":segment:AVERAGE",
                     "LINE3:segment#0000FF")
            ret5 = rrdtool.graph( nameG5,
                     "--start",str(int(start_time)),
                     "--end","N",
                     "--vertical-label=Datagramas/s",
                     "--title=Datagramas Entregados a\nUsuarios UDP",
                     "DEF:datagram="+nameBase+":datagram:AVERAGE",
                     "AREA:datagram#00FF00")
            #Datos reporte
            opsis=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.1.1.0',params[3],1)#info del stemas operativosi
            logo=""
            if "Windows" in opsis:
                logo="win.png"
            else:
                logo="linux.jpg"
            uptime=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.1.3.0',params[3],0)#tiempo activo del sistema
            comunidad=params[2]
            dirr=params[0]
            location=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.1.6.0',params[3],0)#ubicacion geografica
            ports=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.2.1.0',params[3],0)#puertos interfaes??
            #generar reporte
            psize=(596,1210)
            c = canvas.Canvas(nameRep,psize)
            if logo=="win.png":
                c.drawImage(logo, 20, 1150, width=50, height=50)
                text1 = c.beginText(80,1200)
            else:
                c.drawImage(logo, 50, 1150, width=120, height=50)
                text1 = c.beginText(150,1200)
            paso=int(len(opsis)/4)
            iin=0
            isu=paso
            filas=""
            for x in range(1,5):
                filas+=opsis[iin:isu]+"\n"
                iin=isu
                isu=iin+paso
                if x == 4:
                    isu=len(opsis)-1
            text1.textLines("Informacion del sistema:\n"+filas)
            c.drawText(text1)
            text = c.beginText(20, 1105)
            text.textLine("Ubicacion: "+location)
            text.textLine("Numero de interfaces: "+ports+"   Tiempo de actividad: "+uptime)
            text.textLine("Comunidad: "+comunidad+"   "+"IP: "+dirr)
            c.drawText(text)#1080
            c.drawImage(nameG1, 20, 870, width=500, height=200)
            c.drawImage(nameG2, 20, 660, width=500, height=200)
            c.drawImage(nameG3, 20, 450, width=500, height=200)
            c.drawImage(nameG4, 20, 240, width=500, height=200)
            c.drawImage(nameG5, 20, 20, width=500, height=200)
            c.save()
            
    #interfaces info
    elif op==4:
        print("Ingrese el numero en lista del dispositivo del que desea visualizar las interfaces de red")
        nlist=int(input())
        f=open(filename,"r")
        i=1
        straux=""
        for line in f:
            if i == nlist:
                straux=line
                break
            i=i+1
        f.close()
        params=getParam(straux)
        print(params)
        rCon=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.2.1.0',params[3],0)
        for x in range(1,int(rCon)):
            adstate=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.2.2.1.7.'+str(x),params[3],0)
            desc=consultaSNMP(params[2],params[0],'1.3.6.1.2.1.2.2.1.2.'+str(x),params[3],0)
            ndesc=desc[2:]
            if desc != "Error":
                 bytes_object = bytes.fromhex(ndesc)
                 ascii_string = bytes_object.decode("ASCII")
                 print(str(x)+":Estado administrativo:"+adstate+":=Descripcion:"+ascii_string)

    #terminar ejecuccion
    elif op == 6:
        break

    #UMBRAL determinacion
    elif op==5:
        print("Ingrese el numero en lista del dispositivo del que desea calcular el umbral de trabajo")
        nlist=int(input())
        params=getParams(nlist)
        print(params)
        #obtener ids de nucleos
        f=open(fileproc,"r")
        i=1
        straux=""
        ver=False
        for line in f:
            lparam=line.split(",")
            if lparam[0] == params[0]:
                pids=lparam
                ver=True
                pids[len(pids)-1][1:]
                print(pids)
        f.close()
        if ver == False:
            print("Ingrese los id's de los procesadores a monitorear")
            carid=input()
            pids=carid.split(",")
            print(pids)
            f=open(fileproc,"a")
            f.write(params[0]+","+carid+"\n")
            f.close()
        #creacion de base para supervicion
        nameB="bd"+str(nlist)+"p"
        tperiod=60*60*2#2hrs
        tstep=60
        ret=rrdtool.create("ramd"+str(nlist)+".rrd",
                            "--start",'N',
                            "--step",str(tstep),
                            "DS:ramp:GAUGE:"+str(tperiod)+":U:U",
                            "RRA:AVERAGE:0.5:1:120")
        for x in range(1,len(pids)+1):
            ret = rrdtool.create(nameB+str(x)+".rrd",
                                "--start",'N',
                                "--step",str(tstep),
                                "DS:cap:GAUGE:"+str(tperiod)+":U:U",
                                "RRA:AVERAGE:0.5:1:120")
        #creacion de hilo de vigilancia y recopilacion de datos
        t = threading.Thread(target=worker(pids,nlist))
        t.start()

    #pruebas
    elif op == 9:
        useMem=consultaSNMP("comunity","localhost",'1.3.6.1.4.1.2021.4.5.0',"161",0)
        tMem=consultaSNMP("comunity","localhost",'1.3.6.1.4.1.2021.4.4.0',"161",0)
        print(tMem+"::::"+useMem)
        #sacar ram windows(2 conver memoria id 2) y linux(conver a porcentaje solo)
