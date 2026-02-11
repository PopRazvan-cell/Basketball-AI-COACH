import os
import pickle
import base64
import cv2
import numpy as np
from fastapi import FastAPI, Request, Form, File, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse

# --- MODIFICARE: Importăm procesorul ---
from app.processor import BasketballProcessor
# ---------------------------------------

app = FastAPI()
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

PROFILES_DIR = "app/profiles"

# --- MODIFICARE: Inițializăm procesorul global ---
# Se încarcă profilele o singură dată la pornirea serverului
processor = BasketballProcessor(PROFILES_DIR)
# -------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Reîncărcăm lista de fișiere pentru a afișa jucătorii noi
    players = [f.replace(".pkl", "").replace("_", " ") for f in os.listdir(PROFILES_DIR) if f.endswith(".pkl")]
    return templates.TemplateResponse("index.html", {"request": request, "players": players})

@app.get("/enroll", response_class=HTMLResponse)
async def enroll_page(request: Request):
    return templates.TemplateResponse("enroll.html", {"request": request})

# Ruta nouă pentru înrolarea cu camera web
@app.post("/enroll_camera")
async def enroll_camera(name: str = Form(...), image_data: str = Form(...)):
    import face_recognition
    # Curățăm numele de caractere problematice
    safe_name = "".join([c for c in name if c.isalnum() or c in [' ', '-', '_']]).strip().replace(" ", "_")
    
    try:
        header, encoded = image_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        nparr = np.frombuffer(binary_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        encodings = face_recognition.face_encodings(rgb_img)
        if encodings:
            with open(f"{PROFILES_DIR}/{safe_name}.pkl", "wb") as f:
                pickle.dump(encodings[0], f)
            
            # IMPORTANT: Reîncărcăm profilele în procesor după o înrolare nouă
            processor.load_profiles(PROFILES_DIR)
            
            return {"status": "success", "message": f"Jucătorul {name} a fost înrolat!"}
        else:
            return {"status": "error", "message": "Nu am detectat nicio față. Încearcă din nou cu lumină mai bună."}
    except Exception as e:
        return {"status": "error", "message": f"Eroare server: {str(e)}"}

@app.get("/live", response_class=HTMLResponse)
async def live_analysis(request: Request):
    return templates.TemplateResponse("live.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            header, encoded = data.split(",", 1)
            binary_data = base64.b64decode(encoded)
            nparr = np.frombuffer(binary_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            # --- MODIFICARE: Aici folosim procesorul! ---
            # Trimitem cadrul la analiză
            analysis_result = processor.process_frame(frame)
            
            # Trimitem rezultatul înapoi la browser
            await websocket.send_json(analysis_result)
            # --------------------------------------------

    except WebSocketDisconnect:
        print("Client deconectat.")
    except Exception as e:
        print(f"Eroare WebSocket: {e}")
        await websocket.close()
