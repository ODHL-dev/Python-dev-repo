# Fichier: chess_client.py
import socket
import json
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import base64
from io import BytesIO
from PIL import Image, ImageTk

class ChessClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Jeu d'Échecs")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.client_socket = None
        self.client_id = None
        self.username = None
        self.current_game_id = None
        self.player_color = None
        self.opponent_name = None
        self.is_spectator = False
        self.board_state = {}
        self.current_turn = None
        
        # Variables pour suivre le drag & drop
        self.drag_data = {"x": 0, "y": 0, "piece": None, "from_pos": None, "image_id": None}
        
        self.create_widgets()
    
    def on_close(self):
        if self.client_socket:
            self.client_socket.close()
        self.root.destroy()
        
    def create_widgets(self):
        # Frame principale
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Frame de connexion
        self.login_frame = tk.Frame(self.main_frame, padx=20, pady=20)
        self.login_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(self.login_frame, text="Bienvenue au jeu d'échecs en ligne", 
                 font=('Arial', 16, 'bold')).pack(pady=20)
        
        server_frame = tk.Frame(self.login_frame)
        server_frame.pack(fill=tk.X, pady=10)
        tk.Label(server_frame, text="Serveur:").pack(side=tk.LEFT)
        self.server_entry = tk.Entry(server_frame)
        self.server_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.server_entry.insert(0, "localhost")
        
        port_frame = tk.Frame(self.login_frame)
        port_frame.pack(fill=tk.X, pady=10)
        tk.Label(port_frame, text="Port:").pack(side=tk.LEFT)
        self.port_entry = tk.Entry(port_frame)
        self.port_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.port_entry.insert(0, "5000")
        
        username_frame = tk.Frame(self.login_frame)
        username_frame.pack(fill=tk.X, pady=10)
        tk.Label(username_frame, text="Pseudo:").pack(side=tk.LEFT)
        self.username_entry = tk.Entry(username_frame)
        self.username_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.connect_button = tk.Button(self.login_frame, text="Se connecter", command=self.connect_to_server)
        self.connect_button.pack(pady=20)
        
        # Frame de jeu (initialement caché)
        self.game_frame = tk.Frame(self.main_frame)
        
        # Préparation du cadre du plateau
        self.board_frame = tk.Frame(self.game_frame)
        self.board_frame.pack(side=tk.LEFT, padx=10, pady=10)
        
        # Préparation des informations de jeu
        self.info_frame = tk.Frame(self.game_frame)
        self.info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Cadre pour les boutons d'action
        self.action_frame = tk.Frame(self.info_frame)
        self.action_frame.pack(fill=tk.X, pady=10)
        
        self.find_game_button = tk.Button(self.action_frame, text="Trouver une partie", command=self.find_game)
        self.find_game_button.pack(side=tk.LEFT, padx=5)
        
        self.list_games_button = tk.Button(self.action_frame, text="Lister les parties", command=self.list_games)
        self.list_games_button.pack(side=tk.LEFT, padx=5)
        
        self.resign_button = tk.Button(self.action_frame, text="Abandonner", command=self.resign,
                                       state=tk.DISABLED)
        self.resign_button.pack(side=tk.LEFT, padx=5)
        
        # Informations de partie
        self.game_info_label = tk.Label(self.info_frame, text="En attente de partie...", font=('Arial', 12))
        self.game_info_label.pack(pady=10)
        
        self.turn_label = tk.Label(self.info_frame, text="", font=('Arial', 12, 'bold'))
        self.turn_label.pack(pady=5)
        
        # Liste des parties disponibles
        self.game_list_frame = tk.Frame(self.info_frame)
        self.game_list_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tk.Label(self.game_list_frame, text="Parties disponibles:").pack(anchor=tk.W)
        
        self.game_listbox = tk.Listbox(self.game_list_frame, height=10)
        self.game_listbox.pack(fill=tk.BOTH, expand=True)
        
        self.spectate_button = tk.Button(self.game_list_frame, text="Observer la partie", 
                                         command=self.spectate_game)
        self.spectate_button.pack(pady=5)
        
    def create_chessboard(self):
        # Créer un nouveau Canvas pour l'échiquier
        self.canvas = tk.Canvas(self.board_frame, width=400, height=400, bg="white")
        self.canvas.pack()
        
        # Dessiner l'échiquier
        self.squares = {}
        self.piece_images_refs = {}  # Pour garder les références aux images
        
        for row in range(8):
            for col in range(8):
                x1 = col * 50
                y1 = row * 50
                x2 = x1 + 50
                y2 = y1 + 50
                
                # Déterminer la couleur de la case
                color = "#EEEED2" if (row + col) % 2 == 0 else "#769656"
                
                # Créer la case
                square_id = self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
                
                # Calculer la notation algébrique
                file = chr(ord('a') + col)
                rank = 8 - row
                square_notation = f"{file}{rank}"
                
                self.squares[square_notation] = (x1, y1, x2, y2)
        
        # Configurer les événements de drag & drop
        self.canvas.tag_bind("piece", "<ButtonPress-1>", self.on_piece_press)
        self.canvas.tag_bind("piece", "<B1-Motion>", self.on_piece_motion)
        self.canvas.tag_bind("piece", "<ButtonRelease-1>", self.on_piece_release)
    
    def on_piece_press(self, event):
        if self.is_spectator or (self.player_color != self.current_turn):
            return
            
        # Récupérer l'élément sous le curseur
        item = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item)
        
        # Vérifier si c'est une pièce et si elle appartient au joueur
        if "piece" in tags:
            pos_tag = None
            color_tag = None
            for tag in tags:
                if tag.startswith("pos_"):
                    pos_tag = tag[4:]  # Extrait "a2" de "pos_a2"
                elif tag in ["white", "black"]:
                    color_tag = tag
            
            if color_tag == self.player_color:
                # Sauvegarder les données pour le drag
                self.drag_data["piece"] = item
                self.drag_data["from_pos"] = pos_tag
                self.drag_data["x"] = event.x
                self.drag_data["y"] = event.y
                
                # Lever la pièce (en la plaçant au-dessus des autres)
                self.canvas.tag_raise(item)
    
    def on_piece_motion(self, event):
        if self.drag_data["piece"]:
            # Calculer le déplacement
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            
            # Déplacer la pièce
            self.canvas.move(self.drag_data["piece"], dx, dy)
            
            # Mettre à jour la position pour le prochain mouvement
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
    
    def on_piece_release(self, event):
        if not self.drag_data["piece"]:
            return
            
        # Trouver la case sous le curseur
        to_pos = None
        for pos, coords in self.squares.items():
            x1, y1, x2, y2 = coords
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                to_pos = pos
                break
        
        if to_pos and to_pos != self.drag_data["from_pos"]:
            # Tentative de déplacement
            self.make_move(self.drag_data["from_pos"], to_pos)
        else:
            # Remettre la pièce à sa position d'origine
            self.update_board(self.board_state)
        
        # Réinitialiser les données de drag
        self.drag_data = {"x": 0, "y": 0, "piece": None, "from_pos": None, "image_id": None}
    
    # Modifiez la section load_piece_images et update_board dans votre fichier chess_client.py


    def update_board(self, board_state):
        if not hasattr(self, 'canvas'):
            return
            
        # Supprimer toutes les pièces
        self.canvas.delete("piece")
        
        # Définir les symboles pour les pièces
        symbols = {
            'white': {
                'king': '♔',
                'queen': '♕',
                'rook': '♖',
                'bishop': '♗',
                'knight': '♘',
                'pawn': '♙'
            },
            'black': {
                'king': '♚',
                'queen': '♛',
                'rook': '♜',
                'bishop': '♝',
                'knight': '♞',
                'pawn': '♟'
            }
        }
        
        # Placer les pièces selon l'état actuel
        for pos, piece_info in board_state.items():
            piece_type = piece_info['piece']
            color = piece_info['color']
            
            # Trouver les coordonnées de la case
            if pos in self.squares:
                x1, y1, x2, y2 = self.squares[pos]
                
                # Calculer le centre de la case
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                
                # Déterminer la couleur du texte et le symbole
                text_color = "white" if color == "white" else "black"
                symbol = symbols[color][piece_type]
                
                # Créer un cercle de fond pour contraster avec la case
                bg_color = "#BBBBBB" if color == "white" else "#444444"
                circle_id = self.canvas.create_oval(center_x-20, center_y-20, 
                                                center_x+20, center_y+20, 
                                                fill=bg_color, outline="")
                
                # Créer le texte pour la pièce
                piece_id = self.canvas.create_text(center_x, center_y, 
                                                text=symbol, 
                                                font=("Arial", 28, "bold"),
                                                fill=text_color,
                                                tags=("piece", color, f"pos_{pos}", piece_type))
                
                # Attacher les mêmes tags au cercle de fond
                self.canvas.itemconfig(circle_id, tags=("piece", color, f"pos_{pos}", piece_type))
    
    def connect_to_server(self):
        server = self.server_entry.get()
        port = int(self.port_entry.get())
        self.username = self.username_entry.get()
        
        if not self.username:
            messagebox.showerror("Erreur", "Veuillez entrer un pseudo")
            return
        
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server, port))
            
            # Envoyer les informations d'identification
            register_data = {
                'action': 'register',
                'username': self.username
            }
            self.client_socket.sendall(json.dumps(register_data).encode('utf-8'))
            
            # Attendre la réponse
            response = self.client_socket.recv(1024).decode('utf-8')
            response = json.loads(response)
            
            if response['status'] == 'success':
                self.client_id = response['client_id']
                messagebox.showinfo("Connexion réussie", response['message'])
                
                # Basculer vers l'interface de jeu
                self.login_frame.pack_forget()
                self.game_frame.pack(fill=tk.BOTH, expand=True)
                
                # Créer l'échiquier
                self.create_chessboard()
                
                # Démarrer un thread pour écouter les messages du serveur
                receive_thread = threading.Thread(target=self.receive_messages)
                receive_thread.daemon = True
                receive_thread.start()
            else:
                messagebox.showerror("Erreur", response['message'])
                self.client_socket.close()
                self.client_socket = None
                
        except Exception as e:
            messagebox.showerror("Erreur de connexion", str(e))
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None
    
    def receive_messages(self):
        while self.client_socket:
            try:
                data = self.client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                    
                response = json.loads(data)
                self.process_message(response)
                
            except Exception as e:
                print(f"Erreur de réception: {e}")
                break
        
        # Gérer la déconnexion
        if self.client_socket:
            self.client_socket.close()
            self.client_socket = None
            
        messagebox.showwarning("Déconnexion", "Connexion au serveur perdue")
    
    def process_message(self, message):
        action = message['action']
        
        if action == 'wait':
            self.update_game_info("En attente d'un adversaire...")
        
        elif action == 'game_start':
            self.current_game_id = message['game_id']
            self.player_color = message['color']
            self.opponent_name = message['opponent']
            self.is_spectator = False
            
            # Mettre à jour l'état du plateau
            game_state = message['game_state']
            self.board_state = game_state['board']
            self.current_turn = game_state['current_turn']
            
            # Mettre à jour l'interface
            self.update_game_info(f"Partie contre {self.opponent_name}")
            self.update_turn_info()
            self.update_board(self.board_state)
            self.resign_button.config(state=tk.NORMAL)
        
        elif action == 'spectate_start':
            self.current_game_id = message['game_id']
            self.is_spectator = True
            white_player = message['white_player']
            black_player = message['black_player']
            
            # Mettre à jour l'état du plateau
            game_state = message['game_state']
            self.board_state = game_state['board']
            self.current_turn = game_state['current_turn']
            
            # Mettre à jour l'interface
            self.update_game_info(f"Vous observez: {white_player} (Blancs) vs {black_player} (Noirs)")
            self.update_turn_info()
            self.update_board(self.board_state)
            self.resign_button.config(state=tk.DISABLED)
        
        elif action == 'move':
            # Mettre à jour l'état du plateau
            game_state = message['game_state']
            self.board_state = game_state['board']
            self.current_turn = game_state['current_turn']
            
            # Mettre à jour l'interface
            self.update_turn_info()
            self.update_board(self.board_state)
        
        elif action == 'game_over':
            reason = message['reason']
            if reason == 'resignation':
                winner = message['winner']
                winner_username = message['winner_username']
                messagebox.showinfo("Fin de partie", f"{winner_username} ({winner}) a gagné par abandon!")
            elif reason == 'opponent_disconnected':
                messagebox.showinfo("Fin de partie", "Votre adversaire s'est déconnecté. Vous avez gagné!")
            
            # Réinitialiser l'état de la partie
            self.current_game_id = None
            self.player_color = None
            self.opponent_name = None
            self.is_spectator = False
            self.board_state = {}
            self.current_turn = None
            
            # Mettre à jour l'interface
            self.update_game_info("En attente de partie...")
            self.turn_label.config(text="")
            self.resign_button.config(state=tk.DISABLED)
        
        elif action == 'game_list':
            games = message['games']
            self.update_game_list(games)
        
        elif action == 'error':
            messagebox.showerror("Erreur", message['message'])
    
    def update_game_info(self, text):
        self.game_info_label.config(text=text)
    
    def update_turn_info(self):
        if self.current_turn:
            turn_text = f"Au tour des {'Blancs' if self.current_turn == 'white' else 'Noirs'}"
            if not self.is_spectator:
                if self.player_color == self.current_turn:
                    turn_text += " (C'est à vous de jouer)"
                else:
                    turn_text += " (Tour de l'adversaire)"
            self.turn_label.config(text=turn_text)
    
    def update_game_list(self, games):
        self.game_listbox.delete(0, tk.END)
        
        if not games:
            self.game_listbox.insert(tk.END, "Aucune partie en cours")
            self.spectate_button.config(state=tk.DISABLED)
            return
        
        self.game_data = {}
        for game in games:
            game_id = game['game_id']
            white_player = game['white_player']
            black_player = game['black_player']
            spectators = game['spectators']
            
            display_text = f"{white_player} vs {black_player} ({spectators} spectateurs)"
            self.game_listbox.insert(tk.END, display_text)
            self.game_data[display_text] = game_id
        
        self.spectate_button.config(state=tk.NORMAL)
    
    def find_game(self):
        if not self.client_socket:
            return
            
        request = {
            'action': 'find_game'
        }
        self.client_socket.sendall(json.dumps(request).encode('utf-8'))
    
    def list_games(self):
        if not self.client_socket:
            return
            
        request = {
            'action': 'list_games'
        }
        self.client_socket.sendall(json.dumps(request).encode('utf-8'))
    
    def spectate_game(self):
        selection = self.game_listbox.curselection()
        if not selection:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner une partie à observer")
            return
            
        selected_game = self.game_listbox.get(selection[0])
        if selected_game in self.game_data:
            game_id = self.game_data[selected_game]
            
            request = {
                'action': 'spectate',
                'game_id': game_id
            }
            self.client_socket.sendall(json.dumps(request).encode('utf-8'))
    
    def make_move(self, from_pos, to_pos):
        if not self.client_socket or not self.current_game_id:
            return
            
        if self.is_spectator:
            messagebox.showwarning("Spectateur", "Vous ne pouvez pas jouer en tant que spectateur")
            self.update_board(self.board_state)
            return
            
        if self.player_color != self.current_turn:
            messagebox.showwarning("Pas votre tour", "Ce n'est pas votre tour de jouer")
            self.update_board(self.board_state)
            return
        
        request = {
            'action': 'make_move',
            'game_id': self.current_game_id,
            'from': from_pos,
            'to': to_pos
        }
        self.client_socket.sendall(json.dumps(request).encode('utf-8'))
    
    def resign(self):
        if not self.client_socket or not self.current_game_id or self.is_spectator:
            return
            
        confirm = messagebox.askyesno("Abandonner", "Êtes-vous sûr de vouloir abandonner la partie?")
        if confirm:
            request = {
                'action': 'resign',
                'game_id': self.current_game_id
            }
            self.client_socket.sendall(json.dumps(request).encode('utf-8'))
    
    def on_close(self):
        if self.client_socket:
            self.client_socket.close()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ChessClient(root)
    root.mainloop()