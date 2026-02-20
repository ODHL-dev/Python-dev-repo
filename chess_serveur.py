# Fichier: chess_server.py
import socket
import threading
import json
import time
import random
import string

class ChessGame:
    def __init__(self, white_player, black_player, game_id):
        self.white_player = white_player
        self.black_player = black_player
        self.spectators = []
        self.game_id = game_id
        self.board = self.initialize_board()
        self.current_turn = 'white'
        self.history = []
        self.active = True
        
    def initialize_board(self):
        # Représente l'échiquier avec des pièces
        board = {}
        
        # Placement des pièces blanches
        board['a1'] = {'piece': 'rook', 'color': 'white'}
        board['b1'] = {'piece': 'knight', 'color': 'white'}
        board['c1'] = {'piece': 'bishop', 'color': 'white'}
        board['d1'] = {'piece': 'queen', 'color': 'white'}
        board['e1'] = {'piece': 'king', 'color': 'white'}
        board['f1'] = {'piece': 'bishop', 'color': 'white'}
        board['g1'] = {'piece': 'knight', 'color': 'white'}
        board['h1'] = {'piece': 'rook', 'color': 'white'}
        
        # Placement des pions blancs
        for col in 'abcdefgh':
            board[f'{col}2'] = {'piece': 'pawn', 'color': 'white'}
        
        # Placement des pièces noires
        board['a8'] = {'piece': 'rook', 'color': 'black'}
        board['b8'] = {'piece': 'knight', 'color': 'black'}
        board['c8'] = {'piece': 'bishop', 'color': 'black'}
        board['d8'] = {'piece': 'queen', 'color': 'black'}
        board['e8'] = {'piece': 'king', 'color': 'black'}
        board['f8'] = {'piece': 'bishop', 'color': 'black'}
        board['g8'] = {'piece': 'knight', 'color': 'black'}
        board['h8'] = {'piece': 'rook', 'color': 'black'}
        
        # Placement des pions noirs
        for col in 'abcdefgh':
            board[f'{col}7'] = {'piece': 'pawn', 'color': 'black'}
            
        return board
    
    def is_valid_move(self, from_pos, to_pos, color):
        # Vérifie si le mouvement est valide
        if from_pos not in self.board:
            return False
        
        piece = self.board[from_pos]
        if piece['color'] != color:
            return False
        
        # Vérification basique pour l'exemple
        # Une implémentation complète nécessiterait toutes les règles d'échecs
        piece_type = piece['piece']
        
        # Conversion des positions en coordonnées
        from_col = ord(from_pos[0]) - ord('a')
        from_row = int(from_pos[1]) - 1
        to_col = ord(to_pos[0]) - ord('a')
        to_row = int(to_pos[1]) - 1
        
        # Vérification sommaire des règles de mouvement
        if piece_type == 'pawn':
            # Simplifié, ne gère pas toutes les règles
            if color == 'white':
                if from_col == to_col and to_row == from_row + 1:
                    return to_pos not in self.board
                elif from_col == to_col and to_row == from_row + 2 and from_row == 1:
                    return to_pos not in self.board
                elif abs(from_col - to_col) == 1 and to_row == from_row + 1:
                    return to_pos in self.board and self.board[to_pos]['color'] == 'black'
            else:  # black
                if from_col == to_col and to_row == from_row - 1:
                    return to_pos not in self.board
                elif from_col == to_col and to_row == from_row - 2 and from_row == 6:
                    return to_pos not in self.board
                elif abs(from_col - to_col) == 1 and to_row == from_row - 1:
                    return to_pos in self.board and self.board[to_pos]['color'] == 'white'
        
        # Règles simplifiées pour d'autres pièces
        # Une implémentation complète serait beaucoup plus longue
        
        return True
    
    def make_move(self, from_pos, to_pos):
        if to_pos in self.board:
            captured = self.board[to_pos]
        else:
            captured = None
            
        self.board[to_pos] = self.board[from_pos]
        del self.board[from_pos]
        
        move_data = {
            'from': from_pos,
            'to': to_pos,
            'piece': self.board[to_pos],
            'captured': captured,
            'turn': self.current_turn
        }
        
        self.history.append(move_data)
        self.current_turn = 'black' if self.current_turn == 'white' else 'white'
        
        return move_data
    
    def get_game_state(self):
        return {
            'board': self.board,
            'current_turn': self.current_turn,
            'history': self.history,
            'active': self.active,
            'white_player': self.white_player,
            'black_player': self.black_player,
            'game_id': self.game_id
        }

class ChessServer:
    def __init__(self, host='0.0.0.0', port=5000):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = {}  # {client_id: (connection, username)}
        self.waiting_players = []  # Liste des joueurs en attente de partie
        self.games = {}  # {game_id: ChessGame}
        
    def start(self):
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(10)
        print(f"Serveur d'échecs démarré sur {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, address = self.server_socket.accept()
                client_id = self.generate_id()
                self.clients[client_id] = (client_socket, None)
                
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_id))
                client_thread.daemon = True
                client_thread.start()
                
        except KeyboardInterrupt:
            print("Arrêt du serveur...")
        finally:
            self.server_socket.close()
    
    def generate_id(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    
    def handle_client(self, client_socket, client_id):
        try:
            # Attendre que le client s'identifie
            data = client_socket.recv(1024).decode('utf-8')
            data = json.loads(data)
            
            if data['action'] == 'register':
                username = data['username']
                self.clients[client_id] = (client_socket, username)
                
                response = {
                    'status': 'success',
                    'message': f'Bienvenue {username}',
                    'client_id': client_id
                }
                client_socket.sendall(json.dumps(response).encode('utf-8'))
                
                # Gestion des messages du client
                while True:
                    data = client_socket.recv(1024).decode('utf-8')
                    if not data:
                        break
                    
                    data = json.loads(data)
                    self.process_message(client_id, data)
                    
        except Exception as e:
            print(f"Erreur avec le client {client_id}: {e}")
        finally:
            # Nettoyer lorsque le client se déconnecte
            if client_id in self.clients:
                del self.clients[client_id]
            if client_id in self.waiting_players:
                self.waiting_players.remove(client_id)
            # Gérer la déconnexion d'un joueur en partie
            for game_id, game in list(self.games.items()):
                if game.white_player == client_id or game.black_player == client_id:
                    game.active = False
                    opponent_id = game.black_player if game.white_player == client_id else game.white_player
                    if opponent_id in self.clients:
                        opponent_socket = self.clients[opponent_id][0]
                        opponent_socket.sendall(json.dumps({
                            'action': 'game_over',
                            'reason': 'opponent_disconnected',
                            'game_id': game_id
                        }).encode('utf-8'))
            client_socket.close()
    
    def process_message(self, client_id, data):
        action = data['action']
        
        if action == 'find_game':
            self.find_game(client_id)
        elif action == 'make_move':
            self.handle_move(client_id, data)
        elif action == 'spectate':
            self.add_spectator(client_id, data['game_id'])
        elif action == 'list_games':
            self.list_games(client_id)
        elif action == 'resign':
            self.handle_resignation(client_id, data['game_id'])
    
    def find_game(self, client_id):
        if client_id in self.waiting_players:
            return
        
        if not self.waiting_players:
            self.waiting_players.append(client_id)
            response = {
                'action': 'wait',
                'message': 'En attente d\'un adversaire...'
            }
            self.clients[client_id][0].sendall(json.dumps(response).encode('utf-8'))
        else:
            opponent_id = self.waiting_players.pop(0)
            game_id = self.generate_id()
            
            # Déterminer aléatoirement qui joue les blancs
            if random.choice([True, False]):
                white_player, black_player = client_id, opponent_id
            else:
                white_player, black_player = opponent_id, client_id
                
            game = ChessGame(white_player, black_player, game_id)
            self.games[game_id] = game
            
            # Notifier les deux joueurs
            white_response = {
                'action': 'game_start',
                'game_id': game_id,
                'color': 'white',
                'opponent': self.clients[black_player][1],
                'game_state': game.get_game_state()
            }
            black_response = {
                'action': 'game_start',
                'game_id': game_id,
                'color': 'black',
                'opponent': self.clients[white_player][1],
                'game_state': game.get_game_state()
            }
            
            self.clients[white_player][0].sendall(json.dumps(white_response).encode('utf-8'))
            self.clients[black_player][0].sendall(json.dumps(black_response).encode('utf-8'))
    
    def handle_move(self, client_id, data):
        game_id = data['game_id']
        from_pos = data['from']
        to_pos = data['to']
        
        if game_id not in self.games:
            return
        
        game = self.games[game_id]
        
        # Vérifier si c'est au tour du joueur
        player_color = 'white' if game.white_player == client_id else 'black'
        if player_color != game.current_turn:
            response = {
                'action': 'error',
                'message': 'Ce n\'est pas votre tour'
            }
            self.clients[client_id][0].sendall(json.dumps(response).encode('utf-8'))
            return
        
        # Vérifier si le mouvement est valide
        if not game.is_valid_move(from_pos, to_pos, player_color):
            response = {
                'action': 'error',
                'message': 'Mouvement invalide'
            }
            self.clients[client_id][0].sendall(json.dumps(response).encode('utf-8'))
            return
        
        # Effectuer le mouvement
        move = game.make_move(from_pos, to_pos)
        
        # Notifier tous les participants (joueurs + spectateurs)
        update = {
            'action': 'move',
            'game_id': game_id,
            'move': move,
            'game_state': game.get_game_state()
        }
        
        # Envoyer au joueur blanc
        if game.white_player in self.clients:
            self.clients[game.white_player][0].sendall(json.dumps(update).encode('utf-8'))
        
        # Envoyer au joueur noir
        if game.black_player in self.clients:
            self.clients[game.black_player][0].sendall(json.dumps(update).encode('utf-8'))
        
        # Envoyer aux spectateurs
        for spectator in game.spectators:
            if spectator in self.clients:
                self.clients[spectator][0].sendall(json.dumps(update).encode('utf-8'))
    
    def add_spectator(self, client_id, game_id):
        if game_id not in self.games:
            response = {
                'action': 'error',
                'message': 'Partie introuvable'
            }
            self.clients[client_id][0].sendall(json.dumps(response).encode('utf-8'))
            return
        
        game = self.games[game_id]
        
        # Vérifier que le client n'est pas déjà joueur
        if client_id == game.white_player or client_id == game.black_player:
            return
        
        # Ajouter comme spectateur
        if client_id not in game.spectators:
            game.spectators.append(client_id)
        
        # Envoyer l'état actuel de la partie
        response = {
            'action': 'spectate_start',
            'game_id': game_id,
            'white_player': self.clients[game.white_player][1],
            'black_player': self.clients[game.black_player][1],
            'game_state': game.get_game_state()
        }
        self.clients[client_id][0].sendall(json.dumps(response).encode('utf-8'))
    
    def list_games(self, client_id):
        active_games = []
        for game_id, game in self.games.items():
            if game.active:
                active_games.append({
                    'game_id': game_id,
                    'white_player': self.clients[game.white_player][1],
                    'black_player': self.clients[game.black_player][1],
                    'spectators': len(game.spectators)
                })
        
        response = {
            'action': 'game_list',
            'games': active_games
        }
        self.clients[client_id][0].sendall(json.dumps(response).encode('utf-8'))
    
    def handle_resignation(self, client_id, game_id):
        if game_id not in self.games:
            return
        
        game = self.games[game_id]
        if client_id != game.white_player and client_id != game.black_player:
            return
        
        # Déterminer le gagnant
        winner_id = game.black_player if client_id == game.white_player else game.white_player
        winner_color = 'black' if client_id == game.white_player else 'white'
        
        # Marquer la partie comme terminée
        game.active = False
        
        # Notifier tous les participants
        update = {
            'action': 'game_over',
            'game_id': game_id,
            'reason': 'resignation',
            'winner': winner_color,
            'winner_username': self.clients[winner_id][1]
        }
        
        # Envoyer aux joueurs
        if game.white_player in self.clients:
            self.clients[game.white_player][0].sendall(json.dumps(update).encode('utf-8'))
        if game.black_player in self.clients:
            self.clients[game.black_player][0].sendall(json.dumps(update).encode('utf-8'))
        
        # Envoyer aux spectateurs
        for spectator in game.spectators:
            if spectator in self.clients:
                self.clients[spectator][0].sendall(json.dumps(update).encode('utf-8'))

if __name__ == "__main__":
    server = ChessServer()
    server.start()