import os
import json
from dotenv import load_dotenv

import paho.mqtt.client as paho
from paho import mqtt
import time
from sys import argv
from keyboard import read_event

ended = False


# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    """
    Prints the result of the connection with a reasoncode to stdout ( used as callback for connect )
    :param client: the client itself
    :param userdata: userdata is set when initiating the client, here it is userdata=None
    :param flags: these are response flags sent by the broker
    :param rc: stands for reasonCode, which is a code for the connection result
    :param properties: can be used in MQTTv5, but is optional
    """
    print("CONNACK received with code %s." % rc)


# with this callback you can see if your publish was successful
def on_publish(client, userdata, mid, properties=None):
    """
    Prints mid to stdout to reassure a successful publish ( used as callback for publish )
    :param client: the client itself
    :param userdata: userdata is set when initiating the client, here it is userdata=None
    :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
    :param properties: can be used in MQTTv5, but is optional
    """
    print("mid: " + str(mid))


# print which topic was subscribed to
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    """
    Prints a reassurance for successfully subscribing
    :param client: the client itself
    :param userdata: userdata is set when initiating the client, here it is userdata=None
    :param mid: variable returned from the corresponding publish() call, to allow outgoing messages to be tracked
    :param granted_qos: this is the qos that you declare when subscribing, use the same one for publishing
    :param properties: can be used in MQTTv5, but is optional
    """
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


# print message, useful for checking if it was successful
def on_message(client, userdata, msg):
    """
    Prints a mqtt message to stdout ( used as callback for subscribe )
    :param client: the client itself
    :param userdata: userdata is set when initiating the client, here it is userdata=None
    :param msg: the message with topic and payload
    """
    global ended
    print("message: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    if "Error" in msg.payload.decode():
        ended = True
        exit(1)
    if "Game Over" in msg.payload.decode():
        ended = True
        exit(0)


if __name__ == "__main__":
    if len(argv) < 4:
        print("Usage: python PlayerClient.py <player_name> <lobby_name> <team_name>")
        exit(1)
    player_name = argv[1]
    lobby_name = argv[2]
    team_name = argv[3]
    load_dotenv(dotenv_path="../credentials.env")

    broker_address = os.environ.get("BROKER_ADDRESS")
    broker_port = int(os.environ.get("BROKER_PORT"))
    username = os.environ.get("USER_NAME")
    password = os.environ.get("PASSWORD")

    client = paho.Client(client_id=player_name, userdata=None, protocol=paho.MQTTv5)

    # enable TLS for secure connection
    client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
    # set username and password
    client.username_pw_set(username, password)
    # connect to HiveMQ Cloud on port 8883 (default for MQTT)
    client.connect(broker_address, broker_port)

    # setting callbacks, use separate functions like above for better visibility
    client.on_subscribe = (
        on_subscribe  # Can comment out to not print when subscribing to new topics
    )
    client.on_message = on_message
    client.on_publish = (
        on_publish  # Can comment out to not print when publishing to topics
    )

    client.subscribe(f"games/{lobby_name}/lobby")
    client.subscribe(f"games/{lobby_name}/+/game_state")
    client.subscribe(f"games/{lobby_name}/scores")

    client.publish(
        "new_game",
        json.dumps(
            {
                "lobby_name": lobby_name,
                "team_name": team_name,
                "player_name": player_name,
            }
        ),
    )

    time.sleep(1)  # Wait a second to resolve game start
    # Main loop
    # If user presses up, send up, if down pressed, send down, etc
    # If user presses enter, send start
    # If user presses q, send stop
    client.loop_start()

    while True:
        if ended:
            break
        key_event = read_event(suppress=True)
        if key_event.event_type == "up":
            continue
        match key_event.name:
            case "q":
                client.publish(f"games/{lobby_name}/start", "STOP")
                break
            case "up":
                client.publish(f"games/{lobby_name}/{player_name}/move", "UP")
            case "down":
                client.publish(f"games/{lobby_name}/{player_name}/move", "DOWN")
            case "left":
                client.publish(f"games/{lobby_name}/{player_name}/move", "LEFT")
            case "right":
                client.publish(f"games/{lobby_name}/{player_name}/move", "RIGHT")
            case "enter":
                client.publish(f"games/{lobby_name}/start", "START")

    client.loop_stop()
