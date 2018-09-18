This code uses the USB/IP project: http://usbip.sourceforge.net/ to pretend that an
serial SpaceBall 4000 FLX is actually a USB-HID based SpacePilot Pro (for use with the
official 3dxware drivers) or else that it is a standard six-axis joystick.

You have two choices: You can use the official signed usbip release. If you do that, you run
the danger of a blue-screen if you detach without first deleting the driver. When using the
official signed usbip release, 3d.py re-launches in administrator mode, and then deletes the
driver before detaching IF you detach by pressing ctrl-c. If you use the unsigned usbip release
(https://sourceforge.net/p/usbip/discussion/418507/thread/86c5e473/) you won't have such
problems, but installation will be more complicated.

1. Download the latest USB/IP driver. (You get more stability with the unsigned one, but installation is more complex and less secure.) 

2. Unzip the zip file somewhere.

3. Start Device Manager: Win-R devmgmt.msc

4. Click on any display line. Starting with the menu, do: Action | Add legacy hardware | Next | Install ... manually select | Next | Show all devices | Next | Have Disk | Browse. Then find your USBIPEnum.inf (from your zip in step 2) and choose Open.

5. Download the correct exe file for your system from the github repository. Currently the 32-bit version is having some trouble.

6. Plug your SpaceBall into a serial-to-USB adapter. Find out the COM port number of that adapter. (E.g., look in Device Manager under ports, or run 3d -l).

7. Run:


    3d -p COMx
    
where COMx is your COM port. An admin window will pop up and create an emulated SpaceMouse Pro (in my original post I mistakenly said SpacePilot Pro) which should work with 3dxware. If you want to create a standard six-axis 12-button joystick instead, try:

    3d -p COMx -j

8. To exit, close the window that runs the emulation.