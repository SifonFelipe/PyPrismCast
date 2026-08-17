const stateElement = document.getElementById("state");
const timeElement = document.getElementById("time");


const socket = new WebSocket(
    `ws://${window.location.host}/ws`
);


socket.addEventListener("open", () => {
    console.log("WebSocket connected");

    stateElement.textContent = "Connected";
});


socket.addEventListener("close", () => {
    console.log("WebSocket disconnected");

    stateElement.textContent = "Disconnected";
});


socket.addEventListener("message", (event) => {
    const data = JSON.parse(event.data);

    console.log("Status:", data);

    if (data.type !== "status") {
        return;
    }

    stateElement.textContent = data.state;

    timeElement.textContent =
        formatTime(data.current_time);
});


function sendCommand(type, data = {}) {

    if (socket.readyState !== WebSocket.OPEN) {
        console.error("WebSocket is not connected");
        return;
    }

    socket.send(
        JSON.stringify({
            type,
            ...data,
        })
    );
}


function formatTime(seconds) {

    if (!seconds || seconds < 0) {
        return "00:00";
    }

    seconds = Math.floor(seconds);

    const minutes = Math.floor(
        seconds / 60
    );

    const remainingSeconds =
        seconds % 60;

    return (
        `${String(minutes).padStart(2, "0")}:` +
        `${String(remainingSeconds).padStart(2, "0")}`
    );
}
