import os
import json
from dotenv import load_dotenv

import paho.mqtt.client as paho
from paho import mqtt
import time
from sys import argv
from keyboard import read_event
from random import choice


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
    global player_client
    print("message: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    player_client.handle_message(msg)


class AutoPlayerClient:
    def __init__(self) -> None:
        if len(argv) < 4:
            print(
                "Usage: python PlayerClient.py <player_name> <lobby_name> <team_name>"
            )
            exit(1)
        self.player_name = argv[1]
        self.lobby_name = argv[2]
        self.team_name = argv[3]
        load_dotenv(dotenv_path="../credentials.env")
        broker_address = os.environ.get("BROKER_ADDRESS")
        broker_port = int(os.environ.get("BROKER_PORT"))
        username = os.environ.get("USER_NAME")
        password = os.environ.get("PASSWORD")

        self.client = paho.Client(
            client_id=self.player_name, userdata=None, protocol=paho.MQTTv5
        )
        # enable TLS for secure connection
        self.client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
        # set username and password
        self.client.username_pw_set(username, password)
        # connect to HiveMQ Cloud on port 8883 (default for MQTT)
        self.client.connect(broker_address, broker_port)

        # setting callbacks, use separate functions like above for better visibility
        self.client.on_subscribe = (
            on_subscribe  # Can comment out to not print when subscribing to new topics
        )
        self.client.on_message = on_message
        self.client.on_publish = (
            on_publish  # Can comment out to not print when publishing to topics
        )
        self.client.subscribe(f"games/{self.lobby_name}/lobby")
        self.client.subscribe(f"games/{self.lobby_name}/{self.player_name}/game_state")
        self.client.subscribe(f"games/{self.lobby_name}/scores")

        self.ended = False
        self.wall_map = [[False for i in range(12)] for j in range(12)]
        self.coin_map = [[0 for i in range(10)] for j in range(10)]
        self.curr_pos: list[int] = [0, 0]
        self.curr_score: int = 0
        self.visible_map: list[list[int]] = [[0 for i in range(5)] for j in range(5)]
        self.visible_map[2][2] = -1

        self.wall_map[0][:] = [True for i in range(len(self.wall_map[0]))]
        for i in range(len(self.wall_map)):
            self.wall_map[i][0] = True
        for i in range(len(self.wall_map)):
            self.wall_map[i][-1] = True
        self.wall_map[-1][:] = [True for i in range(len(self.wall_map[0]))]

        self.client.publish(
            "new_game",
            json.dumps(
                {
                    "lobby_name": self.lobby_name,
                    "team_name": self.team_name,
                    "player_name": self.player_name,
                }
            ),
        )
        time.sleep(1)  # Wait a second to resolve game start

    def handle_message(self, msg):
        if "Error" in msg.payload.decode():
            ended = True
            exit(1)
        if "Game Over" in msg.payload.decode():
            ended = True
            exit(0)
        if msg.topic == f"games/{self.lobby_name}/{self.player_name}/game_state":
            game_state = json.loads(msg.payload.decode())
            self.load_visible_map(game_state)
            self.print_map(game_state)
            self.next_move()
        if msg.topic == f"games/{self.lobby_name}/scores":
            scores = json.loads(msg.payload.decode())
            if scores[self.team_name] != self.curr_score:
                if (
                    self.coin_map[self.curr_pos]
                    == scores[self.team_name] - self.curr_score
                ):
                    self.coin_map[self.curr_pos] = 0
                self.curr_score = scores[self.team_name]

    def print_map(self, game_state: dict):
        curr_pos = game_state["currentPosition"]
        teammate_pos: list[list[int]] = game_state["teammatePositions"]
        teammate_names: list[str] = game_state["teammateNames"]
        enemy_pos: list[list[int]] = game_state["enemyPositions"]
        coin1: list[list[int]] = game_state["coin1"]
        coin2: list[list[int]] = game_state["coin2"]
        coin3: list[list[int]] = game_state["coin3"]
        walls: list[list[int]] = game_state["walls"]
        visible_map = [[None for i in range(5)] for j in range(5)]

        visible_map[2][2] = self.player_name
        for i in range(len(teammate_pos)):
            visible_map[4 - (curr_pos[0] - teammate_pos[i][0] + 2)][
                teammate_pos[i][1] - curr_pos[1] + 2
            ] = teammate_names[i]
        for i in range(len(enemy_pos)):
            visible_map[4 - (curr_pos[0] - enemy_pos[i][0] + 2)][
                enemy_pos[i][1] - curr_pos[1] + 2
            ] = "Enemy"
        for i in range(len(coin1)):
            visible_map[4 - (curr_pos[0] - coin1[i][0] + 2)][
                coin1[i][1] - curr_pos[1] + 2
            ] = "Coin1"
        for i in range(len(coin2)):
            visible_map[4 - (curr_pos[0] - coin2[i][0] + 2)][
                coin2[i][1] - curr_pos[1] + 2
            ] = "Coin2"
        for i in range(len(coin3)):
            visible_map[4 - (curr_pos[0] - coin3[i][0] + 2)][
                coin3[i][1] - curr_pos[1] + 2
            ] = "Coin3"
        for i in range(len(walls)):
            visible_map[4 - (curr_pos[0] - walls[i][0] + 2)][
                walls[i][1] - curr_pos[1] + 2
            ] = "Wall"

        output = []
        for row in visible_map:
            row_str = []
            for cell in row:
                row_str.append(str(cell))
            output.append("\t".join(row_str))
        output = "\n".join(output)
        print(output)

    def print_wall_map(self):
        for row in self.wall_map:
            print(row)

    def print_coin_map(self):
        for row in self.coin_map:
            print(row)

    def load_visible_map(self, game_state: dict):
        self.curr_pos = game_state["currentPosition"]
        teammate_pos: list[list[int]] = game_state["teammatePositions"]
        enemy_pos: list[list[int]] = game_state["enemyPositions"]
        coin1: list[list[int]] = game_state["coin1"]
        coin2: list[list[int]] = game_state["coin2"]
        coin3: list[list[int]] = game_state["coin3"]
        walls: list[list[int]] = game_state["walls"]
        self.visible_map = [[0 for i in range(5)] for j in range(5)]
        self.visible_map[2][2] = -1

        for i in range(len(teammate_pos)):
            self.visible_map[4 - (self.curr_pos[0] - teammate_pos[i][0] + 2)][
                teammate_pos[i][1] - self.curr_pos[1] + 2
            ] = -1
        for i in range(len(enemy_pos)):
            self.visible_map[4 - (self.curr_pos[0] - enemy_pos[i][0] + 2)][
                enemy_pos[i][1] - self.curr_pos[1] + 2
            ] = -1
        for i in range(len(coin1)):
            self.coin_map[coin1[i][0]][coin1[i][1]] = 1
            self.visible_map[4 - (self.curr_pos[0] - coin1[i][0] + 2)][
                coin1[i][1] - self.curr_pos[1] + 2
            ] = 1
        for i in range(len(coin2)):
            self.coin_map[coin2[i][0]][coin2[i][1]] = 2
            self.visible_map[4 - (self.curr_pos[0] - coin2[i][0] + 2)][
                coin2[i][1] - self.curr_pos[1] + 2
            ] = 2
        for i in range(len(coin3)):
            self.coin_map[coin3[i][0]][coin3[i][1]] = 3
            self.visible_map[4 - (self.curr_pos[0] - coin3[i][0] + 2)][
                coin3[i][1] - self.curr_pos[1] + 2
            ] = 3
        for i in range(len(walls)):
            self.wall_map[walls[i][0] + 1][walls[i][1] + 1] = True
            self.visible_map[4 - (self.curr_pos[0] - walls[i][0] + 2)][
                walls[i][1] - self.curr_pos[1] + 2
            ] = -1

    def next_move(self):
        pass


if __name__ == "__main__":
    player_client = AutoPlayerClient()
    player_client.client.publish(f"games/{player_client.lobby_name}/start", "START")
    player_client.client.loop_start()
    while True:
        key_event = read_event()
        if key_event.event_type == "up":
            continue
        match key_event.name:
            case "q":
                player_client.client.publish(
                    f"games/{player_client.lobby_name}/start", "STOP"
                )
                break
            case "up":
                player_client.client.publish(
                    f"games/{player_client.lobby_name}/{player_client.player_name}/move",
                    "UP",
                )
            case "down":
                player_client.client.publish(
                    f"games/{player_client.lobby_name}/{player_client.player_name}/move",
                    "DOWN",
                )
            case "left":
                player_client.client.publish(
                    f"games/{player_client.lobby_name}/{player_client.player_name}/move",
                    "LEFT",
                )
            case "right":
                player_client.client.publish(
                    f"games/{player_client.lobby_name}/{player_client.player_name}/move",
                    "RIGHT",
                )
            case "w":
                player_client.print_wall_map()
            case "c":
                player_client.print_coin_map()
    player_client.client.loop_stop()
