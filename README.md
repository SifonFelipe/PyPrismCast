# PyPrismCast

## What is it?

**PyPrismCast** is a tool to *cast* to your Chromecast any video from your PC.
It formats your video to the format that Chromecast's needs, starts a server and
plays it.

## Installation

### Prerequisites

- Python 3.10 or higher
- [FFmpeg](https://ffmpeg.org/) installed and available in your system path (required for video transcoding).
- *[uv](https://docs.astral.sh/uv/)* for **dev** and **installation**

### Steps

#### 1- Clone repo and Go in

```bash
git clone https://github.com/SifonFelipe/PyPrismCast.git

cd PyPrismCast
```

#### 2- Install
To install it at machine level, we are going to use `uv`

```bash
uv tool install .
```

#### 3- Cast your videos!


## Usage

### Format your videos
Chromecast only accepts one format of file to cast (`.mp4` container, `aac` audio, `h264` video).
So, first you will have to format them. `pyprismcast` has a command to do that:

```bash
prismcast transcode -R path/to/movies/
```
or just one file:
```bash
prismcast transcode path/to/movie.mp4
```

### Format your subtitles
Chromecast also allows only one type of subtitle file (`.vtt`).

```bash
prismcast transcode -s path/to/subs.srt
```


### Cast your video
To cast a video formatted to chromecast-playable, you just have to run:

```bash
prismcast cast video.mp4

# with subtitles:
prismcast cast video.mp4 -s "subs_en.vtt"

# preselect chromecast device:
prismcast cast video.mp4 -d "LivingRoom"
```

## Vision
1. Have an interface from where pause/play, go forward/backwards, select movie and control volume.
2. Remote controller from mobile, connected to PC
3. Be able to launch, control and play from mobile.



