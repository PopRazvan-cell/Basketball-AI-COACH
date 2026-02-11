import face_recognition
import cv2
import numpy as np
import os
import pickle

class BasketballProcessor:
    def __init__(self, profiles_dir="app/profiles"):
        self.known_face_encodings = []
        self.known_face_names = []
        self.load_profiles(profiles_dir)
        print("[Processor] Motorul AI a pornit. Profile încărcate.")

    def load_profiles(self, profiles_dir):
        """Încarcă toate profilele .pkl la pornirea serverului."""
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
            return

        for filename in os.listdir(profiles_dir):
            if filename.endswith(".pkl"):
                name = filename.replace(".pkl", "").replace("_", " ")
                path = os.path.join(profiles_dir, filename)
                try:
                    with open(path, "rb") as f:
                        encoding = pickle.load(f)
                        self.known_face_encodings.append(encoding)
                        self.known_face_names.append(name)
                    print(f"[Processor] Profil încărcat: {name}")
                except Exception as e:
                    print(f"[Processor] Eroare la încărcarea {filename}: {e}")

    def process_frame(self, frame):
        """
        Primește un cadru video (OpenCV BGR), caută fețe și le identifică.
        """
        # 1. Reducem dimensiunea pentru viteză (opțional, ajută la FPS)
        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        
        # 2. Convertim BGR (OpenCV) la RGB (face_recognition)
        rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        # 3. Găsim fețele în cadru
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

        detected_player = None
        status = "Căutare..."

        # 4. Comparăm fețele găsite cu cele cunoscute
        for face_encoding in face_encodings:
            # Toleranța 0.6 este standard. Mai mic = mai strict.
            matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.6)
            
            if True in matches:
                first_match_index = matches.index(True)
                detected_player = self.known_face_names[first_match_index]
                status = "Identificat"
                # Odată găsit un jucător, ne oprim (presupunem un singur jucător activ)
                break

        # AICI vom adăuga RTMPose în viitor
        # keypoints = self.rtmpose_model(frame) 

        return {
            "player": detected_player,
            "status": status,
            # "keypoints": keypoints # Deocamdată trimitem gol
        }
