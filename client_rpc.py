### Middleware for IoT ###

# This Program acts as a client device that sends data periodically until a sendDisable message is received

import os
import time
import sys
import json
from random import *
import paho.mqtt.client as mqtt

# Thingsboard platform credentials
THINGSBOARD_HOST = 'demo.thingsboard.io'
ACCESS_TOKEN = 'yIq65tr4h2F4PNrBxc4u'
#request = {"method": "getactive", "params": ""} # used if we want the device to check the status on thingsboard by sending an RPC request

running = True
count = 0

topic="v1/devices/me/telemetry"

# MQTT on_connect callback function
def on_connect(client, userdata, flags, rc):
    print("rc code:", rc)
    #client.subscribe('v1/devices/me/rpc/response/+') # used if we are expecting RPC replys from thingsboard
    client.subscribe('v1/devices/me/rpc/request/+')
    #client.publish('v1/devices/me/rpc/request/1',json.dumps(request), 1)

# MQTT on_message caallback function
def on_message(client, userdata, msg):
    print('Topic: ' + msg.topic + '\nMessage: ' + str(msg.payload))

    global running
    running = False
    print("on_message :")
    print(running)

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


    data['temperature'] = round(uniform(25, 46),2)
    data['pressure']    = round(uniform(1, 10),2)
    data['humidity']    = round(uniform(20, 50),2)
    data['machine-state'] = "on"
    data_out=json.dumps(data) #create JSON object
    print("published topic",topic, "data out= ",data_out)
    ret=client.publish(topic,data_out,0)    #publish    

   
    time.sleep(5)
#client.loop_forever()