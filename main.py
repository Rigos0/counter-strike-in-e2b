from e2b_desktop import Sandbox
import os
E2B_API_KEY = os.environ.get("E2B_API_KEY")


# With custom configuration
desktop = Sandbox(
    display=":0", 
    resolution=(1920, 1080),  
    timeout = 3600) 


desktop.stream.start()


# Get stream URL
url = desktop.stream.get_url()
print(url)