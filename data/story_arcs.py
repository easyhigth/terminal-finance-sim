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
    {
        "id": "rival_truce",
        "stages": [
            {"delay": 3, "category": "desk", "sender": "Yannick Osei — desk d'en face",
             "subject": "On se croise souvent",
             "body": ("On finit toujours sur les mêmes dossiers, vous et moi. Je "
                      "préfère vous le dire en face plutôt que dans le dos : je vais "
                      "continuer à vous disputer chaque deal. Rien de personnel — "
                      "c'est le métier.")},
            {"delay": 9, "category": "desk", "sender": "Yannick Osei — desk d'en face",
             "subject": "Beau coup, celui-là",
             "body": ("Je ne vous félicite pas souvent, alors autant le faire "
                      "quand c'est mérité : ce que vous avez fait sur votre "
                      "dernier dossier était propre. Ne vous habituez pas aux "
                      "compliments, ça n'arrivera pas tous les mois.")},
            {"delay": 9, "category": "desk", "sender": "Yannick Osei — desk d'en face",
             "subject": "Une trêve, pour une fois",
             "body": ("Un dossier commun nous attend tous les deux ce trimestre — "
                      "trop gros pour se le disputer bêtement. Je propose qu'on "
                      "compare nos lectures avant de foncer chacun de son côté. "
                      "Ça reste entre nous : la rivalité reprendra après.")},
        ],
        "effect": {"rep": 2, "cash": 0.0,
                   "reason": "Respect gagné d'un concurrent direct"},
    },
    {
        "id": "regulator",
        "stages": [
            {"delay": 4, "category": "compliance", "sender": "Inès Duquesne — Autorité de contrôle",
             "subject": "Contrôle de routine",
             "body": ("Rien d'alarmant : c'est un contrôle de routine sur les "
                      "positions à effet de levier de votre desk. Je vous "
                      "recontacterai si un point nécessite une explication de "
                      "votre part. Pas de quoi perdre le sommeil.")},
            {"delay": 10, "category": "compliance", "sender": "Inès Duquesne — Autorité de contrôle",
             "subject": "Dossier clos, proprement",
             "body": ("Le dossier est clos sans réserve — votre tenue de registre "
                      "est plus soignée que la moyenne de la place, ce qui n'est "
                      "pas un compliment que je distribue à la légère. Continuez "
                      "ainsi, ça facilite le travail de tout le monde.")},
            {"delay": 10, "category": "compliance", "sender": "Inès Duquesne — Autorité de contrôle",
             "subject": "Une question, à titre officieux",
             "body": ("En dehors de tout contrôle : on prépare une nouvelle "
                      "grille de lecture du risque de levier et j'aimerais l'avis "
                      "d'un praticien plutôt que d'un seul comité. Votre nom est "
                      "venu naturellement. Rien d'obligatoire, juste un coup de "
                      "fil quand vous aurez un moment.")},
        ],
        "effect": {"rep": 3, "cash": 0.0,
                   "reason": "Crédibilité reconnue par le régulateur"},
    },
    {
        "id": "whale_client",
        "stages": [
            {"delay": 3, "category": "client", "sender": "Solenne Vasseur",
             "subject": "Une allocation test",
             "body": ("On m'a parlé de vous en bien, mais je préfère juger sur "
                      "pièces. Je vous confie une petite part de mon capital — "
                      "un test, pas encore une confiance acquise. Voyons comment "
                      "vous tenez la distance.")},
            {"delay": 11, "category": "client", "sender": "Solenne Vasseur",
             "subject": "Une question directe",
             "body": ("Le marché a bougé et vous n'avez pas paniqué, c'est déjà "
                      "ça. Dites-moi franchement : qu'est-ce qui vous inquièterait "
                      "aujourd'hui si vous étiez à ma place ? Je préfère une "
                      "réponse honnête à une réponse rassurante.")},
            {"delay": 11, "category": "client", "sender": "Solenne Vasseur",
             "subject": "Le test est passé",
             "body": ("Votre franchise valait mieux que n'importe quel argumentaire "
                      "commercial. Je fais rarement confiance aussi vite, mais je "
                      "vais élargir ce que je vous confie. Ne me faites pas regretter "
                      "cette décision.")},
        ],
        "effect": {"rep": 1, "cash": 15_000.0,
                   "reason": "Confiance élargie d'une cliente exigeante"},
    },
]
