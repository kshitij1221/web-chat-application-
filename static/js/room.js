// static/js/room.js

var socketio = io();

const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
};
// let localStream;
// let remoteStream;
// let peerConnection;

// const startCallButton = document.getElementById("startCall");
// const endCallButton = document.getElementById("endCall");
// const localAudio = document.getElementById("localAudio");
// const remoteAudio = document.getElementById("remoteAudio");

const room = getCookie("room");
const username = getCookie("name").replace(/"/g, "");

const messages = document.getElementById("messages");

const createMessage = (name, msg, self) => {
  const side = username === name ? "self" : "other";

  const content = `
    <div class="message ${side}">
        <div class="text">
            <strong>${name}</strong>: ${msg}
        </div>
        <div class="time">${new Date().toLocaleTimeString()}</div>
    </div>
    `;
  messages.innerHTML += content;
};

const createMediaMessage = (name, url) => {
  const content = `
    <div class="text">
        <span class="msg">
            <strong>${name}</strong>:
            <img src="${url}" />
        </span>
        <span class="muted">
            ${new Date().toLocaleString()}
        </span>
    </div>
    `;
  messages.innerHTML += content;
};

socketio.on("message", (data) => {
  const self = data.name === "{{ session.get('name') }}";
  createMessage(data.name, data.message, self);
});

socketio.on("media", (data) => {
  createMediaMessage(data.name, data.url);
});

socketio.on("load_messages", (data) => {
  data.messages.forEach((msg) => {
    if (msg.url) {
      createMediaMessage(msg.name, msg.url);
    } else {
      createMessage(msg.name, msg.message);
    }
  });
});

const sendMessage = () => {
  const message = document.getElementById("message");
  if (message.value == "") return;
  socketio.emit("message", { data: message.value });
  message.value = "";
};

const uploadMedia = () => {
  const mediaInput = document.getElementById("media-input");
  const file = mediaInput.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append("media", file);

  fetch("/upload_media", {
    method: "POST",
    body: formData,
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        socketio.emit("media", { url: data.url });
        console.log("Media uploaded successfully:", data.url);
      } else {
        console.error("Failed to upload media");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
    });
};

// Handle form submission via AJAX
const inviteForm = document.getElementById("invite-form");
inviteForm.addEventListener("submit", function (event) {
  event.preventDefault(); // Prevent the default form submission

  const formData = new FormData(inviteForm);
  const requestData = new URLSearchParams(formData).toString();

  fetch("/send_invites", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: requestData,
  })
    .then((response) => response.text())
    .then((data) => {
      console.log("Success:", data);
    })
    .catch((error) => {
      console.error("Error:", error);
    });
});
// const makeCall = (e) => {
//   e.preventDefault()
//   const toNumberInput = document.getElementById("to-number");
//   const toNumber = toNumberInput.value.trim();
//   if (!toNumber) {
//     console.error("Phone number is required");
//     return;
//   }

//   const formData = new FormData();
//   formData.append("to_number", toNumber);

//   fetch("/make_call", {
//     method: "POST",
//     body: formData,
//   })
//     .then((response) => response.json())
//     .then((data) => {
//       if (data.success) {
//         console.log("Call initiated successfully. Call SID:", data.call_sid);
//         alert("Call initiated successfully!");
//       } else {
//         console.error("Failed to initiate call:", data.message);
//         alert("Failed to initiate call: " + data.message);
//       }
//     })
//     .catch((error) => {
//       console.error("Error:", error);
//       alert("An error occurred: " + error.message);
//     });
// };

// // Attach event listener to the button
// document.getElementById("make-call-button").addEventListener("click", makeCall);

const exitChat = () => {
  console.log("Exit button clicked");
  fetch("/exit_chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ code: "{{ code }}" }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.success) {
        console.log("Exit successful");
        window.location.href = "/";
      } else {
        console.error("Failed to exit chat");
      }
    })
    .catch((error) => {
      console.error("Error:", error);
    });
};

// startCallButton.onclick = async () => {
//   try {
//     localStream = await navigator.mediaDevices.getUserMedia({ audio: true });
//     localAudio.srcObject = localStream;

//     peerConnection = new RTCPeerConnection(configuration);
//     peerConnection.addStream(localStream);

//     peerConnection.onaddstream = (event) => {
//       remoteAudio.srcObject = event.stream;
//     };

//     socketio.on("offer", (data) => {
//       console.log('Received offer:', data.offer);
//       peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
//       peerConnection.createAnswer().then((answer) => {
//         peerConnection.setLocalDescription(answer);
//         socketio.emit("answer", { answer });
//       });
//     });

//     socketio.on("answer", (data) => {
//       console.log('Received answer:', data.answer);
//       peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
//     });

//     socketio.on("ice-candidate", (data) => {
//       console.log('Received ICE candidate:', data.candidate);
//       peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
      
//     });

//     peerConnection.onicecandidate = (event) => {
//       if (event.candidate) {

//         console.log('Sending ICE candidate:', event.candidate);
//         socketio.emit("ice-candidate", { candidate: event.candidate });
//       }
//     };
//   } catch (error) {
//     console.error("Error accessing media devices.", error);
//   }
// };

// endCallButton.onclick = () => {
//   if (localStream) {
//     localStream.getTracks().forEach((track) => track.stop());
//   }
//   if (peerConnection) {
//     peerConnection.close();
//   }
//   localAudio.srcObject = null;
//   remoteAudio.srcObject = null;
// };

socketio.emit("join", { username, room });
