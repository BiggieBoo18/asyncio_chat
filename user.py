import asyncio
import sys
import time

@asyncio.coroutine
def input_command(loop):
    @asyncio.coroutine
    def _input_command():
        return input("press command>> ")
    command =  yield from _input_command()
    if command!="":
        reader, writer = yield from asyncio.open_connection("127.0.0.1", 1818, loop=loop)
        writer.write(bytes(command, sys.getdefaultencoding()))
        writer.close()

@asyncio.coroutine
def user_service(reader, writer):
    data = yield from reader.read(100)
    print("recieved:", data.decode())
    writer.close()

loop   = asyncio.get_event_loop()
coro   = asyncio.start_server(user_service, "", 1819, loop=loop)
server = loop.run_until_complete(coro)
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    while True:
        loop.run_until_complete(input_command(loop))
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()
