from random import randint
import datetime
import struct
from time import sleep
from USBIP import BaseStucture, USBDevice, InterfaceDescriptor, DeviceConfigurations, EndPoint, USBContainer

joystick = True

# Emulating USB mouse

# HID Configuration

descriptor =         arr = [
          0x05, 0x01,           #  Usage Page (Generic Desktop)  
          0x09, 0x04 if joystick else 0x08,           #  0x08: Usage (Multi-Axis)  
          0xa1, 0x01,           #  Collection (Application)  
          0x09, 0x01,		    #   Usage (Pointer)
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
    productID = 0xc644
    bcdDevice = 0x0
    bcdUSB = 0x0
    bNumConfigurations = 0x1
    bNumInterfaces = 0x1
    bConfigurationValue = 0x1
    configurations = []
    bDeviceClass = 0x0
    bDeviceSubClass = 0x0
    bDeviceProtocol = 0x0
    configurations = [configuration]  # Supports only one configuration

    def __init__(self):
        USBDevice.__init__(self)
        self.start_time = datetime.datetime.now()

    def generate_hid_report(self):
        usage = 0x04 if joystick else 0x08
        
                
        return_val = ''
        for val in arr:
            return_val+=chr(val)
        print(len(return_val))
        return return_val

    def handle_data(self, usb_req):
#        return_val = struct.pack("<Bhhh", 1,randint(-500,500),randint(-500,500),randint(-500,500))
#        print(len(return_val))
#        self.send_usb_req(usb_req, return_val)
#        return_val = struct.pack("<Bhhh", 2,randint(-500,500),randint(-500,500),randint(-500,500))
#        print(len(return_val))
#        self.send_usb_req(usb_req, return_val)
#        sleep(0.05)
        return_val = struct.pack("<BBBB", randint(0,255), 3, 3, 3)
        print(return_val)
        print(len(return_val))
        self.send_usb_req(usb_req, return_val)
        sleep(0.5)


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


usb_Dev = USBHID()
usb_container = USBContainer()
usb_container.add_usb_device(usb_Dev)  # Supports only one device!
usb_container.run()

# Run in cmd: usbip.exe -a 127.0.0.1 "1-1"