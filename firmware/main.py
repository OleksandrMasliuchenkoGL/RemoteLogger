import time
import uasyncio as asyncio
import machine
import network
import webrepl

class RemoteLogger():
    def __init__(self):
        self.writer = None


    async def connect(self, server, port):
        print("Openning connection to " + server + ":" + str(port)) 
        _, self.writer = await asyncio.open_connection(server, int(port))
        await self.writer.drain()


    async def log(self, msg):
        # TODO: Print only if main UART is used
        print(msg)

        try:
            self.writer.write(msg.encode())
            await self.writer.drain()
        except Exception as e:
            halt("Unable to send a message to log server: " + str(e))


logger = RemoteLogger()


fastBlinking=True
async def blink():
    led = machine.Pin(2, machine.Pin.OUT, value = 1)

    while True:
        led(not led()) # Fast blinking if no connection
        await asyncio.sleep_ms(1000 if not fastBlinking else 150)

def readConfig():
    print("Reading configuration...") 

    config = {}
    with open("config.txt") as config_file:
        config['ssid'] = config_file.readline().rstrip()
        config['wifi_pw'] = config_file.readline().rstrip()
        config['server'] = config_file.readline().rstrip()
        config['port'] = config_file.readline().rstrip()

    return config


def halt(err):
    print("Fatal error: " + err)
    for i in range (5, 0, -1):
        print("The app will reboot in {} seconds".format(i))
        time.sleep(1)

    machine.reset()


async def connectWiFi(ssid, passwd, timeout=10):
    global fastBlinking

    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    print("Connecting to WiFi: " + ssid)
    sta.connect(ssid, passwd)

    duration = 0
    while not sta.isconnected():
        if duration >= timeout:
            halt("WiFi connection failed. Status=" + str(sta.status()))

        print("Still connecting... Status=" + str(sta.status()))
        duration += 1
        await asyncio.sleep(1)

    print("Connected to WiFi. ifconfig="+str(sta.ifconfig()))
    fastBlinking = False


async def main():
    config = readConfig()
    print("Configuration: " + str(config))

    asyncio.create_task(blink())

    await connectWiFi(config['ssid'], config['wifi_pw'])
    await logger.connect(config['server'], config['port'])
    webrepl.start()

    asyncio.create_task(blink())

    while True:
        await logger.log("Test")
        await asyncio.sleep(5)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
