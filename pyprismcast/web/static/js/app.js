const stateElement = document.getElementById("player-state");
const bannerElement = document.getElementById("cast-banner");
const bannerTitleElement = document.getElementById("cast-banner-title");
const bannerSubtitleElement = document.getElementById("cast-banner-subtitle");
const bannerActionButton = document.getElementById("banner-play-pause");
const currentTimeElement = document.getElementById("current-time");
const durationElement = document.getElementById("duration");
const movieTitleElement = document.getElementById("movie-title");
const seekBar = document.getElementById("seek-bar");
const playPauseButton = document.getElementById("play-pause");
const playIcon = playPauseButton.querySelector(".icon-play");
const pauseIcon = playPauseButton.querySelector(".icon-pause");
const backwardButton = document.getElementById("backward");
const forwardButton = document.getElementById("forward");
const stopButton = document.getElementById("stop");
const volumeDownButton = document.getElementById("volume-down");
const volumeUpButton = document.getElementById("volume-up");
const volumeLevelElement = document.getElementById("volume-level");
const volumeFillElement = document.getElementById("volume-fill");
const silentAudio = document.getElementById("silent-audio");

// Icons reused inside the cast banner's mini play/pause button
const ICON_PLAY =
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">' +
    '<path d="M8 5.6v12.8c0 .8.9 1.3 1.6.9l10.1-6.4c.6-.4.6-1.4 0-1.8L9.6 4.7c-.7-.4-1.6.1-1.6.9z"/></svg>';
const ICON_PAUSE =
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">' +
    '<rect x="6" y="5" width="4.5" height="14" rx="1.2"/>' +
    '<rect x="13.5" y="5" width="4.5" height="14" rx="1.2"/></svg>';

// === State ===
let socket = null;
let wsConnected = false;
let playerState = "IDLE";
let currentPosition = 0;
let duration = 0;
// Timestamp of the last synchronization received from Chromecast
let lastSyncTime = 0;
let isSeeking = false;
// Last known volume (0-1). Null until the first real reading arrives.
let localVolume = null;

// === WebSocket ===
function connect() {
    const protocol = window.location.protocol === "https:" ? "wss:": "ws:";
    socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

    socket.addEventListener("open", () => {
        wsConnected = true;
        console.log("[ws] Connected");
        updateCastBanner();
    });

    socket.addEventListener("message", (event) => {
        try {
            const message = JSON.parse(event.data);
            handleMessage(message);
        } catch (error) {
            console.error("[ws] Invalid message:", event.data, error);
        }
    });

    socket.addEventListener("close", () => {
        wsConnected = false;
        console.log("[ws] Disconnected");
        updateCastBanner();
        // Try again after 2 seconds.
        setTimeout(connect, 2000);
    });

    socket.addEventListener("error", (error) => {
        console.error("[ws] Error:", error);
    });
}

// === Status polling (safety net) ===
// The backend only broadcasts over the websocket when the media session
// itself changes (play/pause/seek/content). Receiver-level changes like
// volume never trigger a push, so we also poll the REST endpoint, which
// always reads the live value straight from the Chromecast connection.
const STATUS_POLL_MS = 3000;

async function pollStatus() {
    try {
        const response = await fetch("/api/status");
        if (!response.ok) {
            return;
        }
        updatePlayerStatus(await response.json());
    } catch (error) {
        console.warn("[poll] Failed to fetch status:", error);
    }
}

setInterval(pollStatus, STATUS_POLL_MS);

document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
        pollStatus();
    }
});

// === Incoming messages ===
function handleMessage(message) {
    switch (message.type) {
        case "status":
            updatePlayerStatus(message);
            break;
        default:
            console.log("[ws] Unknown message:", message);
    }
}

// === Player Status ===
function updatePlayerStatus(status) {
    playerState = status.state ?? "IDLE";
    stateElement.textContent = playerState;

    // Synchronize position with Chromecast.
    // current_time is a snapshot. We use the timestamp below to continue the clock locally.
    currentPosition = Number(status.current_time) || 0;
    duration = Number(status.duration) || 0;
    lastSyncTime = performance.now();

    // Duration
    durationElement.textContent = formatTime(duration);
    seekBar.max = duration;

    // === Position: Don't overwrite the slider while the user is dragging it ===
    if (!isSeeking) {
        seekBar.value = currentPosition;
        currentTimeElement.textContent = formatTime(currentPosition);
        updateSeekFill();
    }

    // === Play/Pause ===
    setPlayPauseIcon(playerState === "PLAYING");

    // === Volume ===
    const volume = Number(status.volume_level);
    if (Number.isFinite(volume)) {
        updateVolume(volume);
    }

    // === Movie title ===
    if (status.content_id) {
        movieTitleElement.textContent = getMovieName(status.content_id);
    } else {
        movieTitleElement.textContent = "Sin contenido";
    }

    updateCastBanner();
    updateMediaSession();
}

// === OS-level media notification (MediaSession) ===
// Chrome/Android (and Safari/iOS) only surface the lock-screen and
// notification-shade media controls while a real audio or video element
// is playing in the tab, so we keep a silent looping clip going in the
// background and hang the Chromecast controls off it via MediaSession.
const mediaSessionSupported = "mediaSession" in navigator;

function unlockMediaSession() {
    if (!silentAudio || silentAudio.dataset.unlocked) {
        return;
    }
    silentAudio.play()
        .then(() => { silentAudio.dataset.unlocked = "true"; })
        .catch((error) => console.warn("[media-session] Could not start silent audio:", error));
}

document.addEventListener("pointerdown", unlockMediaSession, {once: true});

function updateMediaSession() {
    if (!mediaSessionSupported) {
        return;
    }

    const isActive = playerState === "PLAYING" || playerState === "PAUSED";

    if (!isActive) {
        navigator.mediaSession.metadata = null;
        navigator.mediaSession.playbackState = "none";
        silentAudio?.pause();
        return;
    }

    navigator.mediaSession.metadata = new MediaMetadata({
        title: movieTitleElement.textContent,
        artist: "PyCast",
    });
    navigator.mediaSession.playbackState = playerState === "PLAYING" ? "playing" : "paused";

    if (duration > 0) {
        try {
            navigator.mediaSession.setPositionState({
                duration,
                playbackRate: 1,
                position: Math.min(currentPosition, duration),
            });
        } catch (error) {
            console.warn("[media-session] setPositionState failed:", error);
        }
    }
}

if (mediaSessionSupported) {
    navigator.mediaSession.setActionHandler("play", () => sendCommand("play"));
    navigator.mediaSession.setActionHandler("pause", () => sendCommand("pause"));
    navigator.mediaSession.setActionHandler("stop", () => sendCommand("stop"));
    navigator.mediaSession.setActionHandler("seekbackward", (details) => {
        sendCommand("seek_relative", {seconds: -(details.seekOffset || 10)});
    });
    navigator.mediaSession.setActionHandler("seekforward", (details) => {
        sendCommand("seek_relative", {seconds: details.seekOffset || 10});
    });
}

// === Local clock ===
function updateClock() {
    if (playerState !== "PLAYING" || isSeeking) {
        return;
    }
    if (duration <= 0) {
        return;
    }
    const elapsed = (performance.now() - lastSyncTime) / 1000;
    const position = Math.min(currentPosition + elapsed, duration);

    currentTimeElement.textContent = formatTime(position);
    seekBar.value = position;
    updateSeekFill();
}

setInterval(updateClock, 250);  // update 4 times per second

// === Cast banner ===
// A persistent status strip modelled on the native Chromecast mini
// controller, so there's always a quick way to see and pause what's casting.
function updateCastBanner() {
    if (!wsConnected) {
        bannerElement.dataset.state = "disconnected";
        bannerTitleElement.textContent = "Desconectado";
        bannerSubtitleElement.textContent = "Reintentando conexión\u2026";
        bannerActionButton.hidden = true;
        return;
    }

    if (playerState === "PLAYING" || playerState === "PAUSED") {
        bannerElement.dataset.state = playerState === "PLAYING" ? "casting" : "paused";
        bannerTitleElement.textContent = playerState === "PLAYING" ? "Casteando ahora" : "En pausa";
        bannerSubtitleElement.textContent = movieTitleElement.textContent;
        bannerActionButton.hidden = false;
        bannerActionButton.innerHTML = playerState === "PLAYING" ? ICON_PAUSE : ICON_PLAY;
        bannerActionButton.setAttribute("aria-label", playerState === "PLAYING" ? "Pausar" : "Reproducir");
        return;
    }

    bannerElement.dataset.state = "connected";
    bannerTitleElement.textContent = "Listo para castear";
    bannerSubtitleElement.textContent = "Elegí algo para reproducir";
    bannerActionButton.hidden = true;
}

bannerActionButton.addEventListener("click", () => {
    sendCommand("toggle");
});

// === Commands ===
function sendCommand(type, data = {}) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.warn("[ws] Cannot send command: socket not connected");
        return;
    }
    const message = {type, ...data,};
    console.log("[ws] Sending:", message);
    socket.send(JSON.stringify(message));
}

// === Play/Pause ===
playPauseButton.addEventListener("click", () => {
    sendCommand("toggle");
});

function setPlayPauseIcon(isPlaying) {
    playIcon.hidden = isPlaying;
    pauseIcon.hidden = !isPlaying;
}

// === Seek Relative ===
backwardButton.addEventListener("click", () => {
    sendCommand("seek_relative", {seconds: -10,});
});

forwardButton.addEventListener("click", () => {
    sendCommand("seek_relative", {seconds: 10,});
});

// === Seek Bar ===
seekBar.addEventListener("pointerdown", () => {
    isSeeking = true;
});

// Update time while dragging
seekBar.addEventListener("input", () => {
    if (!isSeeking) {
        return;
    }
    const position = Number(seekBar.value);
    currentTimeElement.textContent = formatTime(position);
    updateSeekFill();
});

// seek
seekBar.addEventListener("pointerup", commitSeek);
seekBar.addEventListener("change", commitSeek);

function commitSeek() {
    if (!isSeeking) {
        return;
    }
    const position = Number(seekBar.value);
    currentPosition = position;
    lastSyncTime = performance.now();
    // tell chromecast
    sendCommand("seek", {position,});
    isSeeking = false;
}

// Keeps the filled portion of the seek bar in sync with its value,
// since the native <input type="range"> has no built-in progress fill.
function updateSeekFill() {
    const max = Number(seekBar.max) || 0;
    const value = Number(seekBar.value) || 0;
    const percentage = max > 0 ? (value / max) * 100 : 0;
    seekBar.style.setProperty("--range-progress", `${percentage}%`);
}

// === Stop ===
stopButton.addEventListener("click", () => {
    sendCommand("stop");
});

// === Volume ===
volumeDownButton.addEventListener("click", () => {
    sendCommand("volume_down", {decrement: 0.1,});
    nudgeVolume(-0.1);
});

volumeUpButton.addEventListener("click", () => {
    sendCommand("volume_up", {increment: 0.1,});
    nudgeVolume(0.1);
});

// Optimistically move the bar before the server confirms — volume changes
// don't come back over the websocket, so without this the UI would only
// catch up on the next poll.
function nudgeVolume(delta) {
    if (localVolume === null) {
        return;
    }
    updateVolume(localVolume + delta);
}

// Update volume UI.
function updateVolume(volume) {
    volume = Math.max(0, Math.min(1, volume));
    localVolume = volume;
    const percentage = Math.round(volume * 100);
    volumeLevelElement.textContent = `${percentage}%`;
    volumeFillElement.style.width = `${percentage}%`;
}

// === Utils ===
function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) {
        return "00:00";
    }
    seconds = Math.floor(seconds);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
    }
    return `${String(minutes).padStart(2, "0")}:${String(remainingSeconds).padStart(2, "0")}`;
}

// get movie name from URL
function getMovieName(contentId) {
    try {
        const url = new URL(contentId);
        const pathname = decodeURIComponent(url.pathname);
        const filename = pathname.split("/").pop();
        return filename || "Contenido desconocido";
    } catch {
        return contentId;
    }
}

// Start
updateCastBanner();
pollStatus();
connect();
