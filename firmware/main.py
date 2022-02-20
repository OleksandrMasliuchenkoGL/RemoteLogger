import uasyncio as asyncio

def readConfig():
    print("Reading configuration...") 

    config = {}
    with open("config.txt") as config_file:
        config['ssid'] = config_file.readline().rstrip()
        config['wifi_pw'] = config_file.readline().rstrip()
        config['server'] = config_file.readline().rstrip()
        config['port'] = config_file.readline().rstrip()

    return config


async def main():
    config = readConfig()
    print("Configuration: " + str(config))

    while True:
        await asyncio.sleep(5)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
