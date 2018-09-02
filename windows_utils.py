#! python
#
# (C) 2001-2016 Chris Liechti <cliechti@gmx.net>
# (C) 2018 Alexander Pruss
#
# SPDX-License-Identifier:    BSD-3-Clause

from __future__ import absolute_import

# pylint: disable=invalid-name,too-few-public-methods
import re
import ctypes
import platform
import msvcrt
from ctypes.wintypes import BOOL
from ctypes.wintypes import HWND
from ctypes.wintypes import DWORD
from ctypes.wintypes import WORD
from ctypes.wintypes import LONG
from ctypes.wintypes import ULONG
from ctypes.wintypes import HKEY
from ctypes.wintypes import BYTE
from ctypes.wintypes import UINT
from ctypes.wintypes import WCHAR
from ctypes.wintypes import CHAR
from ctypes.wintypes import HANDLE
from ctypes.wintypes import LPVOID
from ctypes.wintypes import LPSTR
from ctypes.wintypes import HMENU
from ctypes.wintypes import HWND
from ctypes import WINFUNCTYPE
import serial
from serial.win32 import ULONG_PTR
from serial.tools import list_ports_common

FILE_DEVICE_BUS_EXTENDER = 0x0000002a
METHOD_BUFFERED = 0
FILE_READ_DATA = 1
FILE_WRITE_DATA = 2
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
MF_BYCOMMAND = 0x00000000
SC_CLOSE = 0xF060

def CTL_CODE(DeviceType, Function, Method, Access): 
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

def USBVBUS_IOCTL(index):
    return CTL_CODE (FILE_DEVICE_BUS_EXTENDER, index, METHOD_BUFFERED, FILE_READ_DATA)

IOCTL_USBVBUS_PLUGIN_HARDWARE = USBVBUS_IOCTL (0x0)
IOCTL_USBVBUS_UNPLUG_HARDWARE = USBVBUS_IOCTL (0x1)
IOCTL_USBVBUS_EJECT_HARDWARE = USBVBUS_IOCTL (0x2)
IOCTL_USBVBUS_GET_PORTS_STATUS = USBVBUS_IOCTL (0x3)

def ValidHandle(value, func, arguments):
    if value == 0:
        raise ctypes.WinError()
    return value

NULL = 0
LPOVERLAPPED = LPVOID
HDEVINFO = ctypes.c_void_p
LPCTSTR = ctypes.c_wchar_p
PCTSTR = ctypes.c_wchar_p
PTSTR = ctypes.c_wchar_p
LPDWORD = PDWORD = ctypes.POINTER(DWORD)
#~ LPBYTE = PBYTE = ctypes.POINTER(BYTE)
LPBYTE = PBYTE = ctypes.c_void_p        # XXX avoids error about types

ACCESS_MASK = DWORD
REGSAM = ACCESS_MASK


class GUID(ctypes.Structure):
    _fields_ = [
        ('Data1', DWORD),
        ('Data2', WORD),
        ('Data3', WORD),
        ('Data4', BYTE * 8),
    ]

    def __str__(self):
        return "{{{:08x}-{:04x}-{:04x}-{}-{}}}".format(
            self.Data1,
            self.Data2,
            self.Data3,
            ''.join(["{:02x}".format(d&0xFF) for d in self.Data4[:2]]),
            ''.join(["{:02x}".format(d&0xFF) for d in self.Data4[2:]]),
        )


class SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('ClassGuid', GUID),
        ('DevInst', DWORD),
        ('Reserved', ULONG_PTR),
    ]

    def __str__(self):
        return "ClassGuid:{} DevInst:{}".format(self.ClassGuid, self.DevInst)

class ioctl_usbvbus_unplug(ctypes.Structure):
    _fields_ = [
        ('addr', CHAR),
        ('unused', CHAR*3)
    ]

class ioctl_usbvbus_get_ports_status(ctypes.Structure):
    _fields_ = [
        ('portStatus', CHAR*128)
    ]

class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ('cbSize', DWORD),
        ('InterfaceClassGuid', GUID),
        ('Flags', DWORD),
        ('Reserved', ULONG_PTR),
    ]
    def __str__(self):
        return "InterfaceClassGuid:%s Flags:%s" % (self.InterfaceClassGuid, self.Flags)

class ioctl_usbvbus_plugin(ctypes.Structure):
    _fields_ = [
        ('devid', DWORD),
        ('vendor', WORD),
        ('product', WORD),
        ('version', WORD),
        ('speed', BYTE),
        ('inum', BYTE),
        ('int0_class', BYTE),
        ('int0_subclass', BYTE),
        ('int0_protocol', BYTE),
        ('addr', BYTE)
    ]

PSP_DEVICE_INTERFACE_DATA = ctypes.POINTER(SP_DEVICE_INTERFACE_DATA)
PSP_DEVINFO_DATA = ctypes.POINTER(SP_DEVINFO_DATA)

PSP_DEVICE_INTERFACE_DETAIL_DATA = ctypes.c_void_p

DeviceIoControl = ctypes.windll.kernel32.DeviceIoControl

DeviceIoControl.argtypes = [
        HANDLE,                    # _In_          HANDLE hDevice
        DWORD,                     # _In_          DWORD dwIoControlCode
        LPVOID,                    # _In_opt_      LPVOID lpInBuffer
        DWORD,                     # _In_          DWORD nInBufferSize
        LPVOID,                    # _Out_opt_     LPVOID lpOutBuffer
        DWORD,                     # _In_          DWORD nOutBufferSize
        LPDWORD,                            # _Out_opt_     LPDWORD lpBytesReturned
        LPOVERLAPPED]                       # _Inout_opt_   LPOVERLAPPED lpOverlapped
DeviceIoControl.restype = BOOL
    
setupapi = ctypes.windll.LoadLibrary("setupapi")
SetupDiDestroyDeviceInfoList = setupapi.SetupDiDestroyDeviceInfoList
SetupDiDestroyDeviceInfoList.argtypes = [HDEVINFO]
SetupDiDestroyDeviceInfoList.restype = BOOL

CtrlHandlerRoutine = WINFUNCTYPE(BOOL, DWORD)        
SetConsoleCtrlHandler = ctypes.windll.kernel32.SetConsoleCtrlHandler
SetConsoleCtrlHandler.argtypes = (CtrlHandlerRoutine, BOOL)
SetConsoleCtrlHandler.restype = BOOL

SetupDiEnumDeviceInterfaces = ctypes.windll.setupapi.SetupDiEnumDeviceInterfaces
SetupDiEnumDeviceInterfaces.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, ctypes.POINTER(GUID), DWORD, PSP_DEVICE_INTERFACE_DATA]
SetupDiEnumDeviceInterfaces.restype = BOOL

ExitProcess = ctypes.windll.kernel32.ExitProcess
ExitProcess.argtypes = [UINT]
ExitProcess.restype = None

SetupDiGetDeviceInterfaceDetail = ctypes.windll.setupapi.SetupDiGetDeviceInterfaceDetailW
SetupDiGetDeviceInterfaceDetail.argtypes = [HDEVINFO, PSP_DEVICE_INTERFACE_DATA, PSP_DEVICE_INTERFACE_DETAIL_DATA, DWORD, PDWORD, PSP_DEVINFO_DATA]
SetupDiGetDeviceInterfaceDetail.restype = BOOL

SetupDiClassGuidsFromName = setupapi.SetupDiClassGuidsFromNameW
SetupDiClassGuidsFromName.argtypes = [PCTSTR, ctypes.POINTER(GUID), DWORD, PDWORD]
SetupDiClassGuidsFromName.restype = BOOL

SetupDiEnumDeviceInfo = setupapi.SetupDiEnumDeviceInfo
SetupDiEnumDeviceInfo.argtypes = [HDEVINFO, DWORD, PSP_DEVINFO_DATA]
SetupDiEnumDeviceInfo.restype = BOOL

SetupDiGetClassDevs = setupapi.SetupDiGetClassDevsW
SetupDiGetClassDevs.argtypes = [ctypes.POINTER(GUID), PCTSTR, HWND, DWORD]
SetupDiGetClassDevs.restype = HDEVINFO
SetupDiGetClassDevs.errcheck = ValidHandle

SetupDiGetDeviceRegistryProperty = setupapi.SetupDiGetDeviceRegistryPropertyW
SetupDiGetDeviceRegistryProperty.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, PDWORD, PBYTE, DWORD, PDWORD]
SetupDiGetDeviceRegistryProperty.restype = BOOL

SetupDiGetDeviceInstanceId = setupapi.SetupDiGetDeviceInstanceIdW
SetupDiGetDeviceInstanceId.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, PTSTR, DWORD, PDWORD]
SetupDiGetDeviceInstanceId.restype = BOOL

SetupDiOpenDevRegKey = setupapi.SetupDiOpenDevRegKey
SetupDiOpenDevRegKey.argtypes = [HDEVINFO, PSP_DEVINFO_DATA, DWORD, DWORD, DWORD, REGSAM]
SetupDiOpenDevRegKey.restype = HKEY

DI_FUNCTION = UINT
DIF_REMOVE = 5
SetupDiCallClassInstaller = setupapi.SetupDiCallClassInstaller
SetupDiCallClassInstaller.argtypes = [DI_FUNCTION, HDEVINFO, PSP_DEVINFO_DATA]
SetupDiCallClassInstaller.restype = BOOL 

CreateFile = ctypes.windll.kernel32.CreateFileA
CreateFile.argtypes = [LPSTR, DWORD, DWORD, LPVOID, DWORD, DWORD, HANDLE]
CreateFile.restype  = HANDLE

ReadFile = ctypes.windll.kernel32.ReadFile
ReadFile.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD, LPVOID]
ReadFile.restype = BOOL

WriteFile = ctypes.windll.kernel32.WriteFile
WriteFile.argtypes = [HANDLE, LPVOID, DWORD, LPDWORD, LPVOID]
WriteFile.restype = BOOL

DeleteMenu = ctypes.windll.user32.DeleteMenu
DeleteMenu.argtypes = [HMENU, UINT, UINT]
DeleteMenu.restype = BOOL

GetSystemMenu = ctypes.windll.user32.GetSystemMenu
GetSystemMenu.argtypes = [HWND, BOOL]
GetSystemMenu.restype = HMENU

GetConsoleWindow = ctypes.windll.kernel32.GetConsoleWindow
GetConsoleWindow.argtypes = []
GetConsoleWindow.restype = HWND

DIGCF_PRESENT = 2
DIGCF_DEVICEINTERFACE = 16
INVALID_HANDLE_VALUE = 0
ERROR_INSUFFICIENT_BUFFER = 122
SPDRP_HARDWAREID = 1
SPDRP_FRIENDLYNAME = 12
SPDRP_LOCATION_PATHS = 35
SPDRP_MFG = 11
DICS_FLAG_GLOBAL = 1
DIREG_DEV = 0x00000001
KEY_READ = 0x20019

def uninstallUSBHID(vendorID,productID):
    uninstalled = False
    error = False
    
    searchString = "USB\VID_%04X&PID_%04X" % (vendorID,productID)
    GUIDs = (GUID * 8)()  # so far only seen one used, so hope 8 are enough...
    guids_size = DWORD()
    if not SetupDiClassGuidsFromName(
            "HIDClass",
            GUIDs,
            ctypes.sizeof(GUIDs),
            ctypes.byref(guids_size)):
        raise ctypes.WinError()
        
    # repeat for all possible GUIDs
    for index in range(guids_size.value):
        bInterfaceNumber = None
        g_hdi = SetupDiGetClassDevs(
            ctypes.byref(GUIDs[index]),
            None,
            NULL,
            DIGCF_PRESENT)  # was DIGCF_PRESENT|DIGCF_DEVICEINTERFACE which misses CDC ports

        devinfo = SP_DEVINFO_DATA()
        devinfo.cbSize = ctypes.sizeof(devinfo)
        
        i = 0
        while SetupDiEnumDeviceInfo(g_hdi, i, ctypes.byref(devinfo)):
            i += 1

            # hardware ID
            szHardwareID = ctypes.create_unicode_buffer(250)
            # try to get ID that includes serial number
            if not SetupDiGetDeviceInstanceId(
                    g_hdi,
                    ctypes.byref(devinfo),
                    #~ ctypes.byref(szHardwareID),
                    szHardwareID,
                    ctypes.sizeof(szHardwareID) - 1,
                    None):
                # fall back to more generic hardware ID if that would fail
                if not SetupDiGetDeviceRegistryProperty(
                        g_hdi,
                        ctypes.byref(devinfo),
                        SPDRP_HARDWAREID,
                        None,
                        ctypes.byref(szHardwareID),
                        ctypes.sizeof(szHardwareID) - 1,
                        None):
                    # Ignore ERROR_INSUFFICIENT_BUFFER
                    if ctypes.GetLastError() != ERROR_INSUFFICIENT_BUFFER:
                        raise ctypes.WinError()
            if szHardwareID.value.startswith(searchString):
                if SetupDiCallClassInstaller(DIF_REMOVE, g_hdi, ctypes.byref(devinfo)):
                    uninstalled = True
                else:
                    print("Error uninstalling "+szHardwareID.value)
                    error = True
        SetupDiDestroyDeviceInfoList(g_hdi)
    return uninstalled and not error

class VBUSException(Exception):
    pass
    
def getVBUSNodeName():
    err = VBUSException("It looks like the USBIP driver is not installed")
    guid = GUID(Data1=0xD35F7840, Data2=0x6A0C, Data3=0x11d2, Data4=(0xB8, 0x41, 0x00, 0xC0, 0x4F, 0xAD, 0x51, 0x71))
    g_hdi = SetupDiGetClassDevs(
        ctypes.byref(guid),
        None,
        NULL,
        DIGCF_PRESENT|DIGCF_DEVICEINTERFACE) 
    if g_hdi == -1:
        raise err

    interfaceData = SP_DEVICE_INTERFACE_DATA()
    interfaceData.cbSize = ctypes.sizeof(interfaceData)
    
    if not SetupDiEnumDeviceInterfaces(g_hdi,
        None, 
        ctypes.byref(guid),
        0, 
        ctypes.byref(interfaceData)):
        raise err
        
    needed = DWORD()

    if ( not SetupDiGetDeviceInterfaceDetail(g_hdi,
        ctypes.byref(interfaceData),
        None,
        0,
        ctypes.byref(needed),
        None) and ctypes.GetLastError() != 122 ):
        raise err
        
    class SP_DEVICE_INTERFACE_DETAIL_DATA_CURRENT(ctypes.Structure):
            _fields_ = [
                ('cbSize', DWORD),
                ('DevicePath', WCHAR*(needed.value - ctypes.sizeof(DWORD))),
            ]

    detail = SP_DEVICE_INTERFACE_DETAIL_DATA_CURRENT()
    detail.cbSize = 8 if platform.architecture()[0] == '64bit' else 6
    
    devInfo = SP_DEVINFO_DATA()
    devInfo.cbSize = ctypes.sizeof(devInfo)

    if not SetupDiGetDeviceInterfaceDetail(g_hdi,
        ctypes.byref(interfaceData),
        ctypes.byref(detail),
        needed,
        ctypes.byref(needed),
        None):
        raise err
        
    return detail.DevicePath
    
def vbusGetPortsStatus(vbus):
    class STATUS_BUFFER(ctypes.Structure):
            _fields_ = [
                ('Buffer', BYTE*128),
            ]
    buf = STATUS_BUFFER()
    len = DWORD(0)
    if DeviceIoControl(vbus, IOCTL_USBVBUS_GET_PORTS_STATUS, None, 0, ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(len), None):
        return tuple(x&0xFF for x in buf.Buffer)
    else:
        raise VBUSException("Cannot get VBUS port statuses")
        
def vbusGetFreePort(vbus):
    statuses = vbusGetPortsStatus(vbus)
    for i in range(1,128):
        if not statuses[i]:
            return i
    raise VBUSException("All VBUS ports in use")
    
def vbusAttach(vbus, plugin):
    plugin.addr = vbusGetFreePort(vbus)
    unused = ULONG(0)
    if DeviceIoControl(vbus, IOCTL_USBVBUS_PLUGIN_HARDWARE, ctypes.byref(plugin), ctypes.sizeof(plugin), None, 0, ctypes.byref(unused), None):
        return plugin.addr
    else:
        raise VBUSException("Error attaching, error number = "+str(ctypes.GetLastError()))
        
def vbusDetach(vbus, addr): #, vendorID, productID):
    #uninstallUSBHID(vendorID, productID) ## don't need to do this with version 272
    if addr is not None:
        unplug = ioctl_usbvbus_unplug(addr=addr)
        unused = ULONG(0)
        DeviceIoControl(vbus, IOCTL_USBVBUS_PLUGIN_HARDWARE, ctypes.byref(unplug), ctypes.sizeof(unplug), None, 0, ctypes.byref(unused), None)
        
def windowsOpen(filename):
    return CreateFile(LPSTR(filename.encode()), GENERIC_READ|GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
    
def windowsWrite(handle, data):
    wrote = DWORD(0)
    n = len(data)
    class DATA_BUFFER(ctypes.Structure):
            _fields_ = [
                ('Buffer', BYTE*n),
            ]
    buf = DATA_BUFFER()
    for i in range(n):
        buf.Buffer[i] = data[i]
    #buf.Buffer = bytearray(data)
    if WriteFile(handle, ctypes.byref(buf), n, ctypes.byref(wrote), None):
        return wrote
    else:
        return -1
    
def windowsRead(handle, n):
    didRead = DWORD(0)
    class DATA_BUFFER(ctypes.Structure):
            _fields_ = [
                ('Buffer', BYTE*n),
            ]
    buf = DATA_BUFFER()
    if ReadFile(handle, ctypes.byref(buf), n, ctypes.byref(didRead), None):
        return bytes(bytearray(buf.Buffer)[:didRead.value])
    else:
        return 0    

def disableClose():
    DeleteMenu(GetSystemMenu(GetConsoleWindow(), False),SC_CLOSE, MF_BYCOMMAND);

def comports(include_links=False):
    """Return a list of info objects about serial ports"""
    return list(iterate_comports())

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
# test
if __name__ == '__main__':
    #uninstallUSBHID(0x46d,0xc62b)
    name = getVBUSNodeName()
    f = open(name, "w+b")
    print(vbusGetPortsStatus(f))
    
