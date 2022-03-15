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


def main():
    ser = serial.Serial('COM5', baudrate=38400, timeout=1)

    getChipId(ser)
    mac = getMAC(ser)
    print("Device MAC address: " + ':'.join('{:02x}'.format(x) for x in mac))

    setFlashType(ser)
    eraseFlash(ser)

    reset(ser)

main()