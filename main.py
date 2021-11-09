#!/usr/bin/env python3

import os
from tesla_powerwall import Powerwall
import docker
import time

POWERWALL_URL = ""  # PowerWall Gateway address goes here
EMAIL = ""  # email address that you use to login into the gateway
PASSWD = ""  # password that you use to log into the gateway
WALLET_ADDRESS = "35kwhvhyfnVnGdoWdyLqrtaHeY7RYByPfW"  # mining wallet address
MINING_URL = (
    "stratum+tcp://daggerhashimoto.usa-east.nicehash.com:3353"  # Mining url
)
# lowest battery charge where mining will start
BATTERY_CHARGE_TO_START_MINING = 50
# how often to check is battery level allows mining or not in seconds
HOW_OFTEN_TO_CHECK = 1800


def init():
    # initialize powerwall object and api
    powerwall = Powerwall(
        endpoint=POWERWALL_URL,
        timeout=10,
        http_session=None,
        verify_ssl=False,
        disable_insecure_warning=True,
        pin_version=None,
    )
    powerwall.login(PASSWD, EMAIL)

    api = powerwall.get_api()

    return powerwall, api


class Miner:
    def __init__(self, client, wallet_address, mining_url):

        self.wallet_address = wallet_address
        self.mining_url = mining_url
        self.client = client
        return

    def start_miner(self, client):
        env_vars = {
            "WALLET": WALLET_ADDRESS,
            "SERVER": MINING_URL,
            "WORKER": "Rig",
            "ALGO": "ethash",
        }
        try:
            client.containers.run(
                # change as needed for your graphics card
                "ptrfrll/nv-docker-trex:cuda11",
                detach=True,
                runtime="nvidia",
                name="trex-miner",
                ports={4067: 4067},
                environment=env_vars,
            )
        except os.error as e:
            client.containers.get("trex-miner").restart()
        return

    def stop_miner(self, client):
        trex = client.containers.get("trex-miner")
        trex.stop()
        return

    def is_running(self):
        try:
            client.containers.get("trex-miner")
            return True
        except os.error:
            return False


if __name__ == "__main__":
    powerwall, api = init()

    client = docker.from_env()

    miner = Miner(client, WALLET_ADDRESS, MINING_URL)

    miner.start_miner(client)

    while True:
        # powerwall charge is satisfactory, start mining
        if not miner.is_running() and (
            api.get_system_status_soe()["percentage"]
            > BATTERY_CHARGE_TO_START_MINING
        ):
            miner.start_miner(client)
            print("miner is running or will be startedstart")
        # powerwall charge is too low, shut off mining
        elif miner.is_running() and (
            api.get_system_status_soe()["percentage"]
            < BATTERY_CHARGE_TO_START_MINING
        ):
            print("stopping miner")
            miner.stop_miner(client)
        # try again in ten minutes
        time.sleep(HOW_OFTEN_TO_CHECK)
