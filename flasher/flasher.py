import serial
import struct
import argparse
import socket


class Uart2SocketWrapper:
    def __init__(self, sock):
        self.sock = sock

    def write(self, data):
        self.sock.sendall(data)

    def read(self, len):
        return self.sock.recv(len)


def check(cond, errmsg):
    if not cond:
        raise RuntimeError(errmsg)


def trace(msg):
    enabled = False
    if enabled:
        print(msg)


def calcCRC(data):
    res = 0
    for b in data:
        res ^= b
    
    return res

def sendRequest(ser, msgtype, data):
    # Prepare the message
    msg = struct.pack("<BB", len(data) + 2, msgtype)
    msg += data
    msg += calcCRC(msg  ).to_bytes(1, 'big')
    
    # Send the message
    trace("Sending: " + ' '.join('{:02x}'.format(x) for x in msg))
    ser.write(msg)

    # Wait for response
    data = ser.read(2)
    check(data, "No response from device")

    resplen, resptype = struct.unpack('BB', data)
    trace("Response type={:02x} length={}".format(resptype, resplen))
    data = ser.read(resplen - 1)
    check(data, "Incorrect response from device")

    trace("Received: " + "{:02x} {:02x} ".format(resplen, resptype) + ' '.join('{:02x}'.format(x) for x in data))
    check(msgtype + 1 == resptype, "Incorrect response type")   # Looks like request and response type numbers are next to each other

    return data[:-1]


def getChipId(ser):
    print("Requesting Chip ID")
    resp = sendRequest(ser, 0x32, b'')
    status, chipId = struct.unpack('>BI', resp)
    print("Received chip ID {:08x} (Status={:02x})".format(chipId, status))

    check(status == 0, "Wrong status on get Chip ID request")
    check(chipId == 0x0000b686, "Unsupported chip ID")   # Support only JN5169 for now
    return chipId


def setFlashType(ser):
    print("Selecting internal flash")
    req = struct.pack("<BI", 8, 0x00000000) # Select internal flash (8) at addr 0x00000000
    resp = sendRequest(ser, 0x2c, req)
    status = struct.unpack("<B", resp)
    check(status[0] == 0, "Wrong status on select internal flash")


def getMAC(ser):
    print("Requesting device MAC address")
    req = struct.pack("<IH", 0x01001570, 8) # Mac address is located at 0x01001570
    resp = sendRequest(ser, 0x1f, req)
    check(resp[0] == 0, "Wrong status on read MAC address")
    return [x for x in resp[1:8]]


def eraseFlash(ser):
    print("Erasing internal flash")
    resp = sendRequest(ser, 0x07, b'')
    status = struct.unpack("<B", resp)
    check(status[0] == 0, "Wrong status on erase internal flash")


def reset(ser):
    print("Reset target device")
    resp = sendRequest(ser, 0x14, b'')
    status = struct.unpack("<B", resp)
    check(status[0] == 0, "Wrong status on reset device")


def flashWrite(ser, addr, chunk):
    print("Writing flash at addr {:08x}".format(addr))
    req = struct.pack("<I", addr)
    req += chunk
    resp = sendRequest(ser, 0x09, req)

    check(resp[0] == 0, "Wrong status on write flash command")


def flashFirmware(ser, firmware):
    for addr in range(0, len(firmware), 0x80):
        chunklen = len(firmware) - addr
        if chunklen > 0x80:
            chunklen = 0x80

        flashWrite(ser, addr, firmware[addr:addr+chunklen])

def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Flash NXP JN5169 device")
    parser.add_argument("-p", "--port", help="Serial port")
    parser.add_argument("-s", "--server", help="Remote flashing server")
    parser.add_argument("-f", "--file", required=True, help="Firmware file to flash")
    args = parser.parse_args()

    # Validate parameters
    if not args.port and not args.server:
        print("Please specify either serial port or remote flashing server")
        sys.exit(1)

    if args.port and args.server:
        print("You can use either serial port or remote flashing server")
        sys.exit(1)

    # Load a file to flash
    with open(args.file, "rb") as f:
        firmware = f.read()
    check(firmware[0:4] == b'\x0f\x03\x00\x0b', "Incorrect firmware format")
    firmware = firmware[4:]


    # Open connection
    if args.port:
        ser = serial.Serial(args.port, baudrate=38400, timeout=1)
    if args.server:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((args.server, 5169))
        ser = Uart2SocketWrapper(sock)

    # Prepare the target device
    getChipId(ser)
    mac = getMAC(ser)
    print("Device MAC address: " + ':'.join('{:02x}'.format(x) for x in mac))

    # Flash the firmware
    setFlashType(ser)
    eraseFlash(ser)
    flashFirmware(ser, firmware)
    reset(ser)

main()