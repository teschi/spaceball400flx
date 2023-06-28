#! 
#
# (C) 2001-2016 Chris Liechti <cliechti@gmx.net>
# (C) 2018 Alexander Pruss
#
# SPDX-License-Identifier:    BSD-3-Clause

from __future__ import absolute_import
import winreg

# pylint: disable=invalid-name,too-few-public-methods
import ctypes
#import msvcrt
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
from ctypes.wintypes import HANDLE
from ctypes.wintypes import LPVOID
from ctypes.wintypes import LPSTR
from ctypes.wintypes import HMENU
from ctypes.wintypes import HWND
from ctypes import WINFUNCTYPE

CtrlHandlerRoutine = WINFUNCTYPE(BOOL, DWORD)        
SetConsoleCtrlHandler = ctypes.windll.kernel32.SetConsoleCtrlHandler
#SetConsoleCtrlHandler.argtypes = (CtrlHandlerRoutine, BOOL)
SetConsoleCtrlHandler.restype = BOOL

ExitProcess = ctypes.windll.kernel32.ExitProcess
ExitProcess.argtypes = [UINT]
ExitProcess.restype = None

