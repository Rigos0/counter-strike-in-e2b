import base64
from e2b_desktop import Sandbox


def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_screenshot(desktop: Sandbox, filename = "screenshot.jpg"):
    image_bytes = desktop.screenshot(format="bytes")

    if filename:
        with open("screenshot.jpg", "wb") as f:
            f.write(image_bytes)

    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    return base64_image


def get_screenshot_message(desktop: Sandbox, filename: str | None = None):
    base64_image = get_screenshot(desktop, filename)
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                    },
                },
            ], }
    ]