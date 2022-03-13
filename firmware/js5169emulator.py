import asyncio
import serial
import struct


def calcCRC(data):
    res = 0
    for b in data:
        res ^= b
    
    return res

def sendMessage(ser, msgtype, data):
    # Message header and data
    msg = struct.pack("<BB", len(data) + 2, msgtype)
    msg += data
    msg += calcCRC(msg  ).to_bytes(1, 'big')
    
    print("Sending: " + ' '.join('{:02x}'.format(x) for x in msg))
    ser.write(msg)



def getChipId(ser, req):
    print("MESSAGE: Get Chip ID")
    
    resp = struct.pack('>BI', 0, 0x0000b686)
    sendMessage(ser, 0x33, resp)


def emulateReadRAM(addr, len):
    if addr == 0x00000062:
        print("Reading bootloader version - emulating 42")
        return struct.pack("<I", 42)
    if addr == 0x01001570:
        print("Reading MAC address - returning 00:11:22:33:44:55:66:77:88")
        return struct.pack("<BBBBBBBB", 0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88)
    
    print("Attempt to read {} bytes at unknown address {:08x}".format(len, addr))
    return bytes(len)


def readRAM(ser, req):
    addr, len = struct.unpack("<IH", req)
    print("MESSAGE: Read RAM addr={:08x} len={:04x}".format(addr, len))

    resp = struct.pack('>B', 0)
    resp += emulateReadRAM(addr, len)
    sendMessage(ser, 0x20, resp)


def selectFlashType(ser, req):
    flash, addr = struct.unpack("<BI", req)
 
    status = 0 if flash == 8 else 0xff  #Emulating only internal flash
    print("MESSAGE: Select flash type {:02x} addr={:08x}  - status={:02x}".format(flash, addr, status))

    resp = struct.pack("<B", status)
    sendMessage(ser, 0x2d, resp)


def changeBaudRate(ser, req):
    br = struct.unpack("<B", req)
    print("MESSAGE: Change baud rate to " + str(br[0]))

    resp = struct.pack("<B", 0xff)
    sendMessage(ser, 0x28, resp)


def main():
    ser = serial.Serial('COM6', baudrate=38400, timeout=1)

    while True:
        data = ser.read(2)
        if not data:
            continue

        msglen, msgtype = struct.unpack('BB', data)
        print()
        print("Message length: " + str(msglen))
        print("Message type: {:02x}".format(msgtype))

        data = ser.read(msglen - 1)
        print("Received: " + "{:02x} {:02x} ".format(msglen, msgtype) + ' '.join('{:02x}'.format(x) for x in data))

        if msgtype == 0x32:
            getChipId(ser, data[:-1])
        elif msgtype == 0x1f:
            readRAM(ser, data[:-1])
        elif msgtype == 0x2c:
            selectFlashType(ser, data[:-1])
        elif msgtype == 0x27:
            changeBaudRate(ser, data[:-1])
        else:
            print("Unsupported message type: {:02x}".format(msgtype))


main()