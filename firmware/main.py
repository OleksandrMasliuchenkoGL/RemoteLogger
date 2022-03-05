import time
import uio as io
import usys as sys
import uasyncio as asyncio
import machine
import network
import webrepl
import uos


def singleton(cls):
    instance = None
    def getinstance(*args, **kwargs):
        nonlocal instance
        if instance is None:
            instance = cls(*args, **kwargs)
            return instance
        return instance(*args, **kwargs)
    return getinstance


class UartMode:
    USB_UART = 0
    LOGGING_UART = 1
    PROGRAMMING_UART = 2


@singleton
class UartManager:
    UART_CFG = {
        UartMode.USB_UART: {'baudrate': 115200},
        UartMode.LOGGING_UART: {'baudrate': 115200, 'tx': machine.Pin(15), 'rx': machine.Pin(13), 'rxbuf': 2048},
        UartMode.PROGRAMMING_UART: {'baudrate': 38400, 'tx': machine.Pin(15), 'rx': machine.Pin(13), 'rxbuf': 256}
    }

    def __init__(self, mode = None):
        self.mutex = asyncio.Lock()
        self.mode = None
        self.switchUart(mode)


    def __call__(self, mode):
        self.switchUart(mode)
        return self


    def switchUart(self, mode):
        if self.mode != mode:
            cfg = self.UART_CFG[mode]
            self.uart = machine.UART(0, **cfg)
            self.mode = mode


    def getUart(self):
        return self.uart


    async def __aenter__(self):
        await self.mutex.acquire()
        return self.getUart()


    async def __aexit__(self, *args):
        self.mutex.release()


class RemoteLogger():
    def __init__(self):
        self.writer = None


    async def connect(self, server, port):
        print("Openning connection to " + server + ":" + str(port)) 
        _, self.writer = await asyncio.open_connection(server, int(port))
        await self.writer.drain()


    async def log(self, msg):
        print(msg)

        self.writer.write((msg+'\n').encode())
        await self.writer.drain()


logger = RemoteLogger()



def halt(err):
    print("Swapping back to USB UART")
    uart = UartManager(UartMode.USB_UART).getUart()
    uos.dupterm(uart, 1)

    print("Fatal error: " + err)
    for i in range (5, 0, -1):
        print("The app will reboot in {} seconds".format(i))
        time.sleep(1)

    machine.reset()


def coroutine(fn):
    async def coroutineWrapper():
        try:
            await fn()
        except Exception as e:
            buf = io.StringIO()
            sys.print_exception(e, buf)
            halt(buf.getvalue())

    return coroutineWrapper


fastBlinking=True
@coroutine
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


def swapUART():
    print("Swapping UART to alternate pins. Disconnecting REPL on UART")
    uos.dupterm(None, 1)

    # uart = machine.UART(0, 115200, tx=machine.Pin(15), rx=machine.Pin(13), rxbuf=2048)
    # return uart

@coroutine
async def uart_listener():
    for i in range(15, 0, -1):
        await logger.log("Starting UART logging in " + str(i) + " seconds")
        await asyncio.sleep(1)

    while True:
        async with UartManager(UartMode.LOGGING_UART) as uart:
            reader = asyncio.StreamReader(uart)
            data = yield from reader.readline()
            line = data.decode().rstrip()
            await logger.log("UART message: " + line)


@coroutine
async def main():
    config = readConfig()
    print("Configuration: " + str(config))

    asyncio.create_task(blink())

    await connectWiFi(config['ssid'], config['wifi_pw'])
    await logger.connect(config['server'], config['port'])
    webrepl.start()
    swapUART()
    asyncio.create_task(uart_listener())

    i = 0
    while True:
        await logger.log("Test " + str(i))
        i += 1
        await asyncio.sleep(5)


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
