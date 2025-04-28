from e2b_desktop import Sandbox
from dotenv import load_dotenv

load_dotenv()

# With custom configuration
desktop = Sandbox(
    display=":0",  # Custom display (defaults to :0)
    resolution=(920, 780),  # Custom resolution
    dpi=96,  # Custom DPI
    timeout=3_550
)

# Start the stream
desktop.stream.start()

# Get stream URL
url = desktop.stream.get_url()
print(url)

# # Stop the stream
# desktop.stream.stop()