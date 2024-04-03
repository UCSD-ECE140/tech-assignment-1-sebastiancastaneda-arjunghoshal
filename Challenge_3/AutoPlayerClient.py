import os
import json
from dotenv import load_dotenv

import paho.mqtt.client as paho
from paho import mqtt
import time
from sys import argv
from keyboard import read_event
from random import choice
from math import sqrt


class PlayerMap:
    def __init__(self, observer, player_name: str, rows: int, columns: int) -> None:
        self.observer = observer
        self.player_name: str = player_name
        self.rows = rows
        self.columns = columns
        self.seen_coords: list[list[int]] = []
        self.current_position: list[int] = None
        self.teammates: list[list[int]] = []
        self.teammate_names: list[str] = []
        self.enemies: list[list[int]] = []
        self.walls: list[list[int]] = []
        self.coin1: list[list[int]] = []
        self.coin2: list[list[int]] = []
        self.coin3: list[list[int]] = []
        for i in range(columns + 2):
            self.walls.append([-1, i])
            self.walls.append([rows, i])
        for i in range(rows + 2):
            self.walls.append([i, -1])
            self.walls.append([i, columns])
        self.map: list[list[int]] = [
            [0 for i in range(self.rows)] for j in range(self.columns)
        ]

    def print_map(self):
        display_map: list[list[str]] = [
            ["None" for i in range(self.rows)] for j in range(self.columns)
        ]
        display_map[self.current_position[0]][
            self.current_position[1]
        ] = self.player_name
        for i, teammate in enumerate(self.teammates):
            display_map[teammate[0]][teammate[1]] = self.teammate_names[i]
        for enemy in self.enemies:
            display_map[enemy[0]][enemy[1]] = "Enemy"
        for wall in self.walls:
            if wall[0] < 0 or wall[0] == self.rows:
                continue
            if wall[1] < 0 or wall[1] == self.columns:
                continue
            display_map[wall[0]][wall[1]] = "Wall"
        for coin in self.coin1:
            display_map[coin[0]][coin[1]] = "Coin1"
        for coin in self.coin2:
            display_map[coin[0]][coin[1]] = "Coin2"
        for coin in self.coin3:
            display_map[coin[0]][coin[1]] = "Coin3"

        output = []
        for row in display_map:
            row_str = []
            for cell in row:
                row_str.append(str(cell))
            output.append("\t".join(row_str))
        output = "\n".join(output)
        print(output)

    def remove_collected_coins(self, game_state: dict):
        coins = [[], [], []]
        if self.current_position in self.coin1:
            self.coin1.remove(self.current_position)
            coins[0].append(self.current_position)
        if self.current_position in self.coin2:
            self.coin2.remove(self.current_position)
            coins[1].append(self.current_position)
        if self.current_position in self.coin3:
            self.coin3.remove(self.current_position)
            coins[2].append(self.current_position)
        for enemy in self.enemies:
            if enemy in self.coin1:
                self.coin1.remove(enemy)
                coins[0].append(enemy)
            if enemy in self.coin2:
                self.coin2.remove(enemy)
                coins[1].append(enemy)
            if enemy in self.coin3:
                self.coin3.remove(enemy)
                coins[2].append(enemy)

        for coin in self.coin1:
            if (
                coin[0] < self.current_position[0] - 2
                or coin[0] > self.current_position[0] + 2
            ):
                continue
            if (
                coin[1] < self.current_position[1] - 2
                or coin[1] > self.current_position[1] + 2
            ):
                continue
            if coin not in game_state["coin1"]:
                self.coin1.remove(coin)
                coins[0].append(coin)
        for coin in self.coin2:
            if (
                coin[0] < self.current_position[0] - 2
                or coin[0] > self.current_position[0] + 2
            ):
                continue
            if (
                coin[1] < self.current_position[1] - 2
                or coin[1] > self.current_position[1] + 2
            ):
                continue
            if coin not in game_state["coin2"]:
                self.coin2.remove(coin)
                coins[1].append(coin)
        for coin in self.coin3:
            if (
                coin[0] < self.current_position[0] - 2
                or coin[0] > self.current_position[0] + 2
            ):
                continue
            if (
                coin[1] < self.current_position[1] - 2
                or coin[1] > self.current_position[1] + 2
            ):
                continue
            if coin not in game_state["coin3"]:
                self.coin3.remove(coin)
                coins[2].append(coin)
        if coins[0] or coins[1] or coins[2]:
            self.observer.publish_collected(coins)

    def update_seen_coords(self):
        seen = []
        for i in range(-2, 3):
            for j in range(-2, 3):
                curr_position = [
                    self.current_position[0] + i,
                    self.current_position[1] + j,
                ]
                if curr_position[0] < 0 or curr_position[0] == self.rows:
                    continue
                if curr_position[1] < 0 or curr_position[1] == self.columns:
                    continue
                if curr_position in self.seen_coords:
                    continue
                self.seen_coords.append(curr_position)
                seen.append(curr_position)
        if seen:
            self.observer.publish_seen(seen)

    def update_teammates(self, player_name, player_position):
        if player_name not in self.teammate_names:
            self.teammate_names.append(player_name)
            self.teammates.append(player_position)
            return
        for i in range(len(self.teammates)):
            if self.teammate_names[i] != player_name:
                continue
            self.teammates[i] = player_position

    def update_seen_coins(self, game_state: dict):
        coins = [[], [], []]
        for coin in game_state["coin1"]:
            if coin in self.coin1:
                continue
            coins[0].append(coin)
            self.coin1.append(coin)
        for coin in game_state["coin2"]:
            if coin in self.coin2:
                continue
            coins[1].append(coin)
            self.coin2.append(coin)
        for coin in game_state["coin3"]:
            if coin in self.coin3:
                continue
            coins[2].append(coin)
            self.coin3.append(coin)
        if coins[0] or coins[1] or coins[2]:
            self.observer.publish_coins(coins)

    def update_walls(self, game_state: dict):
        seen_walls = []
        for wall in game_state["walls"]:
            if wall in self.walls:
                continue
            self.walls.append(wall)
            seen_walls.append(wall)
        if seen_walls:
            self.observer.publish_walls(seen_walls)

    def load_visible_map(self, game_state: dict):
        self.current_position = game_state["currentPosition"]
        self.enemies = game_state["enemyPositions"]
        self.remove_collected_coins(game_state)
        self.update_seen_coords()
        self.update_seen_coins(game_state)
        self.update_walls(game_state)
        self.map = [[0 for i in range(self.rows)] for j in range(self.columns)]
        for teammate in self.teammates:
            self.map[teammate[0]][teammate[1]] = -1
        for enemy in self.enemies:
            self.map[enemy[0]][enemy[1]] = -1
        for wall in self.walls:
            if wall[0] < 0 or wall[0] == self.rows:
                continue
            if wall[1] < 0 or wall[1] == self.columns:
                continue
            self.map[wall[0]][wall[1]] = -1
        for coin in self.coin1:
            self.map[coin[0]][coin[1]] = 1
        for coin in self.coin2:
            self.map[coin[0]][coin[1]] = 2
        for coin in self.coin3:
            self.map[coin[0]][coin[1]] = 3

    def next_move(self):
        # perform bfs on the entire known map
        moves = [
            ([0, -1], "LEFT"),
            ([0, 1], "RIGHT"),
            ([-1, 0], "UP"),
            ([1, 0], "DOWN"),
        ]
        queue = []
        visited = []
        best_score = 9999
        init_choice = choice(moves)
        best_direction = init_choice[1]
        next_coords = [
            self.current_position[0] + init_choice[0][0],
            self.current_position[1] + init_choice[0][1],
        ]
        curr_node = self.current_position
        for move, direction in moves:
            neighbor = [curr_node[0] + move[0], curr_node[1] + move[1]]
            if neighbor in visited:
                continue
            if neighbor[0] < 0 or neighbor[0] == self.rows:
                continue
            if neighbor[1] < 0 or neighbor[1] == self.columns:
                continue
            if self.map[neighbor[0]][neighbor[1]] == -1:
                continue
            queue.append((neighbor, direction, 1))
        while len(queue) > 0:
            curr_node, direction, path_len = queue.pop(0)
            for move, _ in moves:
                neighbor = [curr_node[0] + move[0], curr_node[1] + move[1]]
                if neighbor in visited:
                    continue
                if neighbor[0] < 0 or neighbor[0] == self.rows:
                    continue
                if neighbor[1] < 0 or neighbor[1] == self.columns:
                    continue
                if self.map[neighbor[0]][neighbor[1]] == -1:
                    continue
                queue.append((neighbor, direction, path_len + 1))
            if self.map[curr_node[0]][curr_node[1]] > 0:
                score = path_len / self.map[curr_node[0]][curr_node[1]]
                if score < best_score:
                    best_score = score
                    best_direction = direction
                    for move, dir in moves:
                        if dir != best_direction:
                            continue
                        next_coords = [
                            self.current_position[0] + move[0],
                            self.current_position[1] + move[1],
                        ]
                        break
            elif curr_node not in self.seen_coords:
                score = path_len + 200
                if score < best_score:
                    best_score = score
                    best_direction = direction
                    for move, dir in moves:
                        if dir != best_direction:
                            continue
                        next_coords = [
                            self.current_position[0] + move[0],
                            self.current_position[1] + move[1],
                        ]
                        break
            visited.append(curr_node)
        return best_direction, next_coords


def eucliedan_distance(a: list[int], b: list[int]):
    return sqrt((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2)


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
        self.client.subscribe(f"games/{self.lobby_name}/{self.team_name}/+/position")
        self.client.subscribe(f"games/{self.lobby_name}/{self.team_name}/+/collected")
        self.client.subscribe(f"games/{self.lobby_name}/{self.team_name}/+/seencoin")
        self.client.subscribe(f"games/{self.lobby_name}/{self.team_name}/+/seenwall")
        self.client.subscribe(f"games/{self.lobby_name}/{self.team_name}/+/seencoords")

        self.map = PlayerMap(self, self.player_name, 10, 10)
        self.curr_score: int = 0

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

    def publish_collected(self, coins: list[list[list[int]]]):
        self.client.publish(
            f"games/{self.lobby_name}/{self.team_name}/{self.player_name}/collected",
            str(coins),
        )

    def publish_coins(self, coins: list[list[list[int]]]):
        self.client.publish(
            f"games/{self.lobby_name}/{self.team_name}/{self.player_name}/seencoin",
            str(coins),
        )

    def publish_walls(self, wall: list[int]):
        self.client.publish(
            f"games/{self.lobby_name}/{self.team_name}/{self.player_name}/seenwall",
            str(wall),
        )

    def publish_seen(self, seen: list[int]):
        self.client.publish(
            f"games/{self.lobby_name}/{self.team_name}/{self.player_name}/seencoords",
            str(seen),
        )

    def handle_message(self, msg):
        if "Error" in msg.payload.decode():
            exit(1)
        if "Game Over" in msg.payload.decode():
            exit(0)
        if msg.topic == f"games/{self.lobby_name}/{self.player_name}/game_state":
            game_state = json.loads(msg.payload.decode())
            self.map.load_visible_map(game_state)
            self.map.print_map()
            direction, next_coords = self.map.next_move()
            self.move(direction, next_coords)
        topic_list = msg.topic.split("/")
        if topic_list[-1] == "position":
            if topic_list[3] != self.player_name:
                self.map.update_teammates(
                    topic_list[3], json.loads(msg.payload.decode())
                )
        if topic_list[-1] == "collected":
            coins = json.loads(msg.payload.decode())
            if topic_list[3] != self.player_name:
                for coin in coins[0]:
                    if coin in self.map.coin1:
                        self.map.coin1.remove(coin)
                for coin in coins[1]:
                    if coin in self.map.coin2:
                        self.map.coin2.remove(coin)
                for coin in coins[2]:
                    if coin in self.map.coin3:
                        self.map.coin3.remove(coin)
        if topic_list[-1] == "seencoin":
            coins = json.loads(msg.payload.decode())
            if topic_list[3] != self.player_name:
                for coin in coins[0]:
                    if coin not in self.map.coin1:
                        self.map.coin1.append(coin)
                for coin in coins[1]:
                    if coin not in self.map.coin2:
                        self.map.coin2.append(coin)
                for coin in coins[2]:
                    if coin not in self.map.coin3:
                        self.map.coin3.append(coin)
        if topic_list[-1] == "seenwall":
            walls = json.loads(msg.payload.decode())
            if topic_list[3] != self.player_name:
                for wall in walls:
                    if wall in self.map.walls:
                        continue
                    self.map.walls.append(wall)
        if topic_list[-1] == "seencoords":
            coords = json.loads(msg.payload.decode())
            if topic_list[3] != self.player_name:
                for coord in coords:
                    if coord in self.map.seen_coords:
                        continue
                    self.map.seen_coords.append(coord)

    def move(self, move: str, coords: list[int]):
        self.client.publish(
            f"games/{self.lobby_name}/{self.team_name}/{self.player_name}/position",
            str(coords),
        )
        self.client.publish(f"games/{self.lobby_name}/{self.player_name}/move", move)


if __name__ == "__main__":
    player_client = AutoPlayerClient()
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
            case "s":
                player_client.client.publish(
                    f"games/{player_client.lobby_name}/start", "START"
                )
    player_client.client.loop_stop()
