from io import open
from os import remove
from os import rename
from pysnmp.hlapi import *
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
import os.path
import smtplib
import xlsxwriter

COMMASPACE = ', '
fname = 'trend.rrd'
filename="devs.txt"
routersfile="routers.txt"
mailsender = "ibrahimqv99@gmail.com"
mailreceip = "ibrahimqv@live.com.mx"
mailserver = 'smtp.gmail.com: 587'
password = 'i123581321Q.'
xfile="Invent.xlsx"

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

#Funcion parametros del archivo
def getParams(n):
    f=open(filename,"r")
    i=1
    straux=""
    for line in f:
        if i == n:
            straux=line
            break
        i=i+1
    f.close()
    params=straux.split(",")
    return params

#Funcion parametros del router
def getParamsR(n):
    f=open(routersfile,"r")
    i=1
    straux=""
    for line in f:
        if i == n:
            straux=line
            break
        i=i+1
    f.close()
    params=straux.split(",")
    return params

#Creacion de archivo xlsx de inventario
def makeInv():
    workbook = xlsxwriter.Workbook(xfile)
    worksheet = workbook.add_worksheet()
    worksheet.write(0, 0,"Host")
    worksheet.write(0, 1,"SNMP")
    worksheet.write(0, 2,"Comunidad")
    worksheet.write(0, 3,"Puerto")
    x=1
    f=open(filename,"r")
    for line in f:
        params=line.split(",")
        params[3] =str(params[3]).rstrip("\n")
        worksheet.write(x, 0,params[0])
        worksheet.write(x, 1,params[1])
        worksheet.write(x, 2,params[2])
        worksheet.write(x, 3,str(params[3])+".")
        x+=1
    f.close()
    if os.path.isfile(routersfile):
        worksheet.write(0, 5,"IP")
        worksheet.write(0, 6,"Usuario")
        worksheet.write(0, 7,"Contraseña")
        x=1
        f=open(routersfile,"r")
        for line in f:
            params=line.split(",")
            params[2] =str(params[2]).rstrip("\n")
            worksheet.write(x, 5,params[0])
            worksheet.write(x, 6,params[1])
            worksheet.write(x, 7,params[2])
            x+=1
        f.close()
    workbook.close()

def printFile(fname):
    f=open(fname,"r")
    for line in f:
        print(line)
    f.close()
