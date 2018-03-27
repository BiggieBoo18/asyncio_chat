import asyncio
import sys
from random import randint


async def random_hit(n_upper, loop=None):
    if loop is None:
        loop = asyncio.get_event_loop()

    def _callback(future):
        print("DONE!")
    future = loop.create_future()
    future.add_done_callback(_callback)

    def _random_hit(n_upper, count):
        value = randint(1, n_upper)
        if value == n_upper:
            print("Hit!")
            future.set_result(count)
        else:
            print("Not yet.")
            count += 1
            loop.call_soon(_random_hit, n_upper, count)

    loop.call_soon(_random_hit, n_upper, 1)
    return (await future)


def get_input():
    try:
        n = int(sys.argv[1])
    except IndexError:
        print("Input an integer.")
        n = int(input())
    if n < 1:
        n = 1
    return n

n = get_input()
loop = asyncio.get_event_loop()
result = loop.run_until_complete(random_hit(n))
print(result)
