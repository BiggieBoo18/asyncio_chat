import asyncio
import sys

@asyncio.coroutine
def input_command():
    command = input("press command>> ")
    return command

@asyncio.coroutine
def tcp_echo_client(loop):
    reader, writer = yield from asyncio.open_connection('127.0.0.1', 8888, loop=loop)

    command = yield from input_command()
    # print('Send: %r' % command)
    writer.write(bytes(command, sys.getdefaultencoding()))
    # writer.write(message.encode())

    data = yield from reader.read(100)
    print('Received: %r' % data.decode())

    # print('Close the socket')
    writer.close()

loop = asyncio.get_event_loop()
while True:
    loop.run_until_complete(tcp_echo_client(loop))
loop.run_forever()
loop.close()
