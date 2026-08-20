class ChromecastNotFoundError(Exception):
    """Exception raised when a requested resource is not found."""
    pass


class IncompatibleVideoError(Exception):
    """Exception raised when a video file is not compatible with Chromecast."""
    pass
