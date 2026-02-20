import pygame
import socket
import threading
import json
import sys
import time
import random

# Initialisation de Pygame
pygame.init()

# Constantes
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 450
BACKGROUND_COLOR = (25, 25, 75)
FPS = 60

# Couleurs
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
LIGHT_GRAY = (150, 150, 150)

class FightingGameClient:
    def __init__(self, host="localhost", port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.client_id = None
        self.username = None
        self.role = "spectator"  # "spectator" ou "player"
        self.current_match_id = None
        self.match_state = None
        self.running = True
        self.connected = False
        self.in_queue = False
        self.match_list = []
        self.current_screen = "menu"  # "menu", "queue", "match_list", "game"
        self.animation_counter = 0
        self.waiting_dots = 0
        self.last_keys = {}  # Pour stocker l'état des touches au frame précédent
        
        # Initialisation de la fenêtre
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Jeu de Combat en Réseau")
        self.clock = pygame.time.Clock()
        
        # Chargement des ressources
        self.load_resources()
        
    def load_resources(self):
        """Charge les ressources du jeu (images, sons, polices)"""
        # Polices
        self.font_small = pygame.font.SysFont("Arial", 16)
        self.font_medium = pygame.font.SysFont("Arial", 24)
        self.font_large = pygame.font.SysFont("Arial", 32)
        self.font_xl = pygame.font.SysFont("Arial", 48)
        
        # Création de formes pour représenter les personnages
        # Joueur 1 (rouge)
        self.player1_img = pygame.Surface((40, 80))
        self.player1_img.fill(RED)
        # Joueur 2 (bleu)
        self.player2_img = pygame.Surface((40, 80))
        self.player2_img.fill(BLUE)
        
        # Image de coup
        self.attack_img = pygame.Surface((60, 20))
        self.attack_img.fill(YELLOW)
        
        # Boutons
        self.button_width = 200
        self.button_height = 50
        
        # Effets d'attaque
        self.attack_effect = []
        for i in range(3):
            effect = pygame.Surface((60 - i*15, 20 - i*5))
            effect.fill(YELLOW)
            self.attack_effect.append(effect)
        
        # Arène de combat
        self.arena_img = pygame.Surface((SCREEN_WIDTH, 150))
        self.arena_img.fill((50, 50, 50))
        pygame.draw.line(self.arena_img, WHITE, (0, 0), (SCREEN_WIDTH, 0), 3)
        
    def connect_to_server(self):
        """Connecte le client au serveur"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            
            # Démarrer le thread de réception
            receive_thread = threading.Thread(target=self.receive_messages)
            receive_thread.daemon = True
            receive_thread.start()
            
            self.connected = True
            print(f"Connecté au serveur {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Erreur de connexion: {e}")
            return False
    
    def receive_messages(self):
        """Reçoit les messages du serveur"""
        while self.running:
            try:
                message = self.receive_message()
                if not message:
                    print("Déconnecté du serveur")
                    self.connected = False
                    break
                
                self.handle_server_message(message)
            except Exception as e:
                print(f"Erreur de réception: {e}")
                self.connected = False
                break
    
    def handle_server_message(self, message):
        """Traite un message reçu du serveur"""
        msg_type = message.get("type", "")
        
        if msg_type == "welcome":
            # Réception de l'ID client
            self.client_id = message.get("client_id")
            self.username = f"Joueur_{self.client_id}"
            
            # Envoyer le nom d'utilisateur au serveur
            self.send_message({
                "type": "set_username",
                "username": self.username
            })
            
        elif msg_type == "username_set":
            # Confirmation du nom d'utilisateur
            self.username = message.get("username")
            
        elif msg_type == "match_list":
            # Liste des matchs disponibles
            self.match_list = message.get("matches", [])
            
        elif msg_type == "queue_joined":
            # Confirmation d'entrée dans la file d'attente
            self.in_queue = True
            self.current_screen = "queue"
            
        elif msg_type == "queue_left":
            # Confirmation de sortie de la file d'attente
            self.in_queue = False
            self.current_screen = "menu"
            
        elif msg_type == "match_start":
            # Début d'un match
            self.current_match_id = message.get("match_id")
            self.match_state = message.get("state")
            self.role = "player"
            self.current_screen = "game"
            self.in_queue = False
            
        elif msg_type == "match_joined":
            # Rejoindre un match en tant que spectateur
            self.current_match_id = message.get("match_id")
            self.match_state = message.get("state")
            self.role = "spectator"
            self.current_screen = "game"
            
        elif msg_type == "match_update":
            # Mise à jour de l'état du match
            if message.get("match_id") == self.current_match_id:
                self.match_state = message.get("state")
    
    def send_message(self, message):
        """Envoie un message au serveur"""
        try:
            data = json.dumps(message).encode('utf-8')
            message_length = len(data).to_bytes(4, byteorder='big')
            self.socket.sendall(message_length + data)
        except Exception as e:
            print(f"Erreur d'envoi: {e}")
            
    def receive_message(self):
        """Reçoit un message du serveur"""
        try:
            # Recevoir la taille du message
            message_length_bytes = self.socket.recv(4)
            if not message_length_bytes:
                return None
                
            message_length = int.from_bytes(message_length_bytes, byteorder='big')
            
            # Recevoir le message complet
            chunks = []
            bytes_received = 0
            while bytes_received < message_length:
                chunk = self.socket.recv(min(message_length - bytes_received, 4096))
                if not chunk:
                    return None
                chunks.append(chunk)
                bytes_received += len(chunk)
                
            data = b''.join(chunks)
            return json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f"Erreur de réception: {e}")
            return None
    
    def join_queue(self):
        """Rejoindre la file d'attente pour un match"""
        if self.connected:
            self.send_message({
                "type": "join_queue"
            })
    
    def leave_queue(self):
        """Quitter la file d'attente"""
        if self.connected and self.in_queue:
            self.send_message({
                "type": "leave_queue"
            })
    
    def request_match_list(self):
        """Demander la liste des matchs en cours"""
        if self.connected:
            self.send_message({
                "type": "request_match_list"
            })
            self.current_screen = "match_list"
    
    def spectate_match(self, match_id):
        """Rejoindre un match en tant que spectateur"""
        if self.connected:
            self.send_message({
                "type": "spectate_match",
                "match_id": match_id
            })
    
    def send_game_action(self, action):
        """Envoyer une action au serveur"""
        if self.connected and self.current_match_id is not None and self.role == "player":
            self.send_message({
                "type": "game_action",
                "match_id": self.current_match_id,
                "action": action
            })
    
    def draw_button(self, text, x, y, width, height, color, hover_color, action=None):
        """Dessine un bouton interactif"""
        mouse_pos = pygame.mouse.get_pos()
        clicked = pygame.mouse.get_pressed()[0]
        
        # Vérifier si la souris est sur le bouton
        if x <= mouse_pos[0] <= x + width and y <= mouse_pos[1] <= y + height:
            pygame.draw.rect(self.screen, hover_color, (x, y, width, height))
            if clicked and action:
                # Attendre un peu pour éviter les clics multiples
                pygame.time.wait(200)
                action()
        else:
            pygame.draw.rect(self.screen, color, (x, y, width, height))
        
        # Contour du bouton
        pygame.draw.rect(self.screen, WHITE, (x, y, width, height), 2)
        
        # Texte du bouton
        text_surf = self.font_medium.render(text, True, WHITE)
        text_rect = text_surf.get_rect(center=(x + width // 2, y + height // 2))
        self.screen.blit(text_surf, text_rect)
    
    def draw_menu(self):
        """Dessine l'écran du menu principal"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # Titre
        title_text = self.font_xl.render("Jeu de Combat en Réseau", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 80))
        self.screen.blit(title_text, title_rect)
        
        # Statut de connexion
        status_text = self.font_medium.render(
            f"Statut: {'Connecté' if self.connected else 'Déconnecté'}", True, 
            GREEN if self.connected else RED
        )
        self.screen.blit(status_text, (20, 20))
        
        # Nom d'utilisateur
        if self.username:
            username_text = self.font_medium.render(f"Nom: {self.username}", True, WHITE)
            self.screen.blit(username_text, (20, 50))
        
        # Boutons
        button_y = 180
        button_spacing = 70
        
        # Bouton de connexion
        if not self.connected:
            self.draw_button(
                "Se connecter", 
                SCREEN_WIDTH // 2 - self.button_width // 2, 
                button_y, 
                self.button_width, 
                self.button_height, 
                (100, 100, 200), 
                (150, 150, 250), 
                self.connect_to_server
            )
        else:
            # Bouton pour rejoindre la file d'attente
            self.draw_button(
                "Rejoindre la file d'attente", 
                SCREEN_WIDTH // 2 - self.button_width // 2, 
                button_y, 
                self.button_width, 
                self.button_height, 
                (100, 200, 100), 
                (150, 250, 150), 
                self.join_queue
            )
            
            # Bouton pour voir les matchs
            self.draw_button(
                "Voir les matchs en cours", 
                SCREEN_WIDTH // 2 - self.button_width // 2, 
                button_y + button_spacing, 
                self.button_width, 
                self.button_height, 
                (100, 100, 200), 
                (150, 150, 250), 
                self.request_match_list
            )
            
            # Bouton pour quitter
            self.draw_button(
                "Quitter", 
                SCREEN_WIDTH // 2 - self.button_width // 2, 
                button_y + button_spacing * 2, 
                self.button_width, 
                self.button_height, 
                (200, 100, 100), 
                (250, 150, 150), 
                self.quit_game
            )
    
    def draw_queue_screen(self):
        """Dessine l'écran d'attente de match"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # Titre
        title_text = self.font_large.render("En attente d'un adversaire", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Animation d'attente (points qui clignotent)
        self.animation_counter += 1
        if self.animation_counter >= 30:  # ~0.5 seconde avec 60 FPS
            self.waiting_dots = (self.waiting_dots + 1) % 4
            self.animation_counter = 0
            
        dots = "." * self.waiting_dots
        dots_text = self.font_large.render(dots, True, WHITE)
        dots_rect = dots_text.get_rect(midleft=(title_rect.right + 10, title_rect.centery))
        self.screen.blit(dots_text, dots_rect)
        
        # Bouton pour quitter la file d'attente
        self.draw_button(
            "Quitter la file", 
            SCREEN_WIDTH // 2 - self.button_width // 2, 
            300, 
            self.button_width, 
            self.button_height, 
            (200, 100, 100), 
            (250, 150, 150), 
            self.leave_queue
        )
    
    def draw_match_list_screen(self):
        """Dessine l'écran de liste des matchs"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # Titre
        title_text = self.font_large.render("Matchs en cours", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_text, title_rect)
        
        # Raffraîchir la liste
        self.draw_button(
            "Rafraîchir", 
            SCREEN_WIDTH - 120, 
            20, 
            100, 
            30, 
            (100, 100, 200), 
            (150, 150, 250), 
            self.request_match_list
        )
        
        # Bouton retour
        self.draw_button(
            "Retour", 
            20, 
            20, 
            100, 
            30, 
            (200, 100, 100), 
            (250, 150, 150), 
            lambda: setattr(self, 'current_screen', 'menu')
        )
        
        if not self.match_list:
            # Aucun match en cours
            no_match_text = self.font_medium.render("Aucun match en cours", True, WHITE)
            no_match_rect = no_match_text.get_rect(center=(SCREEN_WIDTH // 2, 200))
            self.screen.blit(no_match_text, no_match_rect)
        else:
            # Liste des matchs
            y_offset = 120
            for i, match in enumerate(self.match_list):
                match_id = match.get("match_id")
                status = match.get("status")
                players = match.get("players", [])
                
                # Infos du match
                match_text = self.font_medium.render(
                    f"Match #{match_id}: {' vs '.join(players)} - {status}", 
                    True, 
                    WHITE
                )
                self.screen.blit(match_text, (50, y_offset))
                
                # Bouton pour rejoindre en tant que spectateur
                if status != "finished":
                    self.draw_button(
                        "Regarder", 
                        SCREEN_WIDTH - 150, 
                        y_offset - 5, 
                        100, 
                        30, 
                        (100, 200, 100), 
                        (150, 250, 150), 
                        lambda mid=match_id: self.spectate_match(mid)
                    )
                
                y_offset += 50
    
    def draw_game_screen(self):
        """Dessine l'écran de jeu"""
        if not self.match_state:
            return
            
        self.screen.fill(BACKGROUND_COLOR)
        
        # Fond de l'arène
        self.screen.blit(self.arena_img, (0, 300))
        
        # État du match
        status = self.match_state.get("status", "")
        countdown = self.match_state.get("countdown", 0)
        
        # Informations des joueurs
        players_info = self.match_state.get("players", {})
        
        # En-tête avec infos du match
        if status == "starting":
            # Compte à rebours
            countdown_text = self.font_xl.render(str(countdown), True, WHITE)
            countdown_rect = countdown_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
            self.screen.blit(countdown_text, countdown_rect)
            
            get_ready_text = self.font_large.render("Préparez-vous !", True, WHITE)
            get_ready_rect = get_ready_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
            self.screen.blit(get_ready_text, get_ready_rect)
            
        elif status == "finished":
            # Résultat du match
            winner_id = self.match_state.get("winner")
            if winner_id is not None and winner_id in players_info:
                winner_name = players_info[winner_id]["username"]
                winner_text = self.font_xl.render(f"{winner_name} a gagné !", True, GREEN)
                winner_rect = winner_text.get_rect(center=(SCREEN_WIDTH // 2, 150))
                self.screen.blit(winner_text, winner_rect)
            
            # Bouton pour retourner au menu
            self.draw_button(
                "Retour au menu", 
                SCREEN_WIDTH // 2 - self.button_width // 2, 
                350, 
                self.button_width, 
                self.button_height, 
                (100, 100, 200), 
                (150, 150, 250), 
                lambda: setattr(self, 'current_screen', 'menu')
            )
        
        # Afficher les joueurs et leur barre de vie
        y_offset = 20
        for player_id, player_info in players_info.items():
            position = player_info.get("position", [0, 0])
            health = player_info.get("health", 100)
            username = player_info.get("username", f"Joueur_{player_id}")
            facing = player_info.get("facing", "right")
            action = player_info.get("action", "idle")
            
            # Barre de vie
            health_width = 200
            health_height = 20
            health_x = 20 if int(player_id) == min([int(pid) for pid in players_info.keys()]) else SCREEN_WIDTH - 20 - health_width
            
            # Fond de la barre de vie
            pygame.draw.rect(self.screen, RED, (health_x, y_offset, health_width, health_height))
            # Vie actuelle
            health_percent = max(0, min(health, 100)) / 100
            pygame.draw.rect(self.screen, GREEN, (health_x, y_offset, health_width * health_percent, health_height))
            # Contour
            pygame.draw.rect(self.screen, WHITE, (health_x, y_offset, health_width, health_height), 2)
            
            # Nom du joueur
            player_text = self.font_medium.render(username, True, WHITE)
            text_x = health_x if int(player_id) == min([int(pid) for pid in players_info.keys()]) else health_x + health_width - player_text.get_width()
            self.screen.blit(player_text, (text_x, y_offset - 30))
            
            # Dessiner le joueur
            player_image = self.player1_img if int(player_id) == min([int(pid) for pid in players_info.keys()]) else self.player2_img
            player_rect = player_image.get_rect(midbottom=(position[0], position[1] + 80))
            self.screen.blit(player_image, player_rect)
            
            # Gérer l'action du joueur
            if action == "attacking":
                # Animation d'attaque
                attack_frame = self.animation_counter % len(self.attack_effect)
                attack_img = self.attack_effect[attack_frame]
                
                # Position de l'attaque selon l'orientation
                if facing == "right":
                    attack_x = player_rect.right
                    attack_y = player_rect.centery - 10
                else:
                    attack_x = player_rect.left - attack_img.get_width()
                    attack_y = player_rect.centery - 10
                
                self.screen.blit(attack_img, (attack_x, attack_y))
        
        # Statut (rôle du joueur)
        role_text = self.font_small.render(
            f"Vous êtes: {'Joueur' if self.role == 'player' else 'Spectateur'}", 
            True, 
            YELLOW if self.role == 'player' else WHITE
        )
        self.screen.blit(role_text, (10, SCREEN_HEIGHT - 30))
    
    def handle_player_inputs(self):
        """Gère les entrées du joueur pendant un match"""
        if self.role != "player" or self.current_match_id is None or self.match_state is None:
            return
            
        if self.match_state.get("status") != "running":
            return
            
        keys = pygame.key.get_pressed()
        
        # Mouvement
        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx = -5
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx = 5
            
        if dx != 0:
            self.send_game_action({
                "type": "move",
                "dx": dx
            })
        
        # Attaque (avec refroidissement)
        if keys[pygame.K_SPACE] and not self.last_keys.get(pygame.K_SPACE, False):
            self.send_game_action({
                "type": "attack"
            })
            
        # Mettre à jour l'état des touches
        self.last_keys = {
            pygame.K_SPACE: keys[pygame.K_SPACE],
            pygame.K_LEFT: keys[pygame.K_LEFT],
            pygame.K_RIGHT: keys[pygame.K_RIGHT],
            pygame.K_a: keys[pygame.K_a],
            pygame.K_d: keys[pygame.K_d]
        }
    
    def quit_game(self):
        """Quitte le jeu proprement"""
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        pygame.quit()
        sys.exit()
    
    def run(self):
        """Boucle principale du jeu"""
        while self.running:
            # Gestion des événements
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_game()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.current_screen == "game" and self.match_state.get("status") == "finished":
                            self.current_screen = "menu"
                        elif self.current_screen in ["queue", "match_list"]:
                            self.current_screen = "menu"
            
            # Gestion des entrées du joueur pendant un match
            if self.current_screen == "game":
                self.handle_player_inputs()
            
            # Affichage en fonction de l'écran actuel
            if self.current_screen == "menu":
                self.draw_menu()
            elif self.current_screen == "queue":
                self.draw_queue_screen()
            elif self.current_screen == "match_list":
                self.draw_match_list_screen()
            elif self.current_screen == "game":
                self.draw_game_screen()
            
            # Mise à jour de l'écran
            pygame.display.flip()
            self.clock.tick(FPS)
            self.animation_counter += 1

if __name__ == "__main__":
    # Par défaut, connexion à localhost. Pour se connecter à une autre adresse:
    # client = FightingGameClient("192.168.1.10", 5555)
    client = FightingGameClient()
    client.run()