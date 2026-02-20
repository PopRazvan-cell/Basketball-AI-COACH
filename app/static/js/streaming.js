document.addEventListener('DOMContentLoaded', () => {
    // 1. Referințe către elementele din pagină
    const video = document.getElementById('webcam');
    const statusElement = document.getElementById('status');
    const playerNameElement = document.getElementById('player_name');
    const elbowAngleElement = document.getElementById('elbow_angle');
    
    // Canvas-ul de overlay pentru desenat scheletul (trebuie să existe în live.html)
    const overlay = document.getElementById('skeleton_overlay');
    const overlayCtx = overlay ? overlay.getContext('2d') : null;

    // Canvas ascuns pentru captura de cadre (nu este afișat în UI)
    const hiddenCanvas = document.createElement('canvas');
    const hiddenCtx = hiddenCanvas.getContext('2d');

    // 2. Logica de detectare a protocolului (FIX pentru "Operation is Insecure")
    const isHTTPS = window.location.protocol === 'https:';
    const protocol = isHTTPS ? 'wss' : 'wss';
    const socketUrl = `${protocol}://${window.location.host}/ws`;

    console.log(`[BasketAI] Protocol detectat: ${window.location.protocol}`);
    console.log(`[BasketAI] Conectare la: ${socketUrl}`);

    let socket;

    // 3. Funcția de inițializare a camerei
    async function setupCamera() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { 
                    width: { ideal: 640 }, 
                    height: { ideal: 480 },
                    facingMode: "user" 
                },
                audio: false
            });
            video.srcObject = stream;
            video.onloadedmetadata = () => {
                video.play();
                // Potrivim dimensiunea canvas-ului de overlay cu video-ul
                if (overlay) {
                    overlay.width = video.videoWidth;
                    overlay.height = video.videoHeight;
                }
                initWebSocket();
            };
        } catch (err) {
            console.error("Eroare acces cameră:", err);
            if (statusElement) {
                statusElement.innerText = "Eroare: Acces Cameră Refuzat";
                statusElement.className = "badge bg-danger";
            }
        }
    }

    // 4. Funcția de inițializare WebSocket
    function initWebSocket() {
        socket = new WebSocket(socketUrl);

        socket.onopen = () => {
            console.log("✅ Conexiune WebSocket stabilită!");
            if (statusElement) {
                statusElement.innerText = "Sistem Live - Conectat";
                statusElement.className = "badge bg-success";
            }
            startStreaming();
        };

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            // Actualizăm UI-ul cu datele de la AI
            if (data.player && playerNameElement) playerNameElement.innerText = data.player;
            if (data.stats && data.stats.elbow_angle && elbowAngleElement) {
                elbowAngleElement.innerText = data.stats.elbow_angle + "°";
            }

            // Desenăm scheletul primit de la RTMPose
            if (data.keypoints && overlayCtx) {
                drawSkeleton(data.keypoints);
            }
        };

        socket.onclose = () => {
            console.warn("❌ WebSocket deconectat. Reîncercare în 3s...");
            if (statusElement) {
                statusElement.innerText = "Deconectat - Reconectare...";
                statusElement.className = "badge bg-warning";
            }
            setTimeout(initWebSocket, 3000);
        };

        socket.onerror = (error) => {
            console.error("Eroare WebSocket:", error);
        };
    }

    // 5. Trimiterea cadrelor către server
    function startStreaming() {
        setInterval(() => {
            if (socket.readyState === WebSocket.OPEN && video.readyState === video.HAVE_ENOUGH_DATA) {
                hiddenCanvas.width = 640;
                hiddenCanvas.height = 480;
                hiddenCtx.drawImage(video, 0, 0, 640, 480);
                
                // Compresie JPEG 50% pentru a nu bloca conexiunea la sală
                const frameData = hiddenCanvas.toDataURL('image/jpeg', 0.5);
                setInterval(() => {
                    if (socket.readyState === WebSocket.OPEN && video.readyState === video.HAVE_ENOUGH_DATA) {
                    hiddenCtx.drawImage(video, 0, 0, 640, 480);
                    const frameData = hiddenCanvas.toDataURL('image/jpeg', 0.5);
                    // Cream pachetul de date
                    const payload = {
                    image: frameData,
                    settings: {
                    face: document.getElementById('toggle_face').checked,
                    pose: document.getElementById('toggle_pose').checked
                    }
                    };
                    socket.send(JSON.stringify(payload));
                    }
                    }, 80);

            }
        }, 100); // ~10 FPS
    }

    // 6. Desenarea scheletului pe overlay
    function drawSkeleton(keypoints) {
    const overlay = document.getElementById('skeleton_overlay');
    if (!overlay) return;
    const ctx = overlay.getContext('2d');
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    // Definim conexiunile scheletului (perechi de indexuri de puncte)
    const connections = [[5, 7], [7, 9], [6, 8], [8, 10], [5, 6], [5, 11], [6, 12], [11, 12]];

    ctx.strokeStyle = "#00FF00"; // Verde pentru oase
    ctx.lineWidth = 3;

    connections.forEach(([i, j]) => {
        if (keypoints[i] && keypoints[j]) {
            ctx.beginPath();
            ctx.moveTo(keypoints[i][0], keypoints[i][1]);
            ctx.lineTo(keypoints[j][0], keypoints[j][1]);
            ctx.stroke();
        }
    });

    // Desenăm punctele (articulațiile)
    keypoints.forEach(kp => {
        ctx.beginPath();
        ctx.arc(kp[0], kp[1], 4, 0, 2 * Math.PI);
        ctx.fillStyle = "#FF6600";
        ctx.fill();
    });
}	


    // Pornim totul
    setupCamera();
});
