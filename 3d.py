from time import sleep,time
import sys
import threading
import getopt
import serial # python -m pip install pyserial
import serial.tools.list_ports

import mouse

COMMAND_TIMEOUT = 2
TIMEOUT = 5
newXYZ = False
newButtons = False
outAxisMap = (0,1,2)
polarityXYZ = (1,-1,-1)
polarityRXYZ = (1,-1,-1)
dominationRatio = 0
sensitivity = b'S' # Standard/Cubic
running = True
joystick = False
port = None
conn = None
description = "USB-Serial Controller"
lock = threading.Lock()
xyz = [0,0,0]
rxyz = [0,0,0]
buttons = 0
trimValue = 500
event = threading.Event()



class SerialSpaceMouse(object):
    def __init__(self,axisMap=(0,1,2),polarityXYZ=(1,1-1),polarityRXYZ=(1,1,-1),haveEscape=True,name="unknown"):
        self.axisMap = axisMap
        self.polarityXYZ = polarityXYZ
        self.polarityRXYZ = polarityRXYZ
        self.haveEscape = haveEscape
        self.name = name
        
    @staticmethod
    def get16(data,offset):
        val = (data[offset+1]&0xFF) | ((data[offset]&0xFF)<<8)
        if (val & 0x8000 == 0x8000):
            val = val-0x10000
        return val

        
def trim(x):
    if trimValue == 0:
        return x
    x &= 0xFFFF
    if x&0x8000:
        if (-x)&0xFFFF > trimValue: 
            return (-trimValue)&0xFFFF        
    else:
        if x > trimValue:
            return trimValue
    return x        
    
def haveResponse(r, startsWith=False):
    t0 = time()
    while time() < t0+COMMAND_TIMEOUT:
        conn.timeout = COMMAND_TIMEOUT
        line = conn.read_until(b'\r', len(r)+1)
        conn.timeout = TIMEOUT
        if ( startsWith and line.startsWith(r) ) or line == r + b'\r':
            return True
    return False
            
def confirmWrite(out, confirmation=None, startsWith=False):
    if confirmation is None:
        confirmation = out
    for i in range(3):
        conn.reset_input_buffer()
        conn.write(out+b'\r')
        if haveResponse(confirmation, startsWith=startsWith):
            print("Confirmed command "+out.decode())
            return
    raise serial.SerialException("Cannot confirm "+out.decode())
    
def persistentOpen():
    global conn,running
    conn = None
    print("Trying to open serial connection")
    while running and conn is None:
        try:
            if port is not None:
                print("Opening "+port)
                conn = serial.Serial(port=port,baudrate=9600,timeout=TIMEOUT)
            else:
                for p in serial.tools.list_ports.comports():
                    if p.description.lower().startswith(description.lower()):
                        print("Opening "+str(p))
                        conn = serial.Serial(port=p.device,baudrate=9600,timeout=TIMEOUT)
                        print("Opened")
                        break
            if conn is not None:
                sleep(1)
                conn.reset_input_buffer()
                print("Initializing serial connection to "+currentMouse.name)
                currentMouse.init()
                return
            sleep(0.5)
        except serial.SerialException as e:
            print("Error "+str(e))
            if conn is not None:
                try:
                    conn.close()
                except:
                    pass
            conn = None
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
            persistentOpen()
        except Exception as e:
            print(str(e))
    return None
    
class FLXOrX003(SerialSpaceMouse):
    def __init__(self,keyCommand=b'.',name="unknown"):
        super(FLXOrX003, self).__init__(axisMap=(0,2,1), polarityXYZ=(1,1,1), polarityRXYZ=(1,1,1),haveEscape=True,name=name)
        self.keyCommand = keyCommand

    def init(self):
        conn.write(b'\r')

    def processData(self,data):
        global buttons,xyz,rxyz,newXYZ,newButtons,lock,event
        if len(data) == 15 and data[0] == ord(b'D'):
            lock.acquire()
            xyz[self.axisMap[0]] = self.polarityXYZ[0]*FLX.get16(data, 3)
            xyz[self.axisMap[1]] = self.polarityXYZ[1]*FLX.get16(data, 5)
            xyz[self.axisMap[2]] = self.polarityXYZ[2]*FLX.get16(data, 7)
            rxyz[self.axisMap[0]] = self.polarityRXYZ[0]*FLX.get16(data, 9)
            rxyz[self.axisMap[1]] = self.polarityRXYZ[1]*FLX.get16(data, 11)
            rxyz[self.axisMap[2]] = self.polarityRXYZ[2]*FLX.get16(data, 13)
            if dominationRatio != 0:
                if (xyz[0]*xyz[0]+xyz[1]*xyz[1]+xyz[2]*xyz[2]) >= dominationRatio*dominationRatio*(rxyz[0]*rxyz[0]+rxyz[1]*rxyz[1]+rxyz[2]*rxyz[2]):
                    rxyz[0] = 0
                    rxyz[1] = 0
                    rxyz[2] = 0
                else:
                    xyz[0] = 0
                    xyz[1] = 0
                    xyz[2] = 0
            newXYZ = True
#            print("xyz", xyz, rxyz)
            event.set()
            lock.release()
        elif self.keyCommand == b'.' and len(data) == 3 and data[0] == ord(b'.'):
            b = (data[2]&0xFF) | (data[1]&0xFF)<<8
            b = ((b&0b111111) | ((b&~0b1111111)>>1)) & 0b111111111111;
            lock.acquire()
            buttons = ((b >> 9) | (b << 3)) & 0b111111111111
            newButtons = True
            print("buttons1", buttons)
            event.set()
            lock.release()        
        elif self.keyCommand != b'.' and len(data) == 3 and data[0] == ord(self.keyCommand):
            b = data[1]&0xFF
            lock.acquire()
            buttons = b
            newButtons = True
            print("buttons2", buttons)
            event.set()
            lock.release()        
        
class FLX(FLXOrX003):
    def __init__(self):
        super(FLX, self).__init__(keyCommand=b'.',name="SpaceBall 4000/5000FLX")
        
    def init(self):
        super(FLX, self).init()
        confirmWrite(b"P20")
        confirmWrite(b"Y"+sensitivity)
        confirmWrite(b"A271006", b"a271006E")
        confirmWrite(b"M")
        conn.write(b'BcC\r')
        # confirmWrite(b"BcC")
        

def serialLoop():
    global conn,running
    overflow = False
    buffer = bytearray()
    escape = False
    persistentOpen()
    while running:
        c = persistentRead()
        if not running:
            break
        if c == b'\r':
            if len(buffer):
                currentMouse.processData(buffer)
                buffer = bytearray()
            continue         
        if currentMouse.haveEscape:
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
            

        
currentMouse = FLX()


        
opts, args = getopt.getopt(sys.argv[1:], "hjp:ld:cm:D:", ["help", "joystick", "port=", "list-ports", "description=", "cubic-mode", "max=", "dominance="])
i = 0
while i < len(opts):
    opt,arg = opts[i]
    if opt in ('-h', '--help'):
        print("""python 3d.py [options]\n
-h --help                   this information
-j --joystick               HID joystick mode 
-l --list-ports             list serial ports
-c --cubic                  cubic sensitivity mode
-mMAX   --max=MAX           set maximum value for all axes
-Dratio --dominance=ratio   only translation or rotation depending on translation to rotation ratio
-pCOMx  --port=COMx         COM  SpaceBall port
-ddesc  --description=desc  description of COM port device starts with desc""")
        sys.exit(0)
    elif opt in ('-j', '--joystick'):
        joystick = True
        outAxisMap = (0,2,1)
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
        sensitivity = b'C'   
    elif opt in ('-m', '--max'):
        trimValue = int(arg)
    elif opt in ('-D', '--dominance'):
        dominationRatio = float(arg)
    i += 1


        
t1 = threading.Thread(target=serialLoop)
t1.daemon = True
t1.start()

sentReport = False
stopped = False

print("Press ctrl-c to exit")

x=0
y=0
subPxX=0.0 
subPxY=0.0
delay = 0.01
divideX = 50
divideY = divideX

while True: 
  sleep(delay)
  lock.acquire()
  x=xyz[0]
  y=-xyz[1]
  
  # print (">>>", x, y)
  
  # move mouse around, but keep track of sub-pixels to be able to have slow movements
  subPxX += x/divideX
  subPxY += y/divideY  
  mouse.move(int(subPxX), int(subPxY), absolute=False )
  subPxX -= int(subPxX)
  subPxY -= int(subPxY)
  
  lock.release()

