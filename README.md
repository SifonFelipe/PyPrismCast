# PyPrismCast

## What is it?

**PyPrismCast** is a tool to *cast* to your Chromecast any video from your PC.
It formats your video to the format that Chromecast's needs, starts a server and
plays it.

## Installation

### Prerequisites

- Python 3.12 or higher
- [FFmpeg](https://ffmpeg.org/) installed and available in your system path (required for video transcoding).
- *[uv](https://docs.astral.sh/uv/)* for venv

### Steps

#### 1- Clone repo
`git clone https://github.com/SifonFelipe/PyPrismCast.git`

#### 2- Change directory and Syncronize venv
`cd PyPrismCast`


`uv sync`


## Quick Start
Move your movies to `movies/` folder. Then, run:


`uv run main.py`


It will format the movies to a format that the Chromecast will accept. This step will take some
time, even more if they are long or many.


## Tip
If you have many movies and want to format them all, just run:


`uv run transcode.py`



## Vision
1- Have an interface from where pause/play, go forward/backwards, select movie and control volume.
2- Remote controller from mobile, connected to PC
3- Be able to launch, control and play from mobile.



