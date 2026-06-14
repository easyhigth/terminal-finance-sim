"""
main_cheat.py — Lancement du jeu en MODE TEST (triche).

Identique à `python main.py`, mais active des commandes de test dans le terminal
pour tout essayer soi-même sans devoir progresser :

    GRADE <0-11>   règle votre grade (Intern=0 … Partner=11)
    MAXUNLOCK      passe au grade max (toutes les actions débloquées)
    CASH <montant> règle la trésorerie
    REP <0-100>    règle la réputation
    CHEAT          rappelle la liste des commandes de triche

Lancement :  python main_cheat.py
(Le jeu normal — python main.py — n'expose AUCUNE de ces commandes.)
"""
from main import App


class CheatApp(App):
    def __init__(self):
        super().__init__()
        self.cheats = True
        print("=== MODE TEST activé : tapez CHEAT dans le terminal pour la liste "
              "(GRADE <n>, MAXUNLOCK, CASH, REP). ===")


if __name__ == "__main__":
    CheatApp().run()
