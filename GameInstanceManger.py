import os
import json

import paho.mqtt.client as paho
from paho import mqtt
from dotenv import load_dotenv
from pydantic import ValidationError

from InputTypes import NewPlayer, Move
from game import Game


# Global Variables
load_dotenv(dotenv_path='./credentials.env')

broker_address = os.environ.get('BROKER_ADDRESS')
broker_port = int(os.environ.get('BROKER_PORT'))
username = os.environ.get('USERNAME')
password = os.environ.get('PASSWORD')


def on_message(self, client, userdata, msg):
        """
        Prints a mqtt message to stdout ( used as callback for subscribe )
        :param client: the client itself
        :param userdata: userdata is set when initiating the client, here it is userdata=None
        :param msg: the message with topic and payload
        """
        pass


class GameInstanceManager():
    def __init__(self, lobby_name: str, team_dict: dict[str,list[str]]):
        """
        Creates a new client to handle each game
        """
        # initialize new client
        self.client = paho.Client(callback_api_version=paho.CallbackAPIVersion.VERSION1, client_id=lobby_name, userdata=None, protocol=paho.MQTTv5)
        # enable TLS for secure connection
        self.client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
        # set username and password
        self.client.username_pw_set(username, password)
        # connect to HiveMQ Cloud on port 8883 (default for MQTT)
        self.client.connect(broker_address, broker_port)
        # handles subscription
        self.client.on_message = self.on_message

        # subscribes to player movement topics
        for team in team_dict.keys():
             for player in team_dict[team]:  
                self.client.subscribe(f"games/{lobby_name}/{player}/move")

    def start(self):
        self.client.loop_start()

    def __del__(self):
        self.client.loop_stop()
        self.client.disconnect()


    

if __name__ == "__main__":
    game = GameInstanceManager()
