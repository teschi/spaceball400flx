from __future__ import print_function
import builtins
import atexit
import datetime
import struct
from time import sleep,time
import sys
import threading
import getopt
import serial
import serial.tools.list_ports
import subprocess
import ctypes, sys, os
import uninstall
import signal

noLaunch = False
noAdmin = False
sensitivity = b'S' # Standard/Cubic
running = True
joystick = False
port = None
conn = None
description = "USB-SERIAL CH340"
lock = threading.Lock()
xyz = [0,0,0]
rxyz = [0,0,0]
buttons = 0
newButtons = False
newXYZ = False
newRXYZ = False
trimValue = 32768
forceVendorID = None
forceProductID = None
usbip = "usbip.exe"
event = threading.Event()

builtins.USBIP_VERSION = 273 # 273 for the unsigned patched driver and 262 for the old signed driver

opts, args = getopt.getopt(sys.argv[1:], "u:m:P:V:chljp:d:", ["no-admin", "no-launch", "usbip-directory=", "max", 
                    "product", "vendor", "cubic-mode", "list-ports","help","joystick","port=","description="])
i = 0
while i < len(opts):
    opt,arg = opts[i]
    if opt in ('-h', '--help'):
        print("""python 3d.py [options]\n
-h --help             this information
-j --joystick         HID joystick mode 
-l --list-ports       list serial ports
-c --cubic            cubic sensitivity mode
-mMAX --max=MAX       set maximum value for all axes
-VVID --vendor=VID    force vendor ID
-PPID --product=PID   force product ID
-pCOMx | --port=COMx         COM port of SpaceBall 4000
-ddesc | --description=desc  description of COM port device starts with desc""")
        sys.exit(0)
    elif opt in ('-j', '--joystick'):
        joystick = True
    elif opt in ('-p', '--port'):
        port = arg
        description = None
    elif opt in ('-l', '--list-ports'):
        for p in serial.tools.list_ports.comports():
            print(p.device+": "+p.description)
        sys.exit(0)
    elif opt in ('-d', '--description'):
        port = None
        description = arg
    elif opt in ('-c', '--cubic-mode'):
        sensitivity = b'S'
    elif opt in ('-V', '--vendor'):
        forceVendorID = int(arg, 16)
    elif opt in ('-P', '--product'):
        forceProductID = int(arg, 16)        
    elif opt in ('-m', '--max'):
        trimValue = int(arg)
    elif opt in ('-u', '--usbip-exe'):
        if arg[-1] == '/' or arg[-1] == ':':
            usbip = arg + "usbip.exe"
        elif arg[-1] == '':
            usbip = "usbip.exe"
        else:
            usbip = arg + "/" + "usbip.exe"
    elif opt in ('--no-admin',):
        noAdmin = True
    elif opt in ('--no-launch',):
        noLaunch = True
    i += 1

u = subprocess.Popen([usbip, "-v"], stdout=subprocess.PIPE)
builtins.USBIP_VERSION = 273 if u.stdout.readline().startswith(b"usbip for windows") else 262
u.stdout.close()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if builtins.USBIP_VERSION == 262 and not noAdmin:
    import platform
    if platform.architecture()[0] != '64bit' and platform.machine().endswith('64'):
        print("With the signed driver on Windows x64, please use a 64-bit Python interpreter.")
        exit(1)
    if not is_admin():
        def u(z):
            if sys.version_info[0] >= 3:
                return z
            else:
                return unicode(z)
        print("Relaunching as administrator.\nPlease make sure that to terminate the launched process you use ctrl-c in its window.")
        args = u(__file__)
        if len(sys.argv) >= 2:
            args += " " + " ".join((u('"' + arg + '"') for arg in sys.argv[1:]))
        ctypes.windll.shell32.ShellExecuteW(None, u("runas"), u(sys.executable), args, None, 1)
        sys.exit(0)
    
from USBIP import BaseStucture, USBDevice, InterfaceDescriptor, DeviceConfigurations, EndPoint, USBContainer, USBRequest    

def trim(x):
    if x&0x8000:
        if (-x)&0xFFFF > trimValue: 
            return (-trimValue)&0xFFFF        
    else:
        if x > trimValue:
            return trimValue
    return x        

def persistentOpen():
    global conn,running
    while running:
        try:
            if port is not None:
                print("Opening "+port)
                c = serial.Serial(port=port,baudrate=9600,timeout=5)
                print("Opened")
                return c
            for p in serial.tools.list_ports.comports():
                if p.description.lower().startswith(description.lower()):
                    print("Opening "+str(p))
                    c = serial.Serial(port=p.device,baudrate=9600)
                    print("Opened")
                    return c
            sleep(0.5)
        except serial.SerialException as e:
            print("Error "+str(e))
            sleep(0.5)

def persistentRead():
    global conn,running
    while running:
        try:
            if conn == None:
                raise serial.SerialException
            d = conn.read()
            if len(d) == 1:
                return d
        except serial.SerialException as e:
            print("Reconnecting after "+str(e))
            try:
                conn.close()
            except:
                pass
            conn = None
            sleep(0.5)
            conn = persistentOpen()
        except Exception as e:
            print(str(e))


# HID Configuration

descriptor = [
          0x05, 0x01,           #  Usage Page (Generic Desktop)  
          0x09, 0x04 if joystick else 0x08,           #  0x08: Usage (Multi-Axis)  
          0xa1, 0x01,           #  Collection (Application)  
          0xa1, 0x00,           # Collection (Physical)
          0x85, 0x01,           #  Report ID 
          #0x16, 0x0c, 0xfe,        #logical minimum (-500)
          #0x26, 0xf4, 0x01,        #logical maximum (500)
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
          #0x16,0x0c,0xfe,        #logical minimum (-500)
          #0x26,0xf4,0x01,        #logical maximum (500)
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
    vendorID = forceVendorID if forceVendorID is not None else (0x1EAF if joystick  else 0x46D)
    productID = forceProductID if forceProductID is not None else 0xc62b
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
        self.lastSend = -1
        self.seq = 0

    def generate_hid_report(self):
        return bytes(bytearray(descriptor))

    def handle_data(self, usb_req):
        global newXYZ, newRXYZ, newButtons, event, lock
        event.wait(0.5)
        return_val = b''
        lock.acquire()
        if newRXYZ:
            return_val = struct.pack("<BHHH", 2, trim(rxyz[0]),trim(rxyz[1]),trim(rxyz[2]))
            newRXYZ = False
        elif newButtons:
            return_val = struct.pack("BBBB", 3, buttons&0xFF, buttons>>8, 0)
            newButtons = False
        elif newXYZ:
            return_val = struct.pack("<BHHH", 1, trim(xyz[0]),trim(xyz[1]),trim(xyz[2]))
            newXYZ = False
            newRXYZ = True
        if newXYZ or newRXYZ or newButtons:
            event.set()
        else:
            event.clear()
        lock.release()
        self.send_usb_req(usb_req, return_val, status=(0 if return_val else 1))

    def handle_unknown_control(self, control_req, usb_req):
        if control_req.bmRequestType == 0x81:
            if control_req.bRequest == 0x6:  # Get Descriptor
                if control_req.wValue == 0x22:  # send initial report
                    print('send report descriptor')
                    self.send_usb_req(usb_req, self.generate_hid_report())

        if control_req.bmRequestType == 0x21:  # Host Request
            if control_req.bRequest == 0x0a:  # set idle
                pass
                # Idle

usb_Dev = USBHID()
usb_container = USBContainer()
usb_container.add_usb_device(usb_Dev)  # Supports only one device!
          
def init():
    if conn is None:
        print("not connected")
        return
        
    try:
        print("Init")
        conn.write(b"P20\rY" + sensitivity + b"\rAE\rA271006\rM\r") # update period 32ms, sensitivity Standard (vs. Cubic), auto-rezero Enable (D to disable), auto-rezero after 10,000 ms assuming 6 movement units
    except serial.SerialException:
        print("Failed init")
        
reinit = time()

def get16(data,offset):
    return (data[offset+1]&0xFF) | ((data[offset]&0xFF)<<8)

def processData(data):
    global reinit,buttons,xyz,rxyz,newXYZ,newRXYZ,newButtons,lock,event
    if len(data) == 15 and data[0] == ord(b'D'):
        reinit = time()
        lock.acquire()
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
        newXYZ = True
        event.set()
        lock.release()
    elif len(data) == 3 and data[0] == ord(b'.'):
        b = (data[2]&0xFF) | (data[1]&0xFF)<<8
        b = ((b&0b111111) | ((b&~0b1111111)>>1)) & 0b111111111111;
        lock.acquire()
        buttons = ((b >> 9) | (b << 3)) & 0b111111111111
        newButtons = True
        event.set()
        lock.release()

def serialLoop():
    global conn,running
    overflow = False
    buffer = bytearray()
    escape = False
    conn = persistentOpen()
    init()
    while running:
        c = persistentRead()
        if c == b'\r':
            if len(buffer):
                processData(buffer)
                buffer = bytearray()
            continue                
        if escape:
            if c == b'Q' or c == b'S' or c == b'M':
                c = bytes(bytearray((ord(c)&0b10111111,)))
            escape = False
        elif c == b'^':
            escape = True
            continue
        if len(buffer) < 256:
            buffer += c
            overflow = False
        else:
            overflow = True

def reconnectionLoop():
    global running
    while running:
        delta = time() - reinit
        if delta >= 5:
            init()
        else:
            sleep(5.01-delta)
        sleep(1)
        
def uninstallDriver():
    if uninstall.uninstallUSBHID(USBHID.vendorID, USBHID.productID):
        print("Success uninstalling driver")
    else:
        print("Failure uninstalling driver")
        sleep(10)

t1 = threading.Thread(target=serialLoop)
t1.daemon = True
t1.start()
t2 = threading.Thread(target=reconnectionLoop)
t2.daemon = True
t2.start()

def exitFunction():
    global running
    if running:
        print("Exiting...")
        running = False
        if builtins.USBIP_VERSION == 262:
            uninstallDriver()
        sys.exit(0)

atexit.register(exitFunction)

signal.signal(signal.SIGBREAK, lambda x,y: exitFunction())
signal.signal(signal.SIGINT, lambda x,y: exitFunction())

if not noLaunch:
    print("Starting "+usbip)
    subprocess.Popen([usbip, "-a", "localhost", "1-1"],creationflags=0x00000200)
    print("Press ctrl-c to exit")

usb_container.run()
