import pychromecast


def get_chromecasts():
    """
    Discover available Chromecast devices on the local network.
    """
    chromecasts, browser = pychromecast.get_chromecasts()

    if not chromecasts:
        raise SystemExit("Exiting due to no available Chromecast devices.")

    print(f"Found chromecast devices: {len(chromecasts)}")
    return chromecasts


def select_chromecast(chromecasts):
    """
    Prompt the user to select a Chromecast device from the list of available devices.
    """
    casts = {idx: cast for idx, cast in enumerate(chromecasts)}

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
