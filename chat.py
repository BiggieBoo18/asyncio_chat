import asyncio
import sys

class ChatProtocol(asyncio.Protocol):
    def __init__(self, loop, first_message=""):
        self.loop          = loop
        self.first_message = first_message

    def connection_made(self, transport):
        self.peername = transport.get_extra_info('peername')
        self.transport = transport
        # first send message
        if self.first_message:
            self.transport.write(self.first_message)

    def data_received(self, data):
        message = data.decode()
        print('<{}:{}>: {!r}'.format(self.peername[0], self.peername[1], message))

        # print('Send: {!r}'.format(message))
        # self.transport.write(data)

        # print('Close the client socket')
        self.transport.close()

async def input_message(loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    # def _callback(future):
    #     print("Done")

    command = loop.create_future()
    # command.add_done_callback(_callback)

    def _input_message():
        command.set_result(input("send command>> ").encode())
    loop.call_later(0.2, _input_message)
    return (await command)

def parse_command(command):
    parts = command.split(" ")
    return parts

def search_user(user): # for test
    test = {"biggieboo":("127.0.0.1", 8889)}
    return test.get(user)

async def execute_command(command, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    parts = parse_command(command)
    if parts[0]=="join":   # join
        pass
    elif parts[0]=="send": # send
        if len(parts)<3:
            return None
        # search dns
        info = search_user(parts[1])
        if info:
            addr, port = info
            coro = loop.create_connection(lambda: ChatProtocol(loop, bytes(" ".join(parts[2:]), sys.getdefaultencoding())), addr, port)
        else:
            coro = None
        return coro

def main():
    loop = asyncio.get_event_loop()
    # Each client connection will create a new protocol instance
    first_message = ""
    coro = loop.create_server(lambda: ChatProtocol(loop, first_message), '', 8888)
    server = loop.run_until_complete(coro)

    # Serve requests until Ctrl+C is pressed
    print('Serving on {}'.format(server.sockets[0].getsockname()))
    try:
        while True:
            command = loop.run_until_complete(input_message())
            if command:
                command = command.decode()
                coro = loop.run_until_complete(execute_command(command))
                if coro:
                    loop.run_until_complete(coro)
        # loop.run_forever()
    except KeyboardInterrupt:
        pass

    # Close the server
    server.close()
    loop.run_until_complete(server.wait_closed())
    loop.close()

if __name__ == "__main__":
    main()
