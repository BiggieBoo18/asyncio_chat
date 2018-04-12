import time
import logging

from logzero import logger
from twisted.internet import reactor, task

from neo.Network.NodeLeader import NodeLeader
from neo.Core.Blockchain import Blockchain
from neo.Implementations.Blockchains.LevelDB.LevelDBBlockchain import LevelDBBlockchain
from neo.Implementations.Notifications.LevelDB.NotificationDB  import NotificationDB
from neo.Settings import settings, PrivnetConnectionError

from neo.Network.api.decorators import json_response, gen_authenticated_decorator, catch_exceptions
from neo.contrib.smartcontract import SmartContract
from neo.bin.prompt import PromptInterface

# Set the hash of your contract here:
# SMART_CONTRACT_HASH = "6537b4bd100e514119e3a7ab49d520d20ef2c2a4"

# Internal: setup the smart contract instance
# smart_contract = SmartContract(SMART_CONTRACT_HASH)

def do_send(cli, wallet_path, asset_name, address, amount):
    cli.do_open(['wallet', wallet_path])
    cli.show_wallet([])
    cli.do_send([asset_name, address, amount])
    time.sleep(1)
    reactor.stop()

#
# Main method which starts everything up
#
def main(wallet_path, asset_name, address, amount):
    # settings
    # settings.set_loglevel(logging.DEBUG) # for debug
    settings.set_log_smart_contract_events(False)
    # connect privatenet
    try:
        settings.setup_privnet(True)
    except PrivnetConnectionError as e:
        logger.error(str(e))
        return
    

    # Setup the blockchain
    blockchain = LevelDBBlockchain(settings.chain_leveldb_path)
    Blockchain.RegisterBlockchain(blockchain)
    dbloop = task.LoopingCall(Blockchain.Default().PersistBlocks)
    dbloop.start(.1)

    # Try to set up a notification db
    if NotificationDB.instance():
        NotificationDB.instance().start()
    cli = PromptInterface()
    NodeLeader.Instance().Start()

    # owner.wlt:   AK2nJJpJr6o664CWJKi1QRXjqeic2zRp8y
    # client1.wlt: AdmA3mV2Rw3myD5YuXCNsdJ96eg6dV8acE
    # client2.wlt: APCh64GYzV1oQxjrWPTRwZjpTgqaaWz4Jc
    reactor.callInThread(do_send, cli, wallet_path, asset_name, address, amount)
    reactor.run()
    # After the reactor is stopped, gracefully shutdown the database.
    cli.do_close_wallet()
    NotificationDB.close()
    Blockchain.Default().Dispose()
    NodeLeader.Instance().Shutdown()

if __name__ == "__main__":
    asset_name = "gas"
    address    = "AdmA3mV2Rw3myD5YuXCNsdJ96eg6dV8acE"
    amount     = "100"
    main(asset_name, address, amount)
