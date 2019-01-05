# This Program illustrates the Client Side RPC on ThingsBoard IoT Platform
# Paste your ThingsBoard IoT Platform IP and Device access token
# Client_Side_RPC.py : This program will illustrates the Client side
import os
import time
import sys
import json
from random import *
import paho.mqtt.client as mqtt

# Thingsboard platform credentials
THINGSBOARD_HOST = 'demo.thingsboard.io'
ACCESS_TOKEN = 'yIq65tr4h2F4PNrBxc4u'
request = {"method": "getactive", "params": ""}

running = True
count = 0

topic="v1/devices/me/telemetry"

# MQTT on_connect callback function
def on_connect(client, userdata, flags, rc):
    print("rc code:", rc)
    #client.subscribe('v1/devices/me/rpc/response/+')
    client.subscribe('v1/devices/me/rpc/request/+')
    #running = True
    #client.publish('v1/devices/me/rpc/request/1',json.dumps(request), 1)

# MQTT on_message caallback function
def on_message(client, userdata, msg):
    print('Topic: ' + msg.topic + '\nMessage: ' + str(msg.payload))
    #running = False
    #count = count + 1 
    #change2False()
    global running
    running = False
    print(count)
    print("on_message :")
    print(running)
    # if active is disabled, then disconnect

def change2False(running):
	print("changed2False")
	running = not running
	#return running
def sendback():
	return running
# logic: send data until you get a n
data = {}

# Create a new client for receiving messages
# start the client instance
client = mqtt.Client()

# registering the callbacks
client.on_connect = on_connect
time.sleep(2)
client.on_message = on_message

client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)

client.loop_start()

while running:
    print("loop: ")
    print(running)
    #running = sendback()
    #print(running)

    #running = change2False(running)
    data['temperature'] = round(uniform(45, 46),2)
    #data['pressure']    = round(uniform(1, 10),2)
    #data['humidity']    = round(uniform(20, 50),2)
    data_out=json.dumps(data) #create JSON object
    print("published topic",topic, "data out= ",data_out)
    ret=client.publish(topic,data_out,0)    #publish    
    #if data['temperature']> 50:
    #	client.publish('v1/devices/me/rpc/request/1',json.dumps(request), 1)
    if not running:
        print("loop is broken")
        client.loop_stop()
        break
    print(count)
    if count >0:
    	print("the count worked")
    	break
   
    time.sleep(5)
#client.loop_forever()