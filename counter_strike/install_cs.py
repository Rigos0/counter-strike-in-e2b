import os
from e2b_desktop import Sandbox, CommandExitException


def install_cs_1_6(desktop: Sandbox):
    desktop.open("https://www.cybersports.lt/setup/") # open the link in the default browser
    desktop.commands.run("sudo dpkg --add-architecture i386")
    desktop.commands.run("sudo apt update")
    desktop.wait(100)
    desktop.commands.run("sudo apt install -y wine32")
    desktop.wait(2000)
    try:
        desktop.commands.run("wine .") # this throws an error for fun
    except CommandExitException:
        pass
    desktop.open("https://drive.google.com/u/0/uc?id=1TIsvGACSrQOr1tgPaVpJebH375LjLIV6&export=download")
    desktop.wait(ms=4000)
    desktop.left_click(460, 305) #click the Download button
    desktop.wait(ms=7000) 
    desktop.commands.run("unzip Downloads/Windows7DefaultFonts.zip -d Downloads") # couldnt find
    desktop.commands.run("mv Downloads/Windows7DefaultFonts/* ~/.wine/drive_c/windows/Fonts/")
    desktop.left_click(880, 1040) # open the terminal (I know, clean)
    desktop.wait(100)
    desktop.left_click(1800, 800) # click on the terminal window
    desktop.write("wine Downloads/Counter-Strike-1.6-original.exe", chunk_size=50, delay_in_ms=25) 
    desktop.wait(2000)
    desktop.press("enter") # start the exe with wine
    desktop.wait(6000)
    desktop.press("enter") # start the installation
    desktop.wait(2000)
    desktop.press("enter") # one menu
    desktop.wait(2000)
    desktop.press("enter") # second menu
    desktop.wait(2000)
    desktop.press("enter") # final install button
    desktop.wait(30000) # installation process
    desktop.wait(30000) # installation process
    desktop.press("enter") # LAUNCH