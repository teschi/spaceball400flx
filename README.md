This code uses the USB/IP project: http://usbip.sourceforge.net/ to pretend that an
serial SpaceBall 4000 FLX is actually a USB-HID based SpacePilot Pro (for use with the
official 3dxware drivers) or else that it is a standard six-axis joystick.

You have two choices: You can use the official signed usbip release. If you do that, you run
the danger of a blue-screen if you detach without first deleting the driver. When using the
official signed usbip release, 3d.py re-launches in administrator mode, and then deletes the
driver before detaching IF you detach by pressing ctrl-c. If you use the unsigned usbip release
(https://sourceforge.net/p/usbip/discussion/418507/thread/86c5e473/) you won't have such
problems, but installation will be more complicated.

