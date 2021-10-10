from io import open
from os import remove
from os import rename
from pysnmp.hlapi import *
import rrdtool
import time
import sys
import os.path
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

COMMASPACE = ', '
fname = 'trend.rrd'
filename="devs.txt"
mailsender = "ibrahimqv99@gmail.com"
mailreceip = "tanibet.escom@gmail.com"
mailserver = 'smtp.gmail.com: 587'
password = 'a'#Contraseña

#Funcion envio de correo
def send_alert_attached(subject,cuerpo):
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = mailsender
    msg['To'] = mailreceip
    body = MIMEText(cuerpo)
    msg.attach(body)
    fp = open('deteccion.png', 'rb')
    img = MIMEImage(fp.read())
    fp.close()
    msg.attach(img)
    s = smtplib.SMTP(mailserver)
    s.starttls()
    # Login Credentials for sending the mail
    s.login(mailsender, password)
    s.sendmail(mailsender, mailreceip, msg.as_string())
    s.quit()

#funcion de consulta
def consultaSNMP(comunidad,host,oid,port,full):
    todo=0
    errorIndication, errorStatus, errorIndex, varBinds = next(
        getCmd(SnmpEngine(),
               CommunityData(comunidad),
               UdpTransportTarget((host, int(port))),
               ContextData(),
               ObjectType(ObjectIdentity(oid))))

    if errorIndication:
        print(errorIndication)
        return "Fallo"
    elif errorStatus:
        print('%s at %s' % (errorStatus.prettyPrint(),errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
        return "Error"
    else:
        for varBind in varBinds:
            varB=(' = '.join([x.prettyPrint() for x in varBind]))
            resultado= varB.split()[2]
        if full == 1:
            todo=1
    if todo == 1:
        aux=""
        for varBind in varBinds:
            print(' = '.join([x.prettyPrint() for x in varBind]))
            aux+=' = '.join([x.prettyPrint() for x in varBind])+"\n"
            return aux
    return resultado

#funcion de parametros para linea de texto
def getParam(line):
    i=0
    data1=""
    data2=""
    data3=""
    data4=""
    data5=""
    for car in str(line):
        if i==0:
            if car != ",":
                data1+=car
            else:
                i+=1
        elif i==1:
            if car != ",":
                data2+=car
            else:
                i+=1
        elif i==2:
            if car != ",":
                data3+=car
            else:
                i+=1
        elif i==3:
            if car != "," and car!='\n':
                data4+=car
            else:
                i+=1
        elif i==4:
            if car != "," and car!='\n':
                data5+=car
            else:
                i+=1
    return [data1,data2,data3,data4,data5]
    
#Funcion parametros del archivo
def getParams(n):
    f=open(filename,"r")
    i=1
    straux=""
    for line in f:
        if i == n:
            straux=line
        i=i+1
    f.close()
    params=getParam(straux)
    return params

#Funcion snmp walk
def walk(host, oid,comunidad):
    for (errorIndication,
     errorStatus,
     errorIndex,
     varBinds) in nextCmd(SnmpEngine(), 
                          CommunityData(comunidad),
                          UdpTransportTarget((host, 161)),
                          ContextData(),                                                           
                          ObjectType(ObjectIdentity(oid)),
                          lexicographicMode=False):
        if errorIndication:
            print(errorIndication, file=sys.stderr)
            break
        elif errorStatus:
            print('%s at %s' % (errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'), 
                                file=sys.stderr)             
            break
        else:
            for varBind in varBinds:
                print(varBind)
                print("q")
