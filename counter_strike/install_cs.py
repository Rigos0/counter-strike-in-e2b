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


def connect_to_server(desktop: "Sandbox", ip_address: str):
    desktop.wait(5000)
    desktop.left_click(76, 948) # click on Find Servers
    desktop.wait(1000)
    desktop.left_click(258, 76) # Click on Favorites Tab
    desktop.wait(1000)
    desktop.left_click(665, 604) # Add server
    desktop.wait(1000)
    desktop.write(text=ip_address) # Type server ip Address
    desktop.wait(500)
    desktop.left_click(1119, 527) # Add server to favourites
    desktop.wait(500)
    desktop.left_click(273, 126) # Select the added server
    desktop.wait(500)
    desktop.left_click(849, 606) # Connect
    # Now wait at least 2 mins for connection and Download
    print("Waiting for 150 secs for map download...")
    for i in range(5):
        desktop.wait(30_000)

def choose_team(desktop: "Sandbox", team_option: str = "1", skin: str = "4"):
    # Team: 1=T, 2=CT, 6=SPECTATE
    # Skin: T side: Guerilla warfare skin because they have the red headband
    desktop.press("enter")
    desktop.wait(300)
    desktop.press(team_option) # 1=T, 2=CT, 6=SPECTATE
    desktop.wait(300)
    desktop.press(skin) # T side: Guerilla warfare skin because they have the red headband
