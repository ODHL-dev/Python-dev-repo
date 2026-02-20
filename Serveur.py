# serveur.py
import socket
import threading
import json
import time
import os
import datetime


class QuizServeur:
    # Changez ceci dans la classe QuizServeur
    def __init__(self, host='0.0.0.0', port=5555, questions_file='questions.json', results_file='resultats.json'):
        self.host = host
        self.port = port
        self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_serveur.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket_serveur.bind((self.host, self.port))
        self.clients = {}  # {client_id: {"connection": conn, "username": username, "answers": [], "score": 0}}
        self.questions_file = questions_file
        self.results_file = results_file
        self.questions = self.charger_questions(questions_file)
        self.lock = threading.Lock()
        self.tous_ont_repondu = False
        self.resultats = []
        self.client_count = 0
        self.session_id = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        self.MAX_CHUNK_SIZE = 1024  # Taille maximale des morceaux à envoyer

    def charger_questions(self, fichier):
        try:
            if not os.path.exists(fichier):
                print(f"Le fichier {fichier} n'existe pas. Création d'un fichier d'exemple.")
                self.creer_fichier_questions_exemple(fichier)

            with open(fichier, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('questions', [])
        except Exception as e:
            print(f"Erreur lors du chargement des questions: {e}")
            print("Utilisation des questions par défaut.")
            return self.questions_par_defaut()

    def creer_fichier_questions_exemple(self, fichier):
        questions = {
            "questions": self.questions_par_defaut()
        }
        try:
            with open(fichier, 'w', encoding='utf-8') as f:
                json.dump(questions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur lors de la création du fichier d'exemple: {e}")

    def questions_par_defaut(self):
        return [
            {"question": "Quelle est la capitale de la France?",
             "options": ["Paris", "Londres", "Berlin", "Madrid"],
             "correct_answer": 0},
            {"question": "Combien de continents y a-t-il?",
             "options": ["5", "6", "7", "8"],
             "correct_answer": 2},
            {"question": "Quel est le plus grand océan du monde?",
             "options": ["Atlantique", "Indien", "Arctique", "Pacifique"],
             "correct_answer": 3},
            {"question": "Qui a peint la Joconde?",
             "options": ["Van Gogh", "Picasso", "Leonard de Vinci", "Michel-Ange"],
             "correct_answer": 2},
            {"question": "Quelle est la planète la plus proche du soleil?",
             "options": ["Terre", "Venus", "Mars", "Mercure"],
             "correct_answer": 3}
        ]

    def demarrer(self):
        print(f"Serveur démarré sur {self.host}:{self.port}")
        print(f"Nombre de questions chargées: {len(self.questions)}")
        print(f"ID de session: {self.session_id}")
        self.socket_serveur.listen(5)

        while True:
            conn, addr = self.socket_serveur.accept()
            client_id = self.client_count
            self.client_count += 1

            client_thread = threading.Thread(target=self.gerer_client, args=(conn, client_id))
            client_thread.daemon = True
            client_thread.start()

            print(f"Nouvelle connexion: {addr}, ID: {client_id}")

    def envoyer_donnees_par_morceaux(self, conn, data):
        """Envoie des données par petits morceaux pour éviter les problèmes de taille"""
        # Convertir les données en JSON et encoder
        data_encoded = json.dumps(data).encode('utf-8')
        # Obtenir la taille totale
        total_size = len(data_encoded)
        # Envoyer d'abord la taille totale pour que le client sache combien attendre
        conn.sendall(f"{total_size}".encode('utf-8').ljust(16))
        # Petite pause pour s'assurer que le client est prêt à recevoir
        time.sleep(0.1)

        # Envoyer les données par morceaux
        for i in range(0, total_size, self.MAX_CHUNK_SIZE):
            chunk = data_encoded[i:i + self.MAX_CHUNK_SIZE]
            conn.sendall(chunk)
            # Petite pause entre les morceaux
            time.sleep(0.01)

        # Attendre confirmation de réception complète
        return conn.recv(16).decode('utf-8').strip() == "OK"

    def recevoir_donnees_par_morceaux(self, conn):
        """Reçoit des données par morceaux"""
        # Recevoir d'abord la taille totale attendue
        size_data = conn.recv(16).decode('utf-8').strip()
        if not size_data:
            return None

        try:
            total_size = int(size_data)
            # Confirmer la réception de la taille
            conn.sendall("OK".encode('utf-8').ljust(16))

            # Recevoir les données par morceaux
            received_data = b""
            remaining = total_size

            while remaining > 0:
                chunk_size = min(self.MAX_CHUNK_SIZE, remaining)
                chunk = conn.recv(chunk_size)
                if not chunk:
                    break

                received_data += chunk
                remaining -= len(chunk)

            # Décoder et charger les données JSON
            return json.loads(received_data.decode('utf-8'))

        except Exception as e:
            print(f"Erreur lors de la réception des données: {e}")
            return None

    def gerer_client(self, conn, client_id):
        try:
            # Recevoir le nom d'utilisateur
            data = conn.recv(1024)
            username = data.decode('utf-8')

            with self.lock:
                self.clients[client_id] = {
                    "connection": conn,
                    "username": username,
                    "answers": [],
                    "score": 0,
                    "finished": False
                }

            # Envoyer les questions par morceaux
            if not self.envoyer_donnees_par_morceaux(conn, self.questions):
                print(f"Problème lors de l'envoi des questions au client {client_id}")
                return

            # Recevoir les réponses par morceaux
            answers = self.recevoir_donnees_par_morceaux(conn)
            if answers is None:
                print(f"Problème lors de la réception des réponses du client {client_id}")
                return

            score = self.calculer_score(answers)

            with self.lock:
                self.clients[client_id]["answers"] = answers
                self.clients[client_id]["score"] = score
                self.clients[client_id]["finished"] = True

                # Vérifier si tous les clients ont terminé
                tous_fini = all(client["finished"] for client in self.clients.values())

                if tous_fini and not self.tous_ont_repondu:
                    self.tous_ont_repondu = True
                    self.envoyer_resultats()

        except Exception as e:
            print(f"Erreur avec le client {client_id}: {e}")
            with self.lock:
                if client_id in self.clients:
                    del self.clients[client_id]

    def calculer_score(self, answers):
        score = 0
        for i, answer in enumerate(answers):
            if i < len(self.questions) and answer == self.questions[i]["correct_answer"]:
                score += 1
        return score

    def envoyer_resultats(self):
        # Trier les clients par score
        resultats = []
        for client_id, client in self.clients.items():
            resultats.append({
                "id": client_id,
                "username": client["username"],
                "score": client["score"],
                "answers": client["answers"]
            })

        # Trier par score décroissant
        resultats.sort(key=lambda x: x["score"], reverse=True)

        # Ajouter le rang
        for i, result in enumerate(resultats):
            result["rank"] = i + 1

        # Ajouter les correctifs
        for result in resultats:
            correctifs = []
            for i, answer in enumerate(result["answers"]):
                if i < len(self.questions):
                    correct = answer == self.questions[i]["correct_answer"]
                    correctifs.append({
                        "question_index": i,
                        "user_answer": answer,
                        "correct_answer": self.questions[i]["correct_answer"],
                        "is_correct": correct
                    })
            result["correctifs"] = correctifs

        # Envoyer les résultats à tous les clients par morceaux
        for client_id, client in self.clients.items():
            try:
                self.envoyer_donnees_par_morceaux(client["connection"], resultats)
            except:
                print(f"Erreur lors de l'envoi des résultats au client {client_id}")

        # Sauvegarder les résultats
        self.sauvegarder_resultats(resultats)

    def sauvegarder_resultats(self, resultats):
        # Créer une structure de données pour la sauvegarde
        resultats_a_sauvegarder = {
            "session_id": self.session_id,
            "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "quiz_file": self.questions_file,
            "nombre_participants": len(resultats),
            "resultats": []
        }

        # Ajouter les résultats simplifiés (sans les correctifs détaillés)
        for resultat in resultats:
            resultats_a_sauvegarder["resultats"].append({
                "username": resultat["username"],
                "score": resultat["score"],
                "rank": resultat["rank"],
                "total_questions": len(self.questions),
                "pourcentage_reussite": round((resultat["score"] / len(self.questions)) * 100, 2) if len(
                    self.questions) > 0 else 0
            })

        try:
            # Charger les résultats existants si le fichier existe
            historique = []
            if os.path.exists(self.results_file):
                try:
                    with open(self.results_file, 'r', encoding='utf-8') as f:
                        historique = json.load(f)
                        if not isinstance(historique, list):
                            historique = []
                except:
                    historique = []

            # Ajouter les nouveaux résultats et sauvegarder
            historique.append(resultats_a_sauvegarder)

            with open(self.results_file, 'w', encoding='utf-8') as f:
                json.dump(historique, f, ensure_ascii=False, indent=2)

            print(f"Résultats sauvegardés dans {self.results_file}")

        except Exception as e:
            print(f"Erreur lors de la sauvegarde des résultats: {e}")


if __name__ == "__main__":
    # On peut spécifier un fichier de questions et de résultats en argument
    import sys

    questions_file = 'questions.json'
    results_file = 'resultats.json'

    if len(sys.argv) > 1:
        questions_file = sys.argv[1]
    if len(sys.argv) > 2:
        results_file = sys.argv[2]

    serveur = QuizServeur(questions_file=questions_file, results_file=results_file)
    serveur.demarrer()