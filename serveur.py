"""import socket
from threading import Thread

socket_Serveur= socket.socket(socket.AF_INET,socket.SOCK_STREAM)

socket_Serveur.bind(('0.0.0.0',8000))
socket_Serveur.listen(2)
(socket_Client,add_IP_Client)=socket_Serveur.accept()
print("Connection accomplie")

def send(socket_Client):
    while True:
        message = input(">>>>> ")
        if not message:
            break            
        socket_Client.send(message.encode())

def reception(socket_Client):
    while True:
        donnees = socket_Client.recv(2048)
        if not donnees:
            break
        print(donnees.decode())


envoi=Thread(target=send,args=[socket_Client])
receve=Thread(target=reception,args=[socket_Client])
envoi.start()
receve.start()

receve.join()
socket_Serveur.close()
socket_Client.close()

print("Fin de la communication")"""
import socket
from threading import Thread


class ServeurChat:
    def __init__(self, host='0.0.0.0', port=8000):
        self.socket_Serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_Serveur.bind((host, port))
        self.socket_Serveur.listen(5)  # Peut gérer jusqu'à 5 connexions simultanées
        self.clients = {}  # Stocker les clients connectés

    def handle_client(self, client_socket, address):
        try:
            nom = client_socket.recv(2048).decode()
            self.clients[nom] = client_socket
            print(f"Utilisateur '{nom}' connecté depuis {address}")

            while True:
                donnees = client_socket.recv(2048)
                if not donnees:
                    break
                print(f"{nom}: {donnees.decode()}")

                # Diffuser le message à tous les autres clients
                self.broadcast_message(f"{nom}: {donnees.decode()}", client_socket)
        except:
            print(f"Connexion avec {nom} interrompue.")
        finally:
            client_socket.close()
            del self.clients[nom]
            print(f"Utilisateur '{nom}' déconnecté.")

    def broadcast_message(self, message, sender_socket):
        for nom, client_socket in self.clients.items():
            if client_socket != sender_socket:  # Ne pas envoyer au client émetteur
                try:
                    client_socket.send(message.encode())
                except:
                    print(f"Erreur lors de l'envoi à {nom}")

    def start(self):
        print("Serveur prêt et en attente de connexions...")
        while True:
            client_socket, client_address = self.socket_Serveur.accept()
            print(f"Nouvelle connexion: {client_address}")
            thread = Thread(target=self.handle_client, args=(client_socket, client_address))
            thread.start()


serveur = ServeurChat()
serveur.start()