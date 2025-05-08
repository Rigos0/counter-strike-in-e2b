import sys
import os
from e2b_desktop import Sandbox, CommandExitException
from dotenv import load_dotenv
load_dotenv()


from counter_strike.install_cs import install_cs_1_6, connect_to_server, choose_team
from counter_strike.image_handling import get_screenshot_message, draw_point
from counter_strike.image_handling import get_mouse_movements
from counter_strike.controls import aim, shoot

from llms.models import AimingModel


E2B_API_KEY = os.environ.get("E2B_API_KEY")
CS_SERVER_IP = os.environ.get("CS_SERVER_IP")

desktop = Sandbox(
    display=":0",  
    resolution=(1920, 1080),  # keep this resolution
    timeout = 3600) 
desktop.stream.start()

# Get stream URL
url = desktop.stream.get_url()
print(url)
url_view = desktop.stream.get_url(view_only=True) # only viewing 
print(url_view)


aiming_model = AimingModel()

def game_loop():
    for i in range(30):
        print(f"Iteration {i}")
        screenshot_message = get_screenshot_message(desktop, filename="../images/screenshot.jpg")

        point_json, _ = aiming_model.complete(messages=screenshot_message)
        print(point_json)
        coords = aiming_model.parse_point_json(point_json)
        print(coords)
        print(type(coords))
        if not coords:
            # TODO: Define agentic logic to move around 
            print("Sleeping 5 seconds as enemies not found")
            desktop.wait(5000)
            continue

        draw_point(point = coords, image_path="../images/screenshot.jpg", output_path="../images/screenshot_annotated.jpg")

        mouse_movements = get_mouse_movements(coords=coords)
        aim(mouse_movements, desktop=desktop)
        shoot(desktop=desktop)


if __name__=="__main__":
    install_cs_1_6(desktop=desktop)
    connect_to_server(desktop=desktop, ip_address=CS_SERVER_IP)
    choose_team(desktop=desktop, team_option="1")
    game_loop()
