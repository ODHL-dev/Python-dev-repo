# visualiseur_resultats.py
import json
import os
import sys
from tabulate import tabulate  # Vous devrez peut-être installer ce module: pip install tabulate


def charger_resultats(fichier):
    if not os.path.exists(fichier):
        print(f"Le fichier {fichier} n'existe pas.")
        return None

    try:
        with open(fichier, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur lors du chargement des résultats: {e}")
        return None


def afficher_sessions(historique):
    if not historique:
        print("Aucune session trouvée.")
        return

    print("\n=== SESSIONS DE QUIZ ===\n")

    sessions = []
    for i, session in enumerate(historique):
        sessions.append([
            i + 1,
            session.get("session_id", "Inconnu"),
            session.get("date", "Inconnue"),
            session.get("nombre_participants", 0),
            session.get("quiz_file", "Inconnu")
        ])

    print(tabulate(sessions, headers=["#", "ID Session", "Date", "Participants", "Fichier Quiz"]))


def afficher_resultats_session(session):
    print(f"\n=== RÉSULTATS DE LA SESSION {session.get('session_id', 'Inconnue')} ===")
    print(f"Date: {session.get('date', 'Inconnue')}")
    print(f"Quiz: {session.get('quiz_file', 'Inconnu')}")
    print(f"Participants: {session.get('nombre_participants', 0)}\n")

    resultats = session.get("resultats", [])
    if not resultats:
        print("Aucun résultat dans cette session.")
        return

    tableau = []
    for resultat in resultats:
        tableau.append([
            resultat.get("rank", "?"),
            resultat.get("username", "Inconnu"),
            resultat.get("score", 0),
            resultat.get("total_questions", "?"),
            f"{resultat.get('pourcentage_reussite', 0)}%"
        ])

    print(tabulate(tableau, headers=["Rang", "Nom", "Score", "Total", "Réussite"]))


def menu_principal():
    print("\n=== VISUALISEUR DE RÉSULTATS DE QUIZ ===\n")
    fichier = input("Entrez le nom du fichier de résultats [resultats.json]: ").strip() or "resultats.json"

    historique = charger_resultats(fichier)
    if not historique:
        return

    while True:
        afficher_sessions(historique)

        choix = input("\nEntrez le numéro de la session à consulter (ou q pour quitter): ").strip()
        if choix.lower() == 'q':
            break

        try:
            index = int(choix) - 1
            if 0 <= index < len(historique):
                afficher_resultats_session(historique[index])
                input("\nAppuyez sur Entrée pour continuer...")
            else:
                print("Numéro de session invalide.")
        except ValueError:
            print("Veuillez entrer un numéro valide.")


if __name__ == "__main__":
    # Si un fichier est spécifié en argument, l'utiliser directement
    if len(sys.argv) > 1:
        historique = charger_resultats(sys.argv[1])
        if historique:
            afficher_sessions(historique)
            if len(historique) > 0:
                afficher_resultats_session(historique[-1])  # Afficher la dernière session
    else:
        menu_principal()