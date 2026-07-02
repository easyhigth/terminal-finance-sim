"""
story_arcs.py — Contenu des arcs narratifs de l'inbox (FR, cf. convention
i18n : le contenu profond reste FR). Chaque arc est une petite histoire en
3 messages étalés dans le temps de jeu, avec un dénouement à léger effet
(réputation / trésorerie) — de quoi donner une mémoire et des visages à la
partie, au-delà des évènements mécaniques.

Structure d'un arc :
  id       : identifiant stable (persisté dans player.flags)
  stages   : liste de messages {delay, category, sender, subject, body}
             `delay` = nombre de PAS de marché après le stage précédent
             (après le déclenchement de l'arc pour le premier).
  effect   : appliqué à la livraison du DERNIER message
             {"rep": int, "cash": float, "reason": str}
"""

ARCS = [
    {
        "id": "mentor",
        "stages": [
            {"delay": 2, "category": "manager", "sender": "Victor Kessler",
             "subject": "Des nouvelles du vieux desk",
             "body": ("Alors, on tient le rythme ? J'ai suivi vos débuts de loin. "
                      "Un conseil d'ancien : ne confondez jamais un marché qui monte "
                      "avec du talent. Tenez un journal de vos décisions — vous me "
                      "remercierez au premier retournement.")},
            {"delay": 8, "category": "manager", "sender": "Victor Kessler",
             "subject": "Un service discret",
             "body": ("Un de mes vieux clients me demande un avis sur les valeurs "
                      "industrielles de votre zone. Je n'ai plus l'œil. Jetez un "
                      "coup d'œil à votre écran Recherche et dites-moi ce que vous "
                      "en pensez — sans engagement, c'est votre lecture qui "
                      "m'intéresse.")},
            {"delay": 8, "category": "manager", "sender": "Victor Kessler",
             "subject": "Merci — et bien vu",
             "body": ("Votre lecture était juste, mon client a évité une position "
                      "inconfortable. J'ai glissé votre nom à deux ou trois "
                      "personnes qui comptent. Continuez comme ça : la réputation "
                      "se construit lentement et se perd vite.")},
        ],
        "effect": {"rep": 3, "cash": 0.0,
                   "reason": "Recommandation de votre ancien mentor"},
    },
    {
        "id": "journalist",
        "stages": [
            {"delay": 2, "category": "client", "sender": "Prisca Nardone — La Gazette des Marchés",
             "subject": "Demande d'entretien",
             "body": ("Je prépare un portrait des nouveaux visages de la place. "
                      "Votre nom revient dans plusieurs conversations. Accepteriez-"
                      "vous de répondre à quelques questions sur votre façon de "
                      "travailler ? Rien de piégeux — c'est le desk qui m'intéresse, "
                      "pas les rumeurs.")},
            {"delay": 6, "category": "client", "sender": "Prisca Nardone — La Gazette des Marchés",
             "subject": "L'article avance",
             "body": ("Merci pour le temps accordé. Le papier avance ; mon "
                      "rédacteur en chef veut un angle « nouvelle génération, "
                      "vieilles vertus ». Je recoupe encore deux témoignages et "
                      "je vous tiens au courant de la parution.")},
            {"delay": 6, "category": "client", "sender": "Prisca Nardone — La Gazette des Marchés",
             "subject": "Parution — bonne presse",
             "body": ("L'article est sorti ce matin. Le portrait est flatteur mais "
                      "honnête : rigueur, sang-froid, pas d'esbroufe. Plusieurs "
                      "lecteurs institutionnels m'ont déjà demandé vos coordonnées. "
                      "Bonne continuation — je suivrai la suite de votre carrière.")},
        ],
        "effect": {"rep": 2, "cash": 0.0,
                   "reason": "Portrait flatteur dans la presse financière"},
    },
    {
        "id": "client_worried",
        "stages": [
            {"delay": 2, "category": "client", "sender": "M. Baudry",
             "subject": "Je m'inquiète pour mes économies",
             "body": ("On m'a donné votre nom. Je ne suis pas un gros client — "
                      "l'épargne d'une vie de pharmacien — mais les journaux "
                      "parlent de secousses sur les marchés et je dors mal. "
                      "Pouvez-vous m'expliquer simplement ce qui se passe ?")},
            {"delay": 7, "category": "client", "sender": "M. Baudry",
             "subject": "Merci pour votre patience",
             "body": ("Votre explication m'a rassuré — personne n'avait pris le "
                      "temps de me parler comme à un adulte plutôt qu'à un dossier. "
                      "J'ai décidé de ne pas tout retirer. Ma fille me dit que "
                      "c'était la bonne décision. On verra bien.")},
            {"delay": 7, "category": "client", "sender": "M. Baudry",
             "subject": "Un geste de gratitude",
             "body": ("Les marchés se sont calmés et mes économies ont tenu. Je "
                      "vous envoie un petit mandat de gestion en signe de "
                      "confiance — ce n'est pas grand-chose pour votre desk, mais "
                      "pour moi c'est beaucoup. Merci d'avoir été honnête quand "
                      "c'était facile de ne pas l'être.")},
        ],
        "effect": {"rep": 2, "cash": 8_000.0,
                   "reason": "Fidélité d'un petit client rassuré"},
    },
]
