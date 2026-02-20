import face_recognition
import cv2
import numpy as np
import os
import pickle
import onnxruntime as ort

class BasketballProcessor:
    def __init__(self, profiles_dir="/app/app/profiles", model_path="/app/models/rtmpose-m.onnx"):
        self.known_face_encodings = []
        self.known_face_names = []
        self.profiles_dir = profiles_dir
        self.load_profiles()
        
        # Inițializare ONNX Runtime pentru RTMPose
        try:
            # Folosim CPU (sau CUDA dacă ai GPU configurat în Docker)
            self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            self.input_name = self.session.get_inputs()[0].name
            print(f"[AI] RTMPose încărcat cu succes din {model_path}")
        except Exception as e:
            self.session = None
            print(f"[EROARE AI] Nu s-a putut încărca modelul ONNX: {e}")

    def load_profiles(self):
        """Încarcă sau reîncarcă profilele faciale din fișierele .pkl."""
        self.known_face_encodings = []
        self.known_face_names = []
        
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir)
            return

        for filename in os.listdir(self.profiles_dir):
            if filename.endswith(".pkl"):
                name = filename.replace(".pkl", "").replace("_", " ")
                path = os.path.join(self.profiles_dir, filename)
                try:
                    with open(path, "rb") as f:
                        encoding = pickle.load(f)
                        self.known_face_encodings.append(encoding)
                        self.known_face_names.append(name)
                except Exception as e:
                    print(f"Eroare la încărcarea profilului {filename}: {e}")
        print(f"[FaceID] {len(self.known_face_names)} profile încărcate.")

    def calculate_angle(self, a, b, c):
        """Calculează unghiul format de 3 puncte (ex: umăr, cot, încheietură)."""
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return int(np.degrees(angle))

    def process_frame(self, frame):
        """Procesează un cadru: Identificare față + Detecție Schelet + Calcule."""
        
        self.frame_count += 1
        player_name = self.last_player
        keypoints = []
        
        if run_face:
            if self.frame_count % 30 == 0:

                h_orig, w_orig = frame.shape[:2]
                
                # 1. FACE RECOGNITION (FaceID)
                # Reducem cadrul pentru a crește viteza de procesare
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                face_locations = face_recognition.face_locations(rgb_small)
                face_encodings = face_recognition.face_encodings(rgb_small, face_locations)

                player_name = "Căutare..."
                for face_encoding in face_encodings:
                    matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
                    if True in matches:
                        first_match_index = matches.index(True)
                        player_name = self.known_face_names[first_match_index]
                        break
                pass
        else:
                player_name = "N/A"
        if run_pose and self.session:        


            # 2. RTMPose (POSE ESTIMATION)
            keypoints = []
            stats = {"elbow_angle": 0}
            
            if self.session:
                # Pre-procesare imagine pentru RTMPose (Input standard: 192x256)
                input_size = (192, 256) # (width, height)
                img_input = cv2.resize(frame, input_size)
                img_input = cv2.cvtColor(img_input, cv2.COLOR_BGR2RGB)
                img_input = img_input.transpose(2, 0, 1).astype(np.float32) / 255.0
                img_input = np.expand_dims(img_input, axis=0)

                # Execuție Model ONNX (SimCC Output)
                outputs = self.session.run(None, {self.input_name: img_input})
                # RTMPose returnează de obicei două array-uri pentru X și Y (SimCC decoding)
                simcc_x, simcc_y = outputs[0], outputs[1]

                # Decodăm punctele (cele 17 puncte standard COCO)
                for i in range(17):
                    # Găsim indexul cu probabilitatea maximă
                    x_idx = np.argmax(simcc_x[0, i])
                    y_idx = np.argmax(simcc_y[0, i])
                    
                    # Scalăm indexul la dimensiunea originală a imaginii
                    # SimCC folosește un factor de multiplicare (de obicei 2) față de input
                    x = int(x_idx * (w_orig / (input_size[0] * 2)))
                    y = int(y_idx * (h_orig / (input_size[1] * 2)))
                    
                    keypoints.append([x, y, 1.0]) # [x, y, confidence]

                # 3. BIOMECANICĂ (Calculul brațului drept)
                # Indexuri COCO: 6=Umăr Drept, 8=Cot Drept, 10=Încheietură Dreaptă
                if len(keypoints) > 10:
                    p_shoulder = keypoints[6][:2]
                    p_elbow = keypoints[8][:2]
                    p_wrist = keypoints[10][:2]
                    
                    # Verificăm dacă punctele sunt în cadru (nu sunt la 0,0)
                    if p_elbow[1] > 0 and p_wrist[1] > 0:
                        stats["elbow_angle"] = self.calculate_angle(p_shoulder, p_elbow, p_wrist)

            return {
                "player": player_name,
                "keypoints": keypoints,
                "stats": stats
            }
