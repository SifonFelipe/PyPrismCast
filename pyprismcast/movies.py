"""
Chromecast only supports natively the following formats:
- Container: MP4
- Video: H.264 8-bit, up to 1080p
- Audio: AAC stereo/mono (no 5.1/7.1, no AC-3/DTS)

See transcode.py for more details. Here we assume it is ready to be casted
"""

from pyprismcast.transcode.video import VIDEO_EXTENSIONS


def select_movie(movies_dir, default_movie=None):
    """
    Prompt the user to select a movie from the available movies in the specified directory.
    """
    movies = [
        p for p in movies_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]

    if not movies:
        raise SystemExit("No movies found in the specified directory.")

    if default_movie:
        for movie in movies:
            if movie.name == default_movie:
                print(f"Automatically selecting movie: {movie.name}")
                return movie

        raise SystemExit(
            f"Default movie '{default_movie}' not found. "
            f"Found instead: {[movie.name for movie in movies]}"
        )


    while True:
        print("Available movies:")
        for idx, movie in enumerate(movies):
            print(f"[{idx}] {movie.name}")

        selection = input("Select a movie (or 'q' to quit): ")

        if selection.lower() == 'q':
            raise SystemExit("User exited the selection.")

        try:
            selected_index = int(selection)
            if 0 <= selected_index < len(movies):
                return movies[selected_index]
            else:
                print("Invalid selection. Please try again.")

        except ValueError:
            print("Invalid input. Please enter a number or 'q' to quit.")
