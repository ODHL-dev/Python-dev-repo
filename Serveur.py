import socket
import threading
import json
import time
import random
from queue import Queue

class FightingGameServer:
    def __init__(self, host="0.0.0.0", port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.clients = {}  # {client_id: (connection, address, username, role)}
        self.matches = {}  # {match_id: {players: [], spectators: [], state: {}, updates_queue: Queue()}}
        self.waiting_players = []  # Liste des joueurs en attente
        self.client_id_counter = 0
        self.match_id_counter = 0
        
    def start(self):
        self.server_socket.listen(5)
        print(f"Serveur démarré sur {self.host}:{self.port}")
        
        # Thread pour créer des matchs automatiquement
        matchmaking_thread = threading.Thread(target=self.matchmaking)
        matchmaking_thread.daemon = True
        matchmaking_thread.start()
        
        while True:
            client_socket, address = self.server_socket.accept()
            client_id = self.client_id_counter
            self.client_id_counter += 1
            
            client_thread = threading.Thread(target=self.handle_client, 
                                           args=(client_socket, address, client_id))
            client_thread.daemon = True
            client_thread.start()
            print(f"Nouvelle connexion: {address}, ID: {client_id}")
    
    def matchmaking(self):
        """Crée des matchs automatiquement quand il y a au moins 2 joueurs en attente"""
        while True:
            if len(self.waiting_players) >= 2:
                player1_id = self.waiting_players.pop(0)
                player2_id = self.waiting_players.pop(0)
                
                if player1_id in self.clients and player2_id in self.clients:
                    self.create_match(player1_id, player2_id)
            
            time.sleep(1)
    
    def create_match(self, player1_id, player2_id):
        """Crée un nouveau match entre deux joueurs"""
        match_id = self.match_id_counter
        self.match_id_counter += 1
        
        # Initialisation de l'état du match
        match_state = {
            "players": {
                player1_id: {
                    "position": [100, 300],
                    "health": 100,
                    "facing": "right",
                    "action": "idle",
                    "username": self.clients[player1_id][2]
                },
                player2_id: {
                    "position": [700, 300],
                    "health": 100,
                    "facing": "left",
                    "action": "idle",
                    "username": self.clients[player2_id][2]
                }
            },
            "match_id": match_id,
            "status": "starting",
            "countdown": 3,
            "winner": None
        }
        
        # Création du match
        self.matches[match_id] = {
            "players": [player1_id, player2_id],
            "spectators": [],
            "state": match_state,
            "updates_queue": Queue()
        }
        
        # Informer les joueurs du début du match
        for player_id in [player1_id, player2_id]:
            conn = self.clients[player_id][0]
            self.send_message(conn, {
                "type": "match_start",
                "match_id": match_id,
                "player_id": player_id,
                "opponent_id": player2_id if player_id == player1_id else player1_id,
                "match_state": match_state
            })
            
            # Mise à jour du rôle
            client_info = list(self.clients[player_id])
            client_info[3] = "player"
            self.clients[player_id] = tuple(client_info)
        
        print(f"Match {match_id} créé entre les joueurs {player1_id} et {player2_id}")
        
        # Lancer le thread de gestion du match
        match_thread = threading.Thread(target=self.handle_match, args=(match_id,))
        match_thread.daemon = True
        match_thread.start()
    
    def handle_match(self, match_id):
        """Gère le déroulement d'un match"""
        match = self.matches[match_id]
        
        # Compte à rebours avant le début du match
        for i in range(3, 0, -1):
            match["state"]["countdown"] = i
            self.broadcast_match_state(match_id)
            time.sleep(1)
        
        # Le match commence
        match["state"]["status"] = "running"
        match["state"]["countdown"] = 0
        self.broadcast_match_state(match_id)
        
        # Boucle principale du match
        while match["state"]["status"] == "running":
            # Traitement des mises à jour reçues des joueurs
            while not match["updates_queue"].empty():
                update = match["updates_queue"].get()
                self.process_player_action(match_id, update)
            
            # Vérifier si un joueur a gagné
            self.check_match_end(match_id)
            
            # Diffuser l'état actuel du match
            self.broadcast_match_state(match_id)
            
            time.sleep(0.05)  # 50ms pour ~20 FPS
        
        # Le match est terminé
        time.sleep(5)  # Attendre 5 secondes avant de nettoyer le match
        
        # Supprimer le match
        if match_id in self.matches:
            del self.matches[match_id]
            print(f"Match {match_id} terminé et supprimé")
    
    def process_player_action(self, match_id, update):
        """Traite une action de joueur et met à jour l'état du match"""
        if match_id not in self.matches:
            return
            
        match = self.matches[match_id]
        player_id = update["player_id"]
        action = update["action"]
        
        # Vérifier que le joueur participe au match
        if player_id not in match["players"]:
            return
            
        player_state = match["state"]["players"][player_id]
        
        # Traiter les actions du joueur
        if action["type"] == "move":
            # Mise à jour de la position du joueur
            new_pos_x = player_state["position"][0] + action["dx"]
            # Garder le joueur dans les limites de l'écran
            new_pos_x = max(50, min(750, new_pos_x))
            player_state["position"][0] = new_pos_x
            
            # Mise à jour de l'orientation
            if action["dx"] > 0:
                player_state["facing"] = "right"
            elif action["dx"] < 0:
                player_state["facing"] = "left"
                
            player_state["action"] = "walking" if action["dx"] != 0 else "idle"
            
        elif action["type"] == "attack":
            player_state["action"] = "attacking"
            
            # Pour chaque joueur adverse
            for opponent_id in match["players"]:
                if opponent_id != player_id:
                    opponent_state = match["state"]["players"][opponent_id]
                    
                    # Distance entre les joueurs
                    distance = abs(player_state["position"][0] - opponent_state["position"][0])
                    
                    # Si l'adversaire est dans la portée d'attaque
                    if distance < 150:
                        # Vérifier si le joueur fait face à l'adversaire
                        facing_correctly = (player_state["facing"] == "right" and 
                                           player_state["position"][0] < opponent_state["position"][0]) or \
                                           (player_state["facing"] == "left" and 
                                           player_state["position"][0] > opponent_state["position"][0])
                        
                        if facing_correctly:
                            # Infliger des dégâts
                            damage = random.randint(5, 15)
                            opponent_state["health"] = max(0, opponent_state["health"] - damage)
                            print(f"Joueur {player_id} inflige {damage} dégâts au joueur {opponent_id}")
    
    def check_match_end(self, match_id):
        """Vérifie si un match est terminé"""
        if match_id not in self.matches:
            return
            
        match = self.matches[match_id]
        players = match["state"]["players"]
        
        for player_id, player_state in players.items():
            if player_state["health"] <= 0:
                # Trouver le vainqueur
                winner_id = next(pid for pid in players.keys() if pid != player_id)
                
                match["state"]["status"] = "finished"
                match["state"]["winner"] = winner_id
                print(f"Match {match_id} terminé. Vainqueur: {winner_id}")
                return
    
    def broadcast_match_state(self, match_id):
        """Diffuse l'état actuel du match à tous les participants et spectateurs"""
        if match_id not in self.matches:
            return
            
        match = self.matches[match_id]
        
        # Préparer le message
        message = {
            "type": "match_update",
            "match_id": match_id,
            "state": match["state"]
        }
        
        # Diffuser aux joueurs et spectateurs
        for player_id in match["players"] + match["spectators"]:
            if player_id in self.clients:
                conn = self.clients[player_id][0]
                self.send_message(conn, message)
    
    def handle_client(self, client_socket, address, client_id):
        """Gère la connexion avec un client"""
        # Initialiser le client comme spectateur par défaut
        self.clients[client_id] = (client_socket, address, f"Joueur_{client_id}", "spectator")
        
        try:
            # Envoyer l'ID du client
            self.send_message(client_socket, {
                "type": "welcome",
                "client_id": client_id
            })
            
            while True:
                data = self.receive_message(client_socket)
                if not data:
                    break
                
                self.handle_message(client_id, data)
                
        except Exception as e:
            print(f"Erreur avec le client {client_id}: {e}")
        finally:
            # Nettoyage du client
            self.handle_client_disconnect(client_id)
            client_socket.close()
    
    def handle_message(self, client_id, message):
        """Traite un message reçu d'un client"""
        msg_type = message.get("type", "")
        
        if msg_type == "set_username":
            # Mise à jour du nom d'utilisateur
            username = message.get("username", f"Joueur_{client_id}")
            client_info = list(self.clients[client_id])
            client_info[2] = username
            self.clients[client_id] = tuple(client_info)
            
            # Confirmer la mise à jour
            self.send_message(self.clients[client_id][0], {
                "type": "username_set",
                "username": username
            })
            
        elif msg_type == "request_match_list":
            # Envoyer la liste des matchs en cours
            match_list = []
            for match_id, match in self.matches.items():
                match_info = {
                    "match_id": match_id,
                    "status": match["state"]["status"],
                    "players": [self.clients[pid][2] for pid in match["players"] if pid in self.clients]
                }
                match_list.append(match_info)
            
            self.send_message(self.clients[client_id][0], {
                "type": "match_list",
                "matches": match_list
            })
            
        elif msg_type == "join_queue":
            # Ajouter le joueur à la file d'attente
            if client_id not in self.waiting_players:
                self.waiting_players.append(client_id)
                print(f"Joueur {client_id} ajouté à la file d'attente")
                
                # Confirmer au client
                self.send_message(self.clients[client_id][0], {
                    "type": "queue_joined"
                })
                
        elif msg_type == "leave_queue":
            # Retirer le joueur de la file d'attente
            if client_id in self.waiting_players:
                self.waiting_players.remove(client_id)
                print(f"Joueur {client_id} retiré de la file d'attente")
                
                # Confirmer au client
                self.send_message(self.clients[client_id][0], {
                    "type": "queue_left"
                })
                
        elif msg_type == "spectate_match":
            # Rejoindre un match en tant que spectateur
            match_id = message.get("match_id")
            if match_id in self.matches:
                if client_id not in self.matches[match_id]["players"] and \
                   client_id not in self.matches[match_id]["spectators"]:
                    self.matches[match_id]["spectators"].append(client_id)
                    
                    # Mettre à jour le rôle du client
                    client_info = list(self.clients[client_id])
                    client_info[3] = "spectator"
                    self.clients[client_id] = tuple(client_info)
                    
                    # Envoyer l'état actuel du match
                    self.send_message(self.clients[client_id][0], {
                        "type": "match_joined",
                        "match_id": match_id,
                        "state": self.matches[match_id]["state"]
                    })
                    
                    print(f"Joueur {client_id} spectateur du match {match_id}")
                    
        elif msg_type == "game_action":
            # Transmettre l'action au gestionnaire de match
            match_id = message.get("match_id")
            if match_id in self.matches and client_id in self.matches[match_id]["players"]:
                self.matches[match_id]["updates_queue"].put({
                    "player_id": client_id,
                    "action": message.get("action", {})
                })
    
    def handle_client_disconnect(self, client_id):
        """Gère la déconnexion d'un client"""
        if client_id in self.clients:
            print(f"Client {client_id} déconnecté")
            
            # Retirer de la file d'attente
            if client_id in self.waiting_players:
                self.waiting_players.remove(client_id)
            
            # Vérifier si le client est dans un match
            for match_id, match in list(self.matches.items()):
                if client_id in match["players"]:
                    # Si c'est un joueur, terminer le match
                    opponent_id = next((pid for pid in match["players"] if pid != client_id), None)
                    if opponent_id:
                        match["state"]["status"] = "finished"
                        match["state"]["winner"] = opponent_id
                        print(f"Match {match_id} terminé suite à la déconnexion du joueur {client_id}")
                        self.broadcast_match_state(match_id)
                elif client_id in match["spectators"]:
                    # Si c'est un spectateur, le retirer
                    match["spectators"].remove(client_id)
            
            # Supprimer le client
            del self.clients[client_id]
    
    def send_message(self, connection, message):
        """Envoie un message à un client"""
        try:
            data = json.dumps(message).encode('utf-8')
            message_length = len(data).to_bytes(4, byteorder='big')
            connection.sendall(message_length + data)
        except Exception as e:
            print(f"Erreur d'envoi: {e}")
            
    def receive_message(self, connection):
        """Reçoit un message d'un client"""
        try:
            # Recevoir la taille du message
            message_length_bytes = connection.recv(4)
            if not message_length_bytes:
                return None
                
            message_length = int.from_bytes(message_length_bytes, byteorder='big')
            
            # Recevoir le message complet
            chunks = []
            bytes_received = 0
            while bytes_received < message_length:
                chunk = connection.recv(min(message_length - bytes_received, 4096))
                if not chunk:
                    return None
                chunks.append(chunk)
                bytes_received += len(chunk)
                
            data = b''.join(chunks)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"Erreur de réception: {e}")
            return None

if __name__ == "__main__":
    server = FightingGameServer()
    server.start()