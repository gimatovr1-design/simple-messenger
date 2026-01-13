<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>Simple Messenger</title>

<style>
* { box-sizing: border-box; }

body {
    margin: 0;
    height: 100vh;
    background: linear-gradient(135deg, #1b1f3b, #0b0d1a);
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: system-ui, sans-serif;
    color: white;
}

#chat {
    width: 360px;
    height: 520px;
    background: rgba(255,255,255,0.08);
    backdrop-filter: blur(14px);
    border-radius: 18px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 0 35px rgba(0,0,0,0.6);
}

#header {
    text-align: center;
    font-weight: 600;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.15);
    margin-bottom: 6px;
}

#messages {
    flex: 1;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
}

.msg {
    max-width: 75%;
    padding: 8px 12px;
    border-radius: 12px;
    word-wrap: break-word;
    animation: fade 0.2s ease;
}

.msg.me {
    align-self: flex-end;
    background: linear-gradient(135deg, #4a6cff, #6c8bff);
}

.msg.other {
    align-self: flex-start;
    background: rgba(255,255,255,0.18);
}

@keyframes fade {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

.row {
    display: flex;
    gap: 6px;
    margin-top: 6px;
}

input {
    flex: 1;
    padding: 10px;
    border: none;
    border-radius: 10px;
    background: rgba(0,0,0,0.35);
    color: white;
    outline: none;
}

button {
    padding: 10px 14px;
    border: none;
    border-radius: 10px;
    background: linear-gradient(135deg, #4a6cff, #6c8bff);
    color: white;
    cursor: pointer;
}
</style>
</head>

<body>

<div id="chat">

    <div id="header">Ник: —</div>

    <div class="row">
        <input id="nick" placeholder="Введите ник">
        <button onclick="setNick()">OK</button>
    </div>

    <div id="messages"></div>

    <div class="row">
        <input id="text" placeholder="Сообщение"
               onkeydown="if(event.key==='Enter') sendMessage()">
        <button onclick="sendMessage()">➤</button>
    </div>

</div>

<script>
const ws = new WebSocket(
    (location.protocol === "https:" ? "wss" : "ws") +
    "://" + location.host + "/ws"
);

let myNick = "";

ws.onmessage = (e) => {
    const text = e.data;
    const msg = document.createElement("div");
    msg.classList.add("msg");

    if (myNick && text.startsWith(myNick + ":")) {
        msg.classList.add("me");
        msg.textContent = text.replace(myNick + ":", "").trim();
    } else {
        msg.classList.add("other");
        msg.textContent = text;
    }

    document.getElementById("messages").appendChild(msg);
    msg.scrollIntoView({ behavior: "smooth" });
};

function setNick() {
    const n = document.getElementById("nick").value.trim();
    if (!n) return;

    myNick = n;
    document.getElementById("header").textContent = "Ник: " + n;
    ws.send("/nick " + n);
}

function sendMessage() {
    const input = document.getElementById("text");
    const text = input.value.trim();
    if (!text) return;

    ws.send(text);
    input.value = "";
}
</script>

</body>
</html>
