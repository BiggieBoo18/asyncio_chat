import asyncio
from collections import namedtuple

Client = namedtuple("Client", "reader writer")

class Server:
    clients = {}
    server = None

    def __init__(self, host="127.0.0.1", port=1818):
        self.loop = asyncio.get_event_loop()
        self.host = host
        self.port = port
        self.clients = {}
        self.groups  = {}
        self.janken  = {}

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
            client.writer.write("{}: {}\n".format(peername, msg).encode())
        return

    def close_clients(self):
        print("Sending EndOfFile to all clients to close them.")
        for peername, client in self.clients.items():
            client.writer.write_eof()

    def register_user(self, username, client):
        if not self.clients.get(username):
            self.clients[username] = client
            return True
        else:
            return False

    def create_group(self, groupname, users):
        if not self.groups.get(groupname) and all([self.clients.get(name) for name in users]):
            self.groups[groupname] = users
            return True
        else:
            return False

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

    def execute_command(self, peername, new_client, msg, username):
        part_msg = msg.split(" ")
        if part_msg[0]=="join": # join command
            if len(part_msg)>1: # "join username"
                if self.register_user(part_msg[1], new_client):
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
                if ((username, opponent) in self.janken or
                    (opponent, username) in self.janken):
                    if len(part_msg)>2:
                        if part_msg[2]=="accept":
                            self.send_to_client(username, "janken {} start".format(opponent))
                            self.send_to_client(opponent, "janken {} start".format(username))
                        elif part_msg[2]=="refuse":
                            self.janken.pop((username, opponent), None)
                            self.janken.pop((opponent, username), None)
                            self.send_to_client(username, "refused janken challenge {} vs {}".format(username, opponent))
                            self.send_to_client(opponent, "refused janken challenge {} vs {}".format(username, opponent))
                        if part_msg[2]=="result":
                            if (username, opponent) in self.janken:
                                results = self.janken[(username, opponent)]
                                results[0] = part_msg[3]
                                if not None in results:
                                    results = self.game_results(results)
                                    self.send_to_client(username, "janken {} You {}".format(opponent, results[0]))
                                    self.send_to_client(opponent, "janken {} You {}".format(username, results[1]))
                                    self.janken.pop((username, opponent))
                            elif (opponent, username) in self.janken:
                                results = self.janken[(opponent, username)]
                                results[1] = part_msg[3]
                                if not None in results:
                                    results = self.game_results(results)
                                    self.send_to_client(username, "janken {} You {}".format(opponent, results[1]))
                                    self.send_to_client(opponent, "janken {} You {}".format(username, results[0]))
                                    self.janken.pop((opponent, username))
                else:
                    self.janken[(username, opponent)] = [None, None]
                    if not self.send_to_client(opponent, "janken {} Recieved a janken challenge from {}".format(username, username)):
                        self.send_to_client(username, "[Error] Opponent is not found: {}".format(opponent))
            else:
                self.send_to_client(peername, "[Error] Invalid command: {}".format(msg))

    @asyncio.coroutine
    def client_connected(self, reader, writer):
        print("Client connected.")
        peername = writer.transport.get_extra_info("peername")
        new_client = Client(reader, writer)
        self.clients[peername] = new_client
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

def main():
    loop = asyncio.get_event_loop()
    mainserver = Server()
    asyncio.ensure_future(mainserver.run_server())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("Received interrupt, closing")
        mainserver.close()
    finally:
        loop.close()

if __name__ == "__main__":
    main()
