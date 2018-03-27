import asyncio

def input_message():
    message = input("send message: \n").encode()
    return message

class ChatProtocol(asyncio.Protocol):
    def __init__(self, loop, first_message=""):
        self.loop       = loop
        self.first_message = first_message

    def connection_made(self, transport):
        peername = transport.get_extra_info('peername')
        print('Connection from {}'.format(peername))
        self.transport = transport
        # first sent message
        if self.first_message:
            self.frist_message = input_message()
        self.transport.write(self.first_message)

    def data_received(self, data):
        message = data.decode()
        print('Data received: {!r}'.format(message))

        print('Send: {!r}'.format(message))
        self.transport.write(input_message())

        # print('Close the client socket')
        # self.transport.close()

loop = asyncio.get_event_loop()
# Each client connection will create a new protocol instance
first_message = ""
coro = loop.create_server(lambda: ChatProtocol(message, loop, first_message), '127.0.0.1', 8888)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
