const stateElement = document.getElementById("player-state");
const connectionElement = document.getElementById("connection-status");
const currentTimeElement = document.getElementById("current-time");
const durationElement = document.getElementById("duration");
const movieTitleElement = document.getElementById("movie-title");
const seekBar = document.getElementById("seek-bar");
const playPauseButton = document.getElementById("play-pause");
const backwardButton = document.getElementById("backward");
const forwardButton = document.getElementById("forward");
const stopButton = document.getElementById("stop");
const volumeDownButton = document.getElementById("volume-down");
const volumeUpButton = document.getElementById("volume-up");
const volumeLevelElement = document.getElementById("volume-level");

// === State ===
let socket = null;

let playerState = "IDLE";

let currentPosition = 0;
let duration = 0;

// Timestamp of the last synchronization received from Chromecast
let lastSyncTime = 0;

let isSeeking = false;

// === WebSocket ===
function connect() {

    const protocol = window.location.protocol === "https:" ? "wss:": "ws:";

    socket = new WebSocket(`${protocol}//${window.location.host}/ws`);

    socket.addEventListener(
        "open",
        () => {
            connectionElement.textContent = "Connected";
            console.log("[ws] Connected");
        }
    );

    socket.addEventListener(
        "message",
        (event) => {
            try {
                const message = JSON.parse(event.data);
                handleMessage(message);
            } catch (error) {
                console.error(
                    "[ws] Invalid message:",
                    event.data,
                    error
                );
            }
        }
    );

    socket.addEventListener(
        "close",
        () => {
            connectionElement.textContent = "Disconnected";
            console.log("[ws] Disconnected");
            // Try again after 2 seconds.
            setTimeout(connect, 2000);
        }
    );

    socket.addEventListener(
        "error",
        (error) => {
            console.error("[ws] Error:", error);
        }
    );
}

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
    }

    // === Play/Pause ===
    if (playerState === "PLAYING") {
        playPauseButton.textContent = "⏸";
    } else {
        playPauseButton.textContent = "▶";
    }

    // === Volume ===
    const volume = Number(status.volume_level);

    if (Number.isFinite(volume)) {
        updateVolume(volume);
    }

    // === Movie title ===
    if (status.content_id) {
        movieTitleElement.textContent = getMovieName(status.content_id);
    } else {
        movieTitleElement.textContent = "No media";
    }
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
}

setInterval(updateClock, 250);  // update 4 times per second

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
});

// seek
seekBar.addEventListener("pointerup", commitSeek);
seekBar.addEventListener("change",commitSeek);

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

// === Stop ===
stopButton.addEventListener("click", () => {
    sendCommand("stop");
});

// === Volume ===
volumeDownButton.addEventListener("click", () => {
    sendCommand("volume_down", {decrement: 0.1,});
});

volumeUpButton.addEventListener("click", () => {
    sendCommand("volume_up", {increment: 0.1,});
});

// Update volume UI.
function updateVolume(volume) {
    volume = Math.max(0, Math.min(1, volume));
    const percentage = Math.round(volume * 100);

    volumeLevelElement.textContent = `${percentage}%`;
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
        return (
            `${hours}:` +
            `${String(minutes).padStart(2, "0")}:` +
            `${String(remainingSeconds).padStart(2, "0")}`
        );
    }

    return (
        `${String(minutes).padStart(2, "0")}:` +
        `${String(remainingSeconds).padStart(2, "0")}`
    );
}

// get movie name from URL
function getMovieName(contentId) {
    try {
        const url = new URL(contentId);
        const pathname = decodeURIComponent(url.pathname);
        const filename = pathname.split("/").pop();

        return filename ||"Unknown media";
    } catch {
        return contentId;
    }
}

// Start
connect();
