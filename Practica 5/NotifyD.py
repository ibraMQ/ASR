import sys
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

#Funcion envio de correo
def send_alert_attached(subject,cuerpo):
    COMMASPACE = ', '
    mailsender = "ibrahimqv99@gmail.com"
    mailreceip = "tanibet.escom@gmail.com"
    mailserver = 'smtp.gmail.com: 587'
    password = 'i123581321Q.'
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = mailsender
    msg['To'] = mailreceip
    body=MIMEText(cuerpo)
    msg.attach(body)
    s = smtplib.SMTP(mailserver)
    s.starttls()
    s.login(mailsender, password)
    s.sendmail(mailsender, mailreceip, msg.as_string())
    s.quit()

host = input()
ip = input()
varbind = []
while 1:
    try:
        varbind.append(input())
    except EOFError:
        print("Fin de lectura")
        break

print("Notificacion de Link Down (conexion perdida): ")
msgS="Alerta de LinkDown en la red"
today = date.today()
ips=str(ip).split("->")
msgB="+Fecha: "+today.strftime("%d/%m/%Y")+"\n+Host:"+str(host)+"\n+IP: "+str(ips[0])
msgB=msgB+"\n+Interfaz caida: "+str(ips[1])+"\n+Variables y Oids recividos: "+str(varbind)
print(msgS)
print(msgB)
send_alert_attached(msgS, msgB)