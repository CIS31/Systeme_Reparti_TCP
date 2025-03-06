import socket
import json
import struct
import threading
import time

# ================== Configuration et Initialisation =====================

def charger_machines(fichier_machines):
    """Charge les adresses des machines à partir d'un fichier."""
    with open(fichier_machines, 'r') as file:
        return [line.strip() for line in file.readlines()]


def initialiser_connexions(machines, port):
    """Établit des connexions à toutes les machines spécifiées."""
    connexions = {}
    for machine in machines:
        print(f"Tentative de connexion à {machine}")
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((machine, port))
            connexions[machine] = client_socket
            print(f"Connexion établie avec {machine}")
        except Exception as e:
            print(f"Erreur lors de la connexion à {machine}: {e}")
    return connexions


# ================== Gestion des Messages ==================

def envoyer_message(client_socket, message):
    """Envoie un message de taille variable via un socket."""
    message_bytes = message.encode('utf-8')
    taille_message = struct.pack('!I', len(message_bytes))
    client_socket.sendall(taille_message + message_bytes)


def recevoir_exactement(client_socket, n):
    """Reçoit exactement n octets d'un socket."""
    data = b''
    while len(data) < n:
        packet = client_socket.recv(n - len(data))
        if not packet:
            raise ConnectionError("Connexion fermée par le client")
        data += packet
    return data


def recevoir_message(client_socket):
    """Reçoit un message complet (avec taille préfixée) depuis un socket."""
    taille_message = struct.unpack('!I', recevoir_exactement(client_socket, 4))[0]
    data = recevoir_exactement(client_socket, taille_message)
    return data.decode('utf-8')


# ================== Envoi et Réception des messages ==================

def envoyer_fichiers_aux_machines(liste_fichiers, machines, connexions):
    """Distribue les fichiers aux machines selon un schéma circulaire."""
    split_fichiers = [liste_fichiers[i::len(machines)] for i in range(len(machines))]
    for machine, fichiers in zip(machines, split_fichiers):
        try:
            for fichier in fichiers:
                envoyer_message(connexions[machine], fichier)
                print(f"Envoyé '{fichier}' à {machine}")
        except Exception as e:
            print(f"Erreur lors de l'envoi à {machine}: {e}")

def fermer_connexions(connexions):
    """Ferme toutes les connexions ouvertes."""
    for machine, client_socket in connexions.items():
        try:
            client_socket.close()
            print(f"Connexion fermée avec {machine}")
        except Exception as e:
            print(f"Erreur lors de la fermeture de la connexion avec {machine}: {e}")

def trouver_mot_plus_frequent(compteur_mots):
    """
    Trouve le mot avec le plus grand nombre d'occurrences dans un dictionnaire.
    """
    if not compteur_mots:
        return None, 0
    mot, occurrence = max(compteur_mots.items(), key=lambda x: x[1])
    return mot, occurrence
 
def envoyer_messages_aux_machines(machines, connexions, liste_fichiers):
    """Gère l'envoi des messages pour toutes les phases."""
    machines_json = json.dumps(machines)
    for machine in machines:
        try:
            envoyer_message(connexions[machine], machines_json)
            print(f"Envoyé la liste des machines à {machine}")
        except Exception as e:
            print(f"Erreur lors de l'envoi à {machine}: {e}")

    envoyer_fichiers_aux_machines(liste_fichiers, machines, connexions)

    for machine in machines:
        try:
            envoyer_message(connexions[machine], "FIN PHASE 1")
            print(f"Envoyé 'FIN PHASE 1' à {machine}")
        except Exception as e:
            print(f"Erreur lors de l'envoi à {machine}: {e}")

def fusionner_et_diviser_dictionnaires(liste_dictionnaires, nombre_de_machines, index_machine):
    """ 
        Fusionne une liste de dictionnaires en un seul dictionnaire, 
        puis le divise en sous-dictionnaires basés sur l'index de la machine et le nombre de machines.
    """
    # Fusionner les dictionnaires
    dictionnaire_fusionne = {}
    for d in liste_dictionnaires:
        for mot, frequence in d.items():
            if mot in dictionnaire_fusionne:
                dictionnaire_fusionne[mot] += frequence
            else:
                dictionnaire_fusionne[mot] = frequence
    
    # Diviser le dictionnaire fusionné
    items = list(dictionnaire_fusionne.items())
    sous_dictionnaire = {}
    
    for index, (mot, frequence) in enumerate(items):
        if index % nombre_de_machines == index_machine:
            sous_dictionnaire[mot] = frequence
    
    return sous_dictionnaire

# ================== Envoi et Réception des Phases ==================

def recevoir_messages(machines, connexions, tab_fin_phase_1, tab_fin_phase_2, 
                      tab_fin_phase_3,tab_fin_phase_4, tab_fin_phase_5, tab_fin_phase_6):
    global global_compt
    global_compt = []
    etas = 0

    """Gère la réception des messages et l'enchaînement des phases."""

    temps_debut = time.time() 
    while not all(tab_fin_phase_6):
        for machine, client_socket in connexions.items():
            try:
                message = recevoir_message(client_socket)
                index = machines.index(machine)

                if message == "OK FIN PHASE 1" and not tab_fin_phase_1[index]:
                    print(f"Reçu '{message}' de {machine}")
                    tab_fin_phase_1[index] = True
                    if all(tab_fin_phase_1):
                        for client_socket in connexions.values():
                            envoyer_message(client_socket, "GO PHASE 2")
                        
                elif message == "OK FIN PHASE 2" and not tab_fin_phase_2[index]:
                    print(f"Reçu '{message}' de {machine}")
                    tab_fin_phase_2[index] = True
                    if all(tab_fin_phase_2):
                        for client_socket in connexions.values():
                            envoyer_message(client_socket, "GO PHASE 3")
                        

                elif message.startswith("{") and etas == 0:  
                    try:
                        compteur_mots_global = json.loads(message)
                        global_compt.append(compteur_mots_global)  
                        mot, occurrence = trouver_mot_plus_frequent(compteur_mots_global)
                        print(f"{machine} : Mot le plus fréquent : '{mot}' avec {occurrence} occurrences")
                        
                    except json.JSONDecodeError as e:
                        print(f"Erreur JSON dans le message de {machine} : {e}")

                elif message == "OK FIN PHASE 3":
                    print(f"Reçu 'OK FIN PHASE 3' de {machine}")
                    
                    tab_fin_phase_3[index] = True
                    sous_dict = global_compt
                    sous_dictionnaire = fusionner_et_diviser_dictionnaires(sous_dict, len(machines), index)
                    envoyer_message(client_socket, "GO PHASE 4")
                    try:
                        message = json.dumps(sous_dictionnaire)
                        envoyer_message(client_socket, message)
                        print(f"Envoi du sous-dictionnaire à {machine}")
                    except Exception as e:
                        print(f"Erreur lors de l'envoi du sous-dictionnaire à {machine}: {e}")

                elif message == "OK FIN PHASE 4":
                    print(f"Reçu 'OK FIN PHASE 4' de {machine}")
                    etas = 1
                    tab_fin_phase_4[index] = True
                    if all(tab_fin_phase_4):
                        for client_socket in connexions.values():
                            envoyer_message(client_socket, "GO PHASE 5")
                    
                elif message == "OK FIN PHASE 5":
                    print(f"Reçu 'OK FIN PHASE 5' de {machine}")
                    tab_fin_phase_5[index] = True
                    if all(tab_fin_phase_5):
                        for client_socket in connexions.values():
                            envoyer_message(client_socket, "GO PHASE 6")

                elif message == "OK FIN PHASE 6":
                    print(f"Reçu 'FIN' de {machine}")
                    tab_fin_phase_6[index] = True
                    temps_fin = time.time() 

                else:
                    compteur_mots_global2 = json.loads(message)
                    with open(f"resultats.txt", "a") as fichier:
                        for item in compteur_mots_global2:
                            fichier.write(f"{item}\n")

            except Exception as e:
                print(f"Erreur lors de la réception depuis {machine}: {e}")
        

    print(f"Temps total de process entre OK FIN PHASE 1 et OK FIN PHASE 6 : {temps_fin - temps_debut:.2f} secondes")


# ================== Fonction Principale ==================
def main():
    PORT = 4455
    FICHIER_MACHINES = "machines.txt"
    FICHIERS = [
        "fichier_1.warc.wet",
        "fichier_2.warc.wet",
        "fichier_4.warc.wet",
        "fichier_11.warc.wet",
        "fichier_6.warc.wet",
        "fichier_5.warc.wet",
    ]
    global global_compt

    machines = charger_machines(FICHIER_MACHINES)
    connexions = initialiser_connexions(machines, PORT)

    tab_fin_phase_1 = [False] * len(machines)
    tab_fin_phase_2 = [False] * len(machines)
    tab_fin_phase_3 = [False] * len(machines)
    tab_fin_phase_4 = [False] * len(machines)
    tab_fin_phase_5 = [False] * len(machines)
    tab_fin_phase_6 = [False] * len(machines)

    thread_envoi = threading.Thread(target=envoyer_messages_aux_machines, args=(machines, connexions, FICHIERS))
    thread_reception = threading.Thread(target=recevoir_messages, 
                                        args=(machines, connexions, tab_fin_phase_1, tab_fin_phase_2, 
                                              tab_fin_phase_3, tab_fin_phase_4, tab_fin_phase_5, tab_fin_phase_6))

    thread_envoi.start()
    thread_reception.start()

    thread_envoi.join()
    thread_reception.join()

    fermer_connexions(connexions)


if __name__ == "__main__":
    main()