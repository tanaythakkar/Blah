import random
import boto3
import RPi.GPIO as GPIO
from picamera import PiCamera

#--------------------------------------------
#CAMERA
camera = PiCamera()
camera.capture('/home/pi/Desktop/image.jpg')
#--------------------------------------------
#pir
import RPi.GPIO as GPIO
x = 0
#GPIO.setwarnings(false)
GPIO.setmode(GPIO.BCM)
GPIO.setup(14,GPIO.OUT)
GPIO.setup(23,GPIO.IN)
while x<1:
    a = GPIO.input(23)
   # a = bool(a)
    if a == 1:
        GPIO.output(14,1)
    else:
        GPIO.output(14,0)
    #x+=1
#--------------------------------------------------
#servo
import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BOARD)
GPIO.setup(24, GPIO.OUT)
pwm=GPIO.PWM(24, 50)
pwm.start(0)
a  = input("enter angle")
a = int(a)
def SetAngle(angle):
        duty = angle / 18 + 2
        GPIO.output(24, True)
        pwm.ChangeDutyCycle(duty)
        time.sleep(1)
        GPIO.output(24, False)
        pwm.ChangeDutyCycle(0)
SetAngle(a)
time.sleep(2)
SetAngle(0)
pwm.stop()
GPIO.cleanup()
#--------------------------------------------------------
#import requests

#import json
import random
name2 = input("users name ")
phone = 0
name = "2"
tanay_ph = 9712907611
anish_ph = 9008091950
if name2 == "tanay":
    phone = tanay_ph
    name = "tanay"
elif name2 == "anish":
    phone = anish_ph
    name = "anish"
else:
    print("This User Does Not Exist!")
random_int = random.randrange(1000,10000)
r = requests.get('https://maker.ifttt.com/trigger/sendsms/with/key/cFTVBLO8YrXeBsI_8RD3AM'+'?value1='+str(random_int)+'&'+'value2='+name+"&"+'value3='+str(phone))
r.status_code
print(random_int)
#if

