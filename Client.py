# client_modifie.py
import socket
import json
import time


class QuizClient:
    def __init__(self, host='localhost', port=5555):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.MAX_CHUNK_SIZE = 1024  # Taille maximale des morceaux à recevoir

    def connecter(self, username):
        try:
            print(f"Tentative de connexion à {self.host}:{self.port}...")
            self.socket.connect((self.host, self.port))
            self.socket.sendall(username.encode('utf-8'))
            return True
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            return False

    def recevoir_donnees_par_morceaux(self):
        """Reçoit des données par morceaux"""
        # Recevoir d'abord la taille totale attendue
        size_data = self.socket.recv(16).decode('utf-8').strip()
        if not size_data:
            return None

        try:
            total_size = int(size_data)
            # Confirmer la réception de la taille
            self.socket.sendall("OK".encode('utf-8').ljust(16))

            # Recevoir les données par morceaux
            received_data = b""
            remaining = total_size

            while remaining > 0:
                chunk_size = min(self.MAX_CHUNK_SIZE, remaining)
                chunk = self.socket.recv(chunk_size)
                if not chunk:
                    break

                received_data += chunk
                remaining -= len(chunk)

            # Décoder et charger les données JSON
            return json.loads(received_data.decode('utf-8'))

        except Exception as e:
            print(f"Erreur lors de la réception des données: {e}")
            return None

    def envoyer_donnees_par_morceaux(self, data):
        """Envoie des données par petits morceaux pour éviter les problèmes de taille"""
        # Convertir les données en JSON et encoder
        data_encoded = json.dumps(data).encode('utf-8')
        # Obtenir la taille totale
        total_size = len(data_encoded)
        # Envoyer d'abord la taille totale pour que le serveur sache combien attendre
        self.socket.sendall(f"{total_size}".encode('utf-8').ljust(16))
        # Petite pause pour s'assurer que le serveur est prêt à recevoir
        time.sleep(0.1)

        # Envoyer les données par morceaux
        for i in range(0, total_size, self.MAX_CHUNK_SIZE):
            chunk = data_encoded[i:i + self.MAX_CHUNK_SIZE]
            self.socket.sendall(chunk)
            # Petite pause entre les morceaux
            time.sleep(0.01)

        # Attendre confirmation de réception complète
        return self.socket.recv(16).decode('utf-8').strip() == "OK"

    def recevoir_questions(self):
        try:
            questions = self.recevoir_donnees_par_morceaux()
            return questions
        except Exception as e:
            print(f"Erreur lors de la réception des questions: {e}")
            return None

    def envoyer_reponses(self, answers):
        try:
            return self.envoyer_donnees_par_morceaux(answers)
        except Exception as e:
            print(f"Erreur lors de l'envoi des réponses: {e}")
            return False

    def recevoir_resultats(self):
        try:
            resultats = self.recevoir_donnees_par_morceaux()
            return resultats
        except Exception as e:
            print(f"Erreur lors de la réception des résultats: {e}")
            return None

    def fermer(self):
        self.socket.close()


def afficher_question(question, num_question):
    print(f"\nQuestion {num_question + 1}: {question['question']}")
    for i, option in enumerate(question['options']):
        print(f"  {i + 1}. {option}")


def afficher_resultats(resultats, username):
    print("\n===== RÉSULTATS DU QUIZ =====")

    # Trouver mon résultat
    mon_resultat = None
    for resultat in resultats:
        if resultat["username"] == username:
            mon_resultat = resultat
            break

    if mon_resultat:
        print(f"\nVotre score: {mon_resultat['score']}")
        print(f"Votre rang: {mon_resultat['rank']} sur {len(resultats)}")

        print("\nDétail de vos réponses:")
        for correctif in mon_resultat["correctifs"]:
            q_idx = correctif["question_index"]
            question = None

            # Obtenir la question correspondante
            if "questions_global" in globals():
                question = questions_global[q_idx]

            user_answer_idx = correctif["user_answer"]
            correct_answer_idx = correctif["correct_answer"]

            if question:
                print(f"\nQuestion {q_idx + 1}: {question['question']}")

                for i, option in enumerate(question["options"]):
                    prefix = "   "
                    if i == user_answer_idx and i == correct_answer_idx:
                        prefix = " ✓ "  # Bonne réponse choisie
                    elif i == user_answer_idx:
                        prefix = " ✗ "  # Mauvaise réponse choisie
                    elif i == correct_answer_idx:
                        prefix = " → "  # Bonne réponse non choisie

                    print(f"{prefix}{i + 1}. {option}")
            else:
                print(f"\nQuestion {q_idx + 1}: ")
                if user_answer_idx == correct_answer_idx:
                    print(f" ✓ Votre réponse ({user_answer_idx + 1}) était correcte")
                else:
                    print(f" ✗ Votre réponse était {user_answer_idx + 1}")
                    print(f" → La bonne réponse était {correct_answer_idx + 1}")

    print("\nClassement général:")
    for i, resultat in enumerate(resultats):
        print(f"{i + 1}. {resultat['username']} - Score: {resultat['score']}")


def main():
    print("=== QUIZ CLIENT ===")
    username = input("Entrez votre nom d'utilisateur: ")
    
    # Demander l'adresse IP du serveur
    server_ip = input("Entrez l'adresse IP du serveur (laissez vide pour localhost): ")
    if not server_ip:
        server_ip = 'localhost'
    
    # Optionnel: permettre de changer le port
    port_str = input("Entrez le port du serveur (laissez vide pour 5555): ")
    port = 5555
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            print("Port invalide, utilisation du port par défaut 5555")
    
    client = QuizClient(host=server_ip, port=port)
    if not client.connecter(username):
        print("Impossible de se connecter au serveur. Veuillez réessayer plus tard.")
        return

    print("Connecté au serveur avec succès.")
    print("Réception des questions en cours...")

    questions = client.recevoir_questions()
    if not questions:
        print("Erreur lors de la réception des questions.")
        client.fermer()
        return

    print(f"Réception réussie de {len(questions)} questions.")

    global questions_global
    questions_global = questions

    answers = []

    for i, question in enumerate(questions):
        afficher_question(question, i)

        while True:
            try:
                choix = int(input("Votre réponse (1-4): "))
                if 1 <= choix <= len(question['options']):
                    # Convertir le choix de l'utilisateur en index (0-3)
                    answers.append(choix - 1)
                    break
                else:
                    print(f"Veuillez entrer un nombre entre 1 et {len(question['options'])}.")
            except ValueError:
                print("Veuillez entrer un nombre valide.")

    print("\nVos réponses ont été enregistrées. En attente que tous les participants terminent...")

    if not client.envoyer_reponses(answers):
        print("Erreur lors de l'envoi des réponses.")
        client.fermer()
        return

    print("En attente des résultats...")
    resultats = client.recevoir_resultats()
    if not resultats:
        print("Erreur lors de la réception des résultats.")
        client.fermer()
        return

    afficher_resultats(resultats, username)

    print("\nMerci d'avoir participé au quiz!")
    client.fermer()


if __name__ == "__main__":
    main()