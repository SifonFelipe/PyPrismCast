#!/usr/bin/env python3

from pyprismcast import handlers
from pyprismcast.args import parse_args


def main():
    args = parse_args()

    command = args.command

    if command == "cast":
        handlers.cast(args)

    elif command == "transcode":
        handlers.transcode(args)

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
