import pychromecast
from pyprismcast.errors import ChromecastNotFoundError


def get_chromecasts():
    """
    Discover available Chromecast devices on the local network.
    """
    chromecasts, browser = pychromecast.get_chromecasts()

    if chromecasts:
        print(f"Found chromecast devices: {len(chromecasts)}")
    return chromecasts


def select_chromecast(chromecasts, default_device=None):
    """
    Prompt the user to select a Chromecast device from the list of available devices.
    If a default device name is provided, it will be selected automatically if found.
    """
    casts = {idx: cast for idx, cast in enumerate(chromecasts)}

    if default_device:
        for cast in chromecasts:
            if cast.name == default_device:
                print(f"Automatically selecting Chromecast: {cast.name}")
                return cast

        raise ChromecastNotFoundError(
            f"Default device '{default_device}' not found. "
            f"Found instead: {[cast.name for cast in chromecasts]}"
        )

    if len(casts) == 1:
        print(f"Only one Chromecast device found: {casts[0].name}. Automatically selecting it.")
        return casts[0]

    while True:
        print("Available Chromecast devices:")
        for idx, cast in casts.items():
            print(f"[{idx}] {cast.name}")

        selection = input("Select a Chromecast device (or 'q' to quit): ")

        if selection.lower() == 'q':
            raise SystemExit("User exited the selection.")

        try:
            selected_index = int(selection)
            if selected_index in casts:
                return casts[selected_index]
            else:
                print("Invalid selection. Please try again.")

        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")


def connect(cast):
    """
    Connect to the selected Chromecast device.
    """
    cast.wait()
    print(f"Connected to Chromecast: {cast.name}")
