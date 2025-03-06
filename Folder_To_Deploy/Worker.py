import socket
import json
import struct
import threading
import os
import time
import sys


# ================== Constantes ================== 

etas = 0
PORT = 4455
PORT2 = 4456
CHEMIN_DES_FICHIERS = "/chemin/fichiers" 
NOM_MACHINE = socket.gethostname()

# Compteur global pour Les deux tris 
compteur_mots_tri_1 = {}
compteur_mots_tri_2 =  []

# Verrou pour protéger l'accès aux compteurs
verrou_compteur_tri_1 = threading.Lock()
verrou_compteur_tri_2 = threading.Lock()

dictionnaire_a_trier = {}

# ================== Gestion des Messages ==================

def recevoir_exactement(client_socket, n):
    """ Reçoit exactement n octets du socket client. """
    data = b''
    while len(data) < n:
        packet = client_socket.recv(n - len(data))
        if not packet:
            return None
        data += packet
    return data

def recevoir_message(client_socket):
    """ Reçoit un message du socket client. """
    try:
        taille_message_bytes = recevoir_exactement(client_socket, 4)
        if taille_message_bytes is None:
            return None
        taille_message = struct.unpack('!I', taille_message_bytes)[0]
        data = recevoir_exactement(client_socket, taille_message)
        return data.decode('utf-8') if data else None
    except Exception as e:
        print(f"Erreur lors de la réception du message: {e}")
        return None

def envoyer_message(client_socket, message):
    """ Envoie un message au socket client. """
    try:
        message_bytes = message.encode('utf-8')
        client_socket.sendall(struct.pack('!I', len(message_bytes)))
        client_socket.sendall(message_bytes)
    except Exception as e:
        print(f"Erreur lors de l'envoi du message: {e}")

# ================== Configuration et Initialisation =====================

def initialiser_socket(port, max_retries=5):
    """Initialise un socket serveur sur le port spécifié."""
    serveur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serveur_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  
    for tentative in range(max_retries):
        try:
            serveur_socket.bind(('0.0.0.0', port))
            print(f"'{NOM_MACHINE}' : Socket lié au port {port} après {tentative + 1} tentative(s).")
            return serveur_socket
        except OSError as e:
            if tentative < max_retries - 1:
                print(f"'{NOM_MACHINE}' : Échec de liaison au port {port} ({e}), tentative de libération...")
                liberer_port(port)
                # Délai pour permettre au système de libérer le port
                time.sleep(10)  
            else:
                raise Exception(f"'{NOM_MACHINE}' : Impossible de lier le socket au port {port}.")
    return None


def liberer_port(port):
    """Libère le port spécifié en tuant le processus qui l'utilise."""
    pid = os.popen(f'lsof -t -i:{port}').read().strip()
    if pid:
        os.system(f'kill -9 {pid}')
        print(f"'{NOM_MACHINE}' : Processus {pid} trouvé sur le port {port}")
    else:
        print(f"'{NOM_MACHINE}' : Aucun processus n'utilise le port {port}.")


def accepter_connexion_phase1(serveur_socket, connexions, connexions_phase_2):
    """Accepte les connexions des clients et les gère."""
    while True:
        client_socket, adresse_client = serveur_socket.accept()
        threading.Thread(target=gerer_connexion, args=(client_socket, adresse_client, connexions, connexions_phase_2)).start()


def initialiser_connexions_phase2(machines_reçues, connexions_phase_2):
    """Initialise les connexions entre machines clientes a partir de la phase 2."""
    for machine in machines_reçues:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((machine, PORT2))
            connexions_phase_2[machine] = client_socket
            print(f"{NOM_MACHINE}: Connexion établie avec {machine}")
        except Exception as e:
            print(f"Erreur lors de la connexion à {machine}: {e}")

# ================== Envoi et Réception des messages ==================

def traiter_fichiers(fichiers, chemin, machines_reçues, connexions_phase_2):
    """Lit les fichiers et envoie les mots aux machines clientes."""
    for nom_fichier in fichiers:
        chemin_complet = os.path.join(chemin, nom_fichier)
        try:
            with open(chemin_complet, 'r') as fichier:
                contenu = fichier.read()
                mots = contenu.split()
                
                # Distribution des mots aux machines
                for mot in mots:
                    machine = machines_reçues[len(mot) % len(machines_reçues)]
                    envoyer_message(connexions_phase_2[machine], mot)
        except Exception as e:
            print(f"Erreur avec le fichier {nom_fichier}: {e}")

def traiter_message_json(message_reçu, compteur_mots):
    """Traite un message JSON contenant des mots et leurs fréquences."""
    try:
        mots = message_reçu.split()  
        for mot in mots:
            compteur_mots[mot] = compteur_mots.get(mot, 0) + 1
        return compteur_mots
    except json.JSONDecodeError as e:
        print(f"Erreur lors de la réception du message JSON : {e}")


def accepter_connexion_phase2():
    serveur_socket2 = initialiser_socket(PORT2)
    serveur_socket2.listen(5)
    while True:
        client_socket, adresse_client = serveur_socket2.accept()
        print(f"'PHASE 2 {NOM_MACHINE}' : Connexion acceptée de {adresse_client}")
        threading.Thread(target=gerer_phase_2, args=(client_socket, adresse_client)).start()

def trier_liste_par_frequence_et_mot(liste_mots):
    """Trie une liste de chaînes JSON représentant des dictionnaires par fréquence puis par ordre alphabétique."""
    dictionnaire = {}

    for item in liste_mots:
        item_dict = json.loads(item)
        for mot, frequence in item_dict.items():
            dictionnaire[mot] = frequence

    # Trier le dictionnaire par fréquence puis par ordre alphabétique des mots
    dictionnaire_trie = dict(sorted(dictionnaire.items(), key=lambda x: (x[1], x[0])))
    liste_triee = [json.dumps({mot: frequence}) for mot, frequence in dictionnaire_trie.items()]
    return liste_triee

def gerer_phase_2(client_socket, adresse_client):
    """Gère la reception de la communication entre machines clientes."""
    
    print(f"'PHASE 2 {NOM_MACHINE}' : Gérer phase 2 pour {adresse_client}")
    global etas 
    while True:
        message_reçu = recevoir_message(client_socket)
        if not message_reçu:##
            break
        elif etas ==0:
            mots = message_reçu.split() 
            with verrou_compteur_tri_1:
                for mot in mots:
                    compteur_mots_tri_1[mot] = compteur_mots_tri_1.get(mot, 0) + 1
        elif etas == 1 :
            with verrou_compteur_tri_2:
                    compteur_mots_tri_2.append(message_reçu)

def recevoir_occurrences(machine, message):
    """Reçoit les occurrences des mots envoyés par les machines et recrée le dictionnaire."""
    compteur_mots_fre_global = {}
    try:
        compteur_mots = json.loads(message)
        for mot, occurrence in compteur_mots.items():
            compteur_mots_fre_global[mot] = compteur_mots_fre_global.get(mot, 0) + occurrence
    except Exception as e:
        print(f"Erreur lors de la réception depuis {machine}: {e}")
    return compteur_mots_fre_global


def repartir_mots_par_frequence(dictionnaires, machines_reçues, connexions):
    """Répartit les mots en fonction de leur fréquence aux machines."""
    nombre_de_machines = len(machines_reçues)
    
    for mot, frequence in dictionnaires.items():
        if frequence <= nombre_de_machines:
            machine_index = frequence - 1
        else:
            machine_index = nombre_de_machines - 1
        
        machine = machines_reçues[machine_index]
        try:
            message = json.dumps({mot: frequence})
            envoyer_message(connexions[machine], message)

        except Exception as e:
            print(f"Erreur lors de l'envoi de '{mot}: {frequence}' à {machine}: {e}")

# ================== Envoi et Réception des Phases ==================

def gerer_connexion(client_socket, adresse_client, connexions, connexions_phase_2):
    """Gère toutes les connexions principales."""
    print(f"'{NOM_MACHINE}' : Connexion acceptée de {adresse_client}")
    connexions[adresse_client] = client_socket
    etat = 1
    fichiers = []
    machines_reçues = []
    temps_debut = None

    while True:
        message_reçu = recevoir_message(client_socket)
        if not message_reçu:
            print(f"'{NOM_MACHINE}' : Connexion terminée avec {adresse_client}")
            break
        
        if etat == 1:
            if message_reçu == "FIN PHASE 1":
                etat = 2
                envoyer_message(client_socket, "OK FIN PHASE 1")
                threading.Thread(target=accepter_connexion_phase2).start()
                initialiser_connexions_phase2(machines_reçues, connexions_phase_2)

            elif fichiers or machines_reçues:
                fichiers.append(message_reçu)
            else:
                machines_reçues = json.loads(message_reçu)
                print("machines_reçues", machines_reçues)
        
        elif etat == 2 and message_reçu == "GO PHASE 2":
            etat = 3
            temps_debut = time.time()  
            traiter_fichiers(fichiers, CHEMIN_DES_FICHIERS, machines_reçues, connexions_phase_2)
            
            envoyer_message(client_socket, "OK FIN PHASE 2")
            # Fin du chronométrage réel
            temps_fin = time.time()  
        
        elif etat == 3 and message_reçu == "GO PHASE 3":
            print(f"Temps total entre OK FIN PHASE 1 et GO PHASE 3 : {temps_fin - temps_debut:.2f} secondes")
            envoyer_message(client_socket, json.dumps(compteur_mots_tri_1))
            envoyer_message(client_socket, "OK FIN PHASE 3")
            global etas 
            etas = 1
            etat = 4
        # tous les compteurs de mots sont envoyes au maitre 

        elif etat == 4 and message_reçu == "GO PHASE 4":
            print(f"reception du nv dictionnaire")
        elif etat == 4 : 
            if not message_reçu:
                print(f"'{NOM_MACHINE}' : Connexion terminée avec {adresse_client}")
                break            
            dictionnaire_a_trier = json.loads(message_reçu)
            print(f"reception du nv dictionnaire de {NOM_MACHINE}")
            envoyer_message(client_socket, "OK FIN PHASE 4")
            etat = 5
        # toutes les machines recoivent le dictionnaire a trier des autres workers 

        elif etat == 5 and message_reçu == "GO PHASE 5": 
            repartir_mots_par_frequence(dictionnaire_a_trier, machines_reçues, connexions_phase_2)
            envoyer_message(client_socket, "OK FIN PHASE 5")
            etat = 6

        elif etat == 6 and message_reçu == "GO PHASE 6":
            liste_triee=trier_liste_par_frequence_et_mot(compteur_mots_tri_2)
            envoyer_message(client_socket, json.dumps(liste_triee))
            envoyer_message(client_socket, "OK FIN PHASE 6")
            break


# ================== Fonction Main ==================
def main():
    print(f"'{NOM_MACHINE}' : Démarrage du serveur")
    connexions = {}
    connexions_phase_2 = {}

    serveur_socket = initialiser_socket(PORT)
    serveur_socket.listen(5)
    print(f"'{NOM_MACHINE}' : Serveur écoute sur le port {PORT}")

    threading.Thread(target=accepter_connexion_phase1, args=(serveur_socket, connexions, connexions_phase_2)).start()


if __name__ == "__main__":
    main()