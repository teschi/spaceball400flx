from random import randint
import datetime
import struct
from time import sleep,time
from USBIP import BaseStucture, USBDevice, InterfaceDescriptor, DeviceConfigurations, EndPoint, USBContainer
import sys
import threading
import getopt
import serial
import serial.tools.list_ports

joystick = False
port = None
conn = None
description = "USB-SERIAL CH340"
xyz = [0,0,0]
rxyz = [0,0,0]
buttons = 0

def persistentOpen():
    while True:
        try:
            if port is not None:
                print("Opening "+port)
                c = serial.Serial(port=port,baudrate=9600)
                print("Opened")
                return c
            for p in serial.tools.list_ports.comports():
                print(p.device)
                if p.description.lower().startswith(description.lower()):
                    print("Opening "+str(p))
                    c = serial.Serial(port=p.device,baudrate=9600)
                    print("Opened")
                    return c
        except serial.SerialException as e:
            print("Error "+str(e))
            sleep(0.5)

def persistentRead():
    global conn
    while True:
        try:
            if conn == None:
                raise serial.SerialException
            return conn.read()
        except serial.SerialException as e:
            print("Reconnecting after "+str(e))
            try:
                conn.close()
            except:
                pass
            sleep(0.5)
            conn = persistentOpen()
        except Exception as e:
            print(str(e))

opts, args = getopt.getopt(sys.argv[1:], "hjp:d:", ["help","joystick","port=","description="])
i = 0
while i < len(opts):
    opt,arg = opts[i]
    if opt in ('-h', '--help'):
        print("""python 3d.py [options]\n
-h --help:     this information
-j --joystick: HID joystick mode
-pCOMx | --port=COMx: COM port of SpaceBall 4000
-ddesc | --description=desc: description of COM port device starts with desc""")
        sys.exit(0)
    elif opt in ('-j', '--joystick'):
        joystick = True
    elif opt in ('-p', '--port'):
        port = arg
        description = None
    elif opt in ('-d', '--description'):
        port = None
        description = arg
    i += 1

print("Joystick = "+str(joystick))        
        
# HID Configuration

descriptor = [
          0x05, 0x01,           #  Usage Page (Generic Desktop)  
          0x09, 0x04 if joystick else 0x08,           #  0x08: Usage (Multi-Axis)  
          0xa1, 0x01,           #  Collection (Application)  
          0xa1, 0x00,           # Collection (Physical)
          0x85, 0x01,           #  Report ID 
        #  0x16, 0x0c, 0xfe,        #logical minimum (-500)
        #  0x26, 0xf4, 0x01,        #logical maximum (500)
          0x36, 0x00, 0x80,              # Physical Minimum (-32768)
          0x46, 0xff, 0x7f,              #Physical Maximum (32767)
          0x09, 0x30,           #    Usage (X)  
          0x09, 0x31,           #    Usage (Y)  
          0x09, 0x32,           #    Usage (Z)  
          0x75, 0x10,           #    Report Size (16)  
          0x95, 0x03,           #    Report Count (3)  
          0x81, 0x02,           #    Input (variable,absolute)  
          0xC0,                 #  End Collection  
          0xa1, 0x00,            # Collection (Physical)
          0x85, 0x02,         #  Report ID 
        #  0x16,0x0c,0xfe,        #logical minimum (-500)
        #  0x26,0xf4,0x01,        #logical maximum (500)
          0x36,0x00,0x80,              # Physical Minimum (-32768)
          0x46,0xff,0x7f,              #Physical Maximum (32767)
          0x09, 0x33,           #    Usage (RX)  
          0x09, 0x34,           #    Usage (RY)  
          0x09, 0x35,           #    Usage (RZ)  
          0x75, 0x10,           #    Report Size (16)  
          0x95, 0x03,           #    Report Count (3)  
          0x81, 0x02,           #    Input (variable,absolute)  
          0xC0,                           #  End Collection     
          
          0xa1, 0x00,            # Collection (Physical)
          0x85, 0x03,         #  Report ID 
          0x15, 0x00,           #   Logical Minimum (0)  
          0x25, 0x01,           #    Logical Maximum (1) 
          0x75, 0x01,           #    Report Size (1)  
          0x95, 24,           #    Report Count (24) 
          0x05, 0x09,           #    Usage Page (Button)  
          0x19, 1,           #    Usage Minimum (Button #1)  
          0x29, 24,           #    Usage Maximum (Button #24)  
          0x81, 0x02,           #    Input (variable,absolute)  
          0xC0,
          0xC0,]


class HIDClass(BaseStucture):
    _fields_ = [
        ('bLength', 'B', 9),
        ('bDescriptorType', 'B', 0x21),  # HID
        ('bcdHID', 'H'),
        ('bCountryCode', 'B'),
        ('bNumDescriptors', 'B'),
        ('bDescriptorType2', 'B'),
        ('bDescriptionLengthLow', 'B'),
        ('bDescriptionLengthHigh', 'B'),
    ]


hid_class = HIDClass(bcdHID=0x0101,  
                     bCountryCode=0x0,
                     bNumDescriptors=0x1,
                     bDescriptorType2=0x22,  # Report
                     bDescriptionLengthLow=len(descriptor)&0xFF,
                     bDescriptionLengthHigh=len(descriptor)>>8,
                     )  


interface_d = InterfaceDescriptor(bAlternateSetting=0,
                                  bNumEndpoints=1,
                                  bInterfaceClass=3,  # class HID
                                  bInterfaceSubClass=1,
                                  bInterfaceProtocol=2,
                                  iInterface=0)

end_point = EndPoint(bEndpointAddress=0x81,
                     bmAttributes=0x3,
                     wMaxPacketSize=8000,  # Little endian
                     bInterval=0xFF)  # interval to report


configuration = DeviceConfigurations(wTotalLength=0x2200,
                                     bNumInterfaces=0x1,
                                     bConfigurationValue=0x1,
                                     iConfiguration=0x0,  # No string
                                     bmAttributes=0x80,  # valid self powered
                                     bMaxPower=50)  # 100 mah current

interface_d.descriptions = [hid_class]  # Supports only one description
interface_d.endpoints = [end_point]  # Supports only one endpoint
configuration.interfaces = [interface_d]   # Supports only one interface


class USBHID(USBDevice):
    vendorID = 0x1EAF if joystick else 0x46D
    productID = 0xc62b
    bcdDevice = 0x200
    bcdUSB = 0x200
    bNumConfigurations = 0x1
    bNumInterfaces = 0x1
    bConfigurationValue = 0x1
    configurations = []
    bDeviceClass = 0x0
    bDeviceSubClass = 0x0
    bDeviceProtocol = 0x01
    configurations = [configuration]  # Supports only one configuration

    def __init__(self):
        USBDevice.__init__(self)
        self.start_time = datetime.datetime.now()

    def generate_hid_report(self):
        usage = 0x04 if joystick else 0x08
        
                
        return_val = ''
        for val in descriptor:
            return_val+=chr(val)
        print(len(return_val))
        return return_val

    def handle_data(self, usb_req):
        if usb_req.seqnum % 3 == 0:
            return_val = struct.pack(">BHHH", 1, xyz[0],xyz[1],xyz[2])
            self.send_usb_req(usb_req, return_val)
        elif usb_req.seqnum % 3 == 1:
            return_val = struct.pack(">BHHH", 2, rxyz[0],rxyz[1],rxyz[2])
            self.send_usb_req(usb_req, return_val)        
        elif usb_req.seqnum % 3 == 2:
            return_val = struct.pack("BBBB", 3, buttons & 0xFF,buttons >> 8, 0)
            self.send_usb_req(usb_req, return_val)        

    def handle_unknown_control(self, control_req, usb_req):
        if control_req.bmRequestType == 0x81:
            if control_req.bRequest == 0x6:  # Get Descriptor
                if control_req.wValue == 0x22:  # send initial report
                    print 'send initial report'
                    self.send_usb_req(usb_req, self.generate_hid_report())

        if control_req.bmRequestType == 0x21:  # Host Request
            if control_req.bRequest == 0x0a:  # set idle
                print 'Idle'
                # Idle
                pass

buffer = b''      
overflow = False
escape = False
          
def init():
    try:
        print("Init")
        conn.write("P20\rYS\rAE\rA271006\rM\r") # update period 32ms, sensitivity Standard (vs. Cubic), auto-rezero Enable (D to disable), auto-rezero after 10,000 ms assuming 6 movement units
    except serial.SerialException:
        print("Failed init")
        pass
        
reinit = time()

def get16(data,offset):
    return (ord(data[offset])&0xFF) | ((ord(data[offset+1])&0xFF)<<8)

def processData(data):
    global reinit,buttons,xyz,rxyz
    if len(data) == 15 and data[0] == 'D':
        reinit = time()
        if joystick:
            xyz[0] = get16(data, 3);
            xyz[2] = get16(data, 5);
            xyz[1] = 0xFFFF&-get16(data, 7);
            rxyz[0] = get16(data, 9);
            rxyz[2] = get16(data, 11);
            rxyz[1] = 0xFFFF&-get16(data, 13);
        else:
            xyz[0] = get16(data, 3)
            xyz[1] = get16(data, 5);
            xyz[2] = 0xFFFF&-get16(data, 7)
            rxyz[0] = get16(data, 9)
            rxyz[1] = get16(data, 11)
            rxyz[2] = 0xFFFF&-get16(data, 13)
    elif len(data) == 3 and data[0] == '.':
        b = (ord(data[2])&0xFF) | (ord(data[1])&0xFF)<<8
        b = ((b&0b111111) | ((b&~0b1111111)>>1)) & 0b111111111111;
        buttons = ((b >> 9) | (b << 3)) & 0b111111111111

def serialLoop():
    global buffer
    global conn
    conn = persistentOpen()
    init()
    while True:
        c = persistentRead()
        if escape:
            if c == b'Q' or c == b'S' or c == b'M':
                c &= 0b10111111
        else:
            if c == b'\r':
                processData(buffer)
                buffer = ''
                continue
        if len(buffer) < 256:
            buffer += c
            overflow = False
        else:
            overflow = True

def reconnectionLoop():
    while True:
        delta = time() - reinit
        if delta >= 5:
            init()
        sleep(delta+0.01)

usb_Dev = USBHID()
usb_container = USBContainer()
usb_container.add_usb_device(usb_Dev)  # Supports only one device!
threading.Thread(target=serialLoop).start()
threading.Thread(target=reconnectionLoop).start()
#threading.Thread(target=usb_container.run).start()
usb_container.run()

# Run in cmd: usbip.exe -a 127.0.0.1 "1-1"
