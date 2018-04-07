import asyncio

def watch_stdin():
    msg = input()
    return msg

class Client:
    reader = None
    writer = None
    sockname = None

    def __init__(self, host='127.0.0.1', port=1818):
        self.host     = host
        self.port     = port
        self.username = ""

    def send_msg(self, msg):
        msg = '{}\n'.format(msg).encode()
        self.writer.write(msg)

    def close(self):
        print('Closing.')
        if self.writer:
            self.send_msg('close()')
        mainloop = asyncio.get_event_loop()
        mainloop.stop()

    @asyncio.coroutine
    def create_input(self):
        while True:
            mainloop = asyncio.get_event_loop()
            future = mainloop.run_in_executor(None, watch_stdin)
            input_message = yield from future
            part_msg = input_message.split()
            if input_message == 'close()' or not self.writer:
                self.close()
                break
            elif len(part_msg)>1 and part_msg[0]=="join":
                self.username = part_msg[1]
            if input_message:
                mainloop.call_soon_threadsafe(self.send_msg, input_message)

    def execute_command(self, msg):
        part_msg = msg.split(" ")
        if part_msg[0]=="janken":
            if part_msg[2]=="start":
                while True:
                    result = input("janken ([G]u, [C]hoki, [P]a): ")
                    if result in ["G", "Gu", "g", "gu"]:
                        result = "G"
                        break
                    elif result in ["C", "Choki", "c", "choki"]:
                        result = "C"
                        break
                    elif result in ["P", "Pa", "p", "pa"]:
                        result = "P"
                        break
                self.send_msg("janken {} result {}".format(part_msg[1], result))
            elif part_msg[2]=="You":
                print(part_msg)
            else:
                while True:
                    acception = input("{} accept ([Y]es or [N]o): ".format(" ".join(part_msg[2:])))
                    if acception in ["Yes", "Y", "yes", "y"]:
                        self.send_msg("janken {} accept".format(part_msg[1]))
                        break
                    elif acception in ["No", "N", "no", "n"]:
                        self.send_msg("janken {} refuse".format(part_msg[1]))
                    break
        else:
            print('{}'.format(msg))

    @asyncio.coroutine
    def connect(self):
        print('Connecting...')
        try:
            reader, writer = yield from asyncio.open_connection(self.host, self.port)
            asyncio.ensure_future(self.create_input())
            self.reader = reader
            self.writer = writer
            self.sockname = writer.get_extra_info('sockname')
            while not reader.at_eof():
                msg = yield from reader.readline()
                # if msg:
                #     print('{}'.format(msg.decode().strip()))
                self.execute_command(msg.decode().strip())
            print('The server closed the connection, press <enter> to exit.')
            self.writer = None
        except ConnectionRefusedError as e:
            print('Connection refused: {}'.format(e))
            self.close()

def main():
    loop = asyncio.get_event_loop()
    client = Client()
    asyncio.ensure_future(client.connect())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        # Raising and going through a keyboard interrupt will not interrupt the Input
        # So, do not stop using ctrl-c, the program will deadlock waiting for watch_stdin()
        print('Got keyboard interrupt <ctrl-C>, please send "close()" to exit.')
        loop.run_forever()
    loop.close()

if __name__ == '__main__':
    main()
