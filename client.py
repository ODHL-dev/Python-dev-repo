"""import socket
from threading import Thread

socketc=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
socketc.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
socketc.connect(("192.168.1.71",8000))

def Send(socketc):
    while True:
        message = input(">>>>> ")
        if not message:
            break
        socketc.send(message.encode())

def reception(socketc):
    while True:
        donnees = socketc.recv(2048)
        if not donnees:
            break
        print(donnees.decode())

envoi=Thread(target=Send,args=[socketc])
recevoir=Thread(target=reception,args=[socketc])

envoi.start()
recevoir.start()"""

import socket
from threading import Thread


class ClientChat:
    def __init__(self, host='127.0.0.1', port=8000):
        self.socket_Client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_Client.connect((host, port))

    def send_messages(self):
        try:
            nom = input("Entrez votre nom : ")
            self.socket_Client.send(nom.encode())  # Envoi du nom au serveur

            while True:
                message = input(">>>>> ")
                if message.lower() == "exit":
                    break
                self.socket_Client.send(message.encode())
        except:
            print("Erreur lors de l'envoi du message.")
        finally:
            self.socket_Client.close()

    def receive_messages(self):
        try:
            while True:
                donnees = self.socket_Client.recv(2048)
                if not donnees:
                    break
                print(donnees.decode())
        except:
            print("Erreur lors de la réception des messages.")

    def start(self):
        thread_envoi = Thread(target=self.send_messages)
        thread_reception = Thread(target=self.receive_messages)

        thread_envoi.start()
        thread_reception.start()

        thread_envoi.join()
        thread_reception.join()


client = ClientChat()
client.start()