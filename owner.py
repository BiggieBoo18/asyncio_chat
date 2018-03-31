import asyncio
import sys

class Owner(object):
    def __init__(self):
        self.members = {} # {"username":(ip, port)}

    @asyncio.coroutine
    def handle_echo(self, reader, writer):
        data     = yield from reader.read(100)
        command  = data.decode()
        peername = writer.get_extra_info('peername')

        # execute command
        yield from self.execute_command(writer, command, peername)

        print("Close the client socket")
        writer.close()

    def parse_command(self, command):
        parts = command.split(" ")
        return parts

    def search_member(self, username):
        return self.members.get(username)

    @asyncio.coroutine
    def write_message(self, parts, message):
        # search member
        info = self.search_member(parts[1])
        if info:
            addr, port = info
            connect = asyncio.open_connection(addr, port)
            remote_reader, remote_writer = yield from connect
            remote_writer.write(bytes(message, sys.getdefaultencoding()))
            yield from remote_writer.drain()
            remote_writer.close()

    @asyncio.coroutine
    def execute_command(self, writer, command, peername=None):
        parts = self.parse_command(command)
        if parts[0]=="join":   # join
            self.members[parts[1]] = (peername[0], 1819)
            yield from self.write_message(parts, "registered {}".format(peername))
            # connect = asyncio.open_connection("127.0.0.1", 8889)
            # remote_reader, remote_writer = yield from connect
            # remote_writer.write(bytes("registered {}".format(peername), sys.getdefaultencoding()))
            # yield from remote_writer.drain()
            # remote_writer.close()
        elif parts[0]=="send": # send
            if len(parts)<3:
                return None
            yield from self.write_message(parts, " ".join(parts[2:]))

    def main(self):
        loop = asyncio.get_event_loop()
        coro = asyncio.start_server(self.handle_echo, '', 1818, loop=loop)
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

if __name__ == "__main__":
    owner = Owner()
    owner.main()
