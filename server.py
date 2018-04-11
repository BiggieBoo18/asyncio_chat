import asyncio
from collections import namedtuple, Counter
import random

# constant
LIFEPOINTS = 3  # If janken result is win, LIFEPOINTS increase, or lose, LIFEPOINTS decrease
N_CARDS    = 10 # Number of cards per user
INDEX_CLIENT     = 0
INDEX_LIFEPOINTS = 1
INDEX_CARDS      = 2
INDEX_ADDRESS    = 3

Client = namedtuple("Client", "reader writer")

class Server:
    clients = {}
    server = None

    def __init__(self, host="127.0.0.1", port=1818, address=""):
        self.loop    = asyncio.get_event_loop()
        self.host    = host
        self.port    = port
        self.address = address
        self.clients = {}
        self.groups  = {}
        self.janken  = {}
        self.stat    = {}
        self.buylife = []

    @asyncio.coroutine
    def run_server(self):
        try:
            self.server = yield from asyncio.start_server(self.client_connected, self.host, self.port)
            print("Running server on {}:{}".format(self.host, self.port))
        except OSError:
            print("Cannot bind to this port! Is the server already running?")
            self.loop.stop()

    def send_to_client(self, name, msg):
        client = self.clients.get(name)
        if client:
            client = client[INDEX_CLIENT]
            print("Sending to {}".format(name))
            client.writer.write("{}\n".format(msg).encode())
            return True
        else:
            return False

    def send_to_group(self, groupname, msg):
        names = self.groups.get(groupname)
        if names:
            print("Got message {}, send to group".format(msg))
            for name in names:
                self.send_to_client(name, msg)
            return True
        else:
            return False

    def send_to_all_clients(self, peername, msg):
        print("Got message {}, send to all clients".format(msg))
        for client_peername, client in self.clients.items():
            print("Sending to {}".format(client_peername))
            client[0].writer.write("{}: {}\n".format(peername, msg).encode())
        return

    def close_clients(self):
        print("Sending EndOfFile to all clients to close them.")
        for peername, client in self.clients.items():
            client[0].writer.write_eof()

    def deliver_cards(self):
        cards = sorted([random.choice(["G", "C", "P"]) for i in range(N_CARDS)])
        stat = Counter(cards)
        if not self.stat:
            self.stat = stat
        else:
            for k, v in stat.items():
                tmp = self.stat.get(k)
                if not tmp:
                    self.stat[k] = v
                else:
                    self.stat[k] += v
        return cards

    def register_user(self, username, address, client):
        if not self.clients.get(username):
            cards = self.deliver_cards()
            self.clients[username] = [client, LIFEPOINTS, cards, address]
            return True
        else:
            return False

    def create_group(self, groupname, users):
        if not self.groups.get(groupname) and all([self.clients.get(name) for name in users]):
            self.groups[groupname] = users
            return True
        else:
            return False

    def send_janken_accept(self, username, opponent):
        user_info = self.clients.get(username)
        oppo_info = self.clients.get(opponent)
        self.send_to_client(username, "janken {} start {}".format(opponent, " ".join(user_info[INDEX_CARDS])))
        self.send_to_client(opponent, "janken {} start {}".format(username, " ".join(oppo_info[INDEX_CARDS])))

    def send_janken_refuse(self, username, opponent):
        self.janken.pop((username, opponent), None)
        self.janken.pop((opponent, username), None)
        self.send_to_client(username, "refused janken challenge {} vs {}".format(username, opponent))
        self.send_to_client(opponent, "refused janken challenge {} vs {}".format(username, opponent))

    def check_qualified(self, username, opponent):
        ret  = True
        user = self.clients.get(username)
        oppo = self.clients.get(opponent)
        if not (user and oppo):
            return False
        user_lifepoints = user[INDEX_LIFEPOINTS]
        oppo_lifepoints = oppo[INDEX_LIFEPOINTS]
        user_cards      = user[INDEX_CARDS]
        oppo_cards      = oppo[INDEX_CARDS]
        if user_lifepoints==0 or oppo_lifepoints==0 or not user_cards or not oppo_cards:
            ret = False
        return ret

    def game_results(self, results):
        result1, result2 = results
        # (Win, Lose)
        if ((result1=="G" and result2=="C") or
            (result1=="C" and result2=="P") or
            (result1=="P" and result2=="G")):
            return ("Win", "Lose")
        # (Lose, Win)
        elif ((result1=="G" and result2=="P") or
              (result1=="C" and result2=="G") or
              (result1=="P" and result2=="C")):
            return ("Lose", "Win")
        # (Draw, Draw)
        else:
            return ("Draw", "Draw")

    def change_n_cards(self, name, result):
        ret = True
        client_info = self.clients.get(name)
        if client_info:
            client_info[INDEX_CARDS].remove(result)
            self.stat[result] -= 1
        else:
            ret = False
        return ret

    def change_lifepoints(self, name, result):
        ret = True
        client_info = self.clients.get(name)
        if not client_info:
            return False
        if result=="Win":
            client_info[INDEX_LIFEPOINTS] += 1
        elif result=="Lose":
            client_info[INDEX_LIFEPOINTS] -= 1
        elif result=="Draw":
            pass
        else:
            ret = False
        return ret

    def send_janken_result(self, username, opponent, part_msg):
        if (username, opponent) in self.janken:
            results = self.janken[(username, opponent)]
            results[0] = part_msg[3]
            if not None in results:
                self.change_n_cards(opponent, results[1])
                self.change_n_cards(username, results[0])
                results = self.game_results(results)
                self.send_to_client(username, "janken {} You {}".format(opponent, results[0]))
                self.send_to_client(opponent, "janken {} You {}".format(username, results[1]))
                self.change_lifepoints(opponent, results[1])
                self.change_lifepoints(username, results[0])
                self.janken.pop((username, opponent))
        elif (opponent, username) in self.janken:
            results = self.janken[(opponent, username)]
            results[1] = part_msg[3]
            if not None in results:
                self.change_n_cards(opponent, results[0])
                self.change_n_cards(username, results[1])
                results = self.game_results(results)
                self.send_to_client(username, "janken {} You {}".format(opponent, results[1]))
                self.send_to_client(opponent, "janken {} You {}".format(username, results[0]))
                self.change_lifepoints(opponent, results[0])
                self.change_lifepoints(username, results[1])
                self.janken.pop((opponent, username))

    def send_buylife_accept(self, username, name, price):
        self.send_to_client(username, "accepted buylife between {} and {}".format(username, name))
        self.send_to_client(name, "accepted buylife between {} and {}".format(username, name))
        if (username, name) in self.buylife:
            name_info = self.clients.get(name)
            name_addr = name_info[INDEX_ADDRESS]
            name_info[INDEX_LIFEPOINTS] -= 1
            user_info = self.clients.get(username)
            user_info[INDEX_LIFEPOINTS] += 1
            self.send_to_client(username, "address {} {}".format(name_addr, price))
            self.buylife.remove((username, name))
        elif (name, username) in self.buylife:
            user_info = self.clients.get(username)
            user_addr = user_info[INDEX_ADDRESS]
            user_info[INDEX_LIFEPOINTS] -= 1
            name_info = self.clients.get(name)
            name_info[INDEX_LIFEPOINTS] += 1
            self.send_to_client(name, "address {} {}".format(user_addr, price))
            self.buylife.remove((name, username))

    def send_buylife_refuse(self, username, name):
        if (username, name) in self.buylife:
            self.buylife.remove((username, name))
        elif (name, username) in self.buylife:
            self.buylife.remove((name, username))
        self.send_to_client(username, "refused buylife between {} and {}".format(username, name))
        self.send_to_client(name, "refused buylife between {} and {}".format(username, name))

    def execute_command(self, peername, new_client, msg, username):
        part_msg = msg.split(" ")
        if part_msg[0]=="join": # join command
            if len(part_msg)>2: # "join username"
                if self.register_user(part_msg[1], part_msg[2], new_client):
                    username = part_msg[1]
                    self.send_to_client(part_msg[1], "Registered: {}".format(part_msg[1]))
                    return username
                else:
                    self.send_to_client(part_msg[1], "[Error] Already used: {}".format(part_msg[1]))
            else:
                self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))
        elif part_msg[0]=="send": # send command
            if len(part_msg)>2: # "send username/groupname message"
                if not self.send_to_client(part_msg[1], "{} >>> {}".format(username, " ".join(part_msg[2:]))):
                    if not self.send_to_group(part_msg[1], "{} >>> {}".format(username, " ".join(part_msg[2:]))):
                        self.send_to_client(username, "[Error] Username or Groupname is not found: {}".format(msg))
            else:
                self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))
        elif part_msg[0]=="create": # create command
            if len(part_msg)>2: # "create groupname user1 user2..."
                groupname = part_msg[1]
                if self.create_group(groupname, part_msg[2:]):
                    self.send_to_group(groupname, "Created group: {}".format(part_msg[1]))
                else:
                    self.send_to_client(username, "[Error] Already used: {} or username is not found".format(part_msg[1]))
            else:
                self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))
        elif part_msg[0]=="janken": # janken command
            if len(part_msg)>1: # "janken username" "janken username *args"
                opponent = part_msg[1]
                print("username:{}, opponent:{}".format(username, opponent))
                if not self.check_qualified(username, opponent):
                    self.send_to_client(username, "[Error] {} or {} is not qualified to play janken".format(username, opponent))
                    self.send_to_client(opponent, "[Error] {} or {} is not qualified to play janken".format(username, opponent))
                elif ((username, opponent) in self.janken or
                    (opponent, username) in self.janken):
                    if len(part_msg)>2:
                        if part_msg[2]=="accept":
                            self.send_janken_accept(username, opponent)
                        elif part_msg[2]=="refuse":
                            self.send_janken_refuse(username, opponent)
                        if part_msg[2]=="result":
                            self.send_janken_result(username, opponent, part_msg)
                else:
                    self.janken[(username, opponent)] = [None, None]
                    if not self.send_to_client(opponent, "janken {} Recieved a janken challenge from {}".format(username, username)):
                        self.send_to_client(username, "[Error] Opponent is not found: {}".format(opponent))
            else:
                self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))
        elif part_msg[0]=="buylife": # buylife command
            if len(part_msg)>2: # buylife username life_price
                name  = part_msg[1]
                price = part_msg[2]
                if ((username, name) in self.buylife or
                    (name, username) in self.buylife):
                    print("here1")
                    if len(part_msg)>3: # buylife username life_price accept/refuse
                        res = part_msg[3]
                        if res=="accept":
                            self.send_buylife_accept(username, name, price)
                        elif res=="refuse":
                            self.send_buylife_refuse(username, name)
                else:
                    print("here2")
                    if not (price.isdigit() and self.send_to_client(name, "buylife {} {}".format(username, price))):
                        self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))
                    else:
                        self.buylife.append((username, name))
            else:
                self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))
        elif part_msg[0]=="myinfo": # myinfo command
            client_info = self.clients.get(username)
            self.send_to_client(username, "Your infomation:\nlifepoints={}\ncards={}\naddress={}".format(client_info[INDEX_LIFEPOINTS], client_info[INDEX_CARDS], client_info[INDEX_ADDRESS]))
        elif part_msg[0]=="stat": # stat command
            client_info = self.clients.get(username)
            self.send_to_client(username, "Statistics infomation:\nstat={}".format(dict(self.stat)))
        else:
            self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        print("Client connected.")
        peername = writer.transport.get_extra_info("peername")
        new_client = Client(reader, writer)
        self.clients[peername] = [new_client, 0, []]
        # self.send_to_client(peername, "Welcome to this server client: {}".format(peername))
        username = ""
        while not reader.at_eof():
            try:
                msg = yield from reader.readline()
                if msg:
                    msg = msg.decode().strip()
                    print("Server Received: {}".format(msg))
                    if not msg == "close()":
                        # parse command
                        ret = self.execute_command(peername, new_client, msg, username)
                        if ret:
                            username = ret
                    else:
                        print("User {} disconnected".format(username))
                        try:
                            del self.clients[username]
                        except KeyError:
                            pass
                        writer.write_eof()
            except ConnectionResetError as e:
                print("ERROR: {}".format(e))
                try:
                    del self.clients[username]
                except KeyError:
                    pass
                return

    def close(self):
        self.close_clients()
        self.loop.stop()

def main(address):
    loop = asyncio.get_event_loop()
    mainserver = Server(address=address)
    asyncio.ensure_future(mainserver.run_server())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Received interrupt, closing")
        mainserver.close()
    finally:
        loop.close()

if __name__ == "__main__":
    address = ""
    while not address:
        address = input("Please type your address: ")
    main(address)
