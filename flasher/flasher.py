import serial
import struct


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

    msglen, msgtype = struct.unpack('BB', data)
    trace("Response type={:02x} length={}".format(msgtype, msglen))
    data = ser.read(msglen - 1)
    check(data, "Incorrect response from device")

    trace("Received: " + "{:02x} {:02x} ".format(msglen, msgtype) + ' '.join('{:02x}'.format(x) for x in data))

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


def eraseFlash(ser):
    print("Erasing internal flash")
    resp = sendRequest(ser, 0x07, b'')
    status = struct.unpack("<B", resp)
    check(status[0] == 0, "Wrong status on erase internal flash")


def main():
    ser = serial.Serial('COM5', baudrate=38400, timeout=1)

    getChipId(ser)
    setFlashType(ser)
    eraseFlash(ser)


main()