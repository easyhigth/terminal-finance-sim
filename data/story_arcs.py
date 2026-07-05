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
    {
        "id": "fraud_probe",
        "stages": [
            {"delay": 2, "category": "compliance",
             "sender": "Conformité Interne",
             "subject": "Signalement — transaction suspecte",
             "body": ("Une transaction sur le compte de votre client Kariba Mining a "
                      "déclenché un signalement automatique. Rien de grave a priori, "
                      "mais le régulateur local demande des justificatifs. Transmettez "
                      "les documents sous 48h ouvrées pour éviter l'escalade.")},
            {"delay": 8, "category": "compliance",
             "sender": "Conformité Interne",
             "subject": "RE: Signalement Kariba — mise à jour",
             "body": ("Le régulateur a accusé réception des justificatifs. L'enquête "
                      "préliminaire est close, mais votre nom reste dans le dossier. "
                      "Soyez irréprochable sur les prochains trimestres : un deuxième "
                      "signalement déclencherait un audit complet.")},
            {"delay": 12, "category": "compliance",
             "sender": "Conformité Interne",
             "subject": "Clôture — dossier Kariba",
             "body": ("Dossier refermé sans suite. Votre réactivité a joué en votre "
                      "faveur. La conformité vous remercie. Continuez comme ça.")},
        ],
        "effect": {"rep": 2, "cash": 0.0,
                   "reason": "Enquête réglementaire refermée sans suite"},
    },
    {
        "id": "hostile_bid",
        "stages": [
            {"delay": 2, "category": "client",
             "sender": "Bloomberg M&A Desk",
             "subject": "Rumeur : OPA hostile sur Nexora Technologies",
             "body": ("Des rumeurs de rachat circulent sur Nexora Technologies. Un "
                      "fonds activiste aurait accumulé une participation de 7 % et "
                      "préparerait une offre hostile. Le titre a bondi de 12 % en "
                      "after-hours. À surveiller de très près.")},
            {"delay": 6, "category": "client",
             "sender": "Bloomberg M&A Desk",
             "subject": "OPA Nexora : l'offre est déposée",
             "body": ("C'est officiel : le fonds Valiance Capital lance une OPA à "
                      "68 $ par action sur Nexora, soit une prime de 25 %. Le conseil "
                      "recommande de ne pas apporter. Bataille en vue. Vous avez des "
                      "clients exposés au titre ?")},
            {"delay": 10, "category": "client",
             "sender": "Votre Analyste Senior",
             "subject": "Nexora : issue de l'OPA",
             "body": ("L'OPA a échoué : Valiance n'a obtenu que 38 % des titres. "
                      "Le cours retombe à 52 $. Les arbitragistes ont perdu gros. "
                      "J'espère que vous n'étiez pas exposé. Bonne leçon : une OPA "
                      "hostile, c'est jamais gagné d'avance.")},
        ],
        "effect": {"rep": 1, "cash": 5_000.0,
                   "reason": "A bien conseillé ses clients pendant l'OPA Nexora"},
    },
    {
        "id": "whistleblower",
        "stages": [
            {"delay": 2, "category": "research",
             "sender": "Expéditeur Anonyme",
             "subject": "Vous devriez regarder ça...",
             "body": ("Je ne peux pas vous dire qui je suis, mais je travaille chez "
                      "GreenPeak Energy. Leur dernier rapport ESG est truffé de fausses "
                      "déclarations. Les émissions de CO2 sont 3× supérieures à ce "
                      "qu'ils publient. Un journal d'investigation va sortir l'article "
                      "dans quelques semaines. Faites ce que vous voulez de cette info.")},
            {"delay": 7, "category": "research",
             "sender": "Financial Times",
             "subject": "GreenPeak Energy : scandale ESG",
             "body": ("Le FT révèle ce matin que GreenPeak Energy a massivement "
                      "sous-déclaré ses émissions. Le titre plonge de 18 % à "
                      "l'ouverture. Le régulateur environnemental ouvre une enquête. "
                      "Plusieurs fonds ESG annoncent leur désinvestissement.")},
            {"delay": 8, "category": "research",
             "sender": "Votre Comité Éthique",
             "subject": "GreenPeak : vous étiez informé ?",
             "body": ("Le comité éthique a noté que vous aviez réduit votre exposition "
                      "à GreenPeak AVANT la publication du FT. Simple coïncidence ou "
                      "information privilégiée ? Nous classons sans suite vu les "
                      "montants modestes, mais soyez plus prudent à l'avenir.")},
        ],
        "effect": {"rep": -1, "cash": 20_000.0,
                   "reason": "A évité le scandale GreenPeak (zone grise éthique)"},
    },
    {
        "id": "startup_ipo",
        "stages": [
            {"delay": 2, "category": "client",
             "sender": "Votre Banquier d'Affaires",
             "subject": "Mandat IPO — NovaTech AI",
             "body": ("NovaTech AI, une startup d'IA générative, prépare son IPO. "
                      "Ils cherchent un bookrunner. Le deal est risqué (boîte de 3 ans, "
                      "pas encore rentable) mais les commissions sont énormes. Vous "
                      "voulez qu'on pitche ?")},
            {"delay": 5, "category": "client",
             "sender": "Votre Banquier d'Affaires",
             "subject": "NovaTech AI : on a le mandat !",
             "body": ("On a décroché le mandat ! NovaTech nous a choisis comme "
                      "bookrunner. La fourchette de prix est fixée à 22-26 $. Le "
                      "roadshow commence la semaine prochaine. Préparez-vous à "
                      "vendre du rêve.")},
            {"delay": 10, "category": "client",
             "sender": "Votre Banquier d'Affaires",
             "subject": "NovaTech IPO : clôture",
             "body": ("L'IPO est un succès : sursouscrite 8×, le titre ouvre à "
                      "34 $ (+55 %). Les commissions nettes pour la firme s'élèvent "
                      "à 2,4 M$. Félicitations — vous venez de mener votre première "
                      "introduction en bourse.")},
        ],
        "effect": {"rep": 3, "cash": 50_000.0,
                   "reason": "IPO NovaTech AI menée avec succès"},
    },
    {
        "id": "rival_poach",
        "stages": [
            {"delay": 2, "category": "desk",
             "sender": "Chasseur de Têtes Anonyme",
             "subject": "Opportunité confidentielle",
             "body": ("Un concurrent de premier plan m'a mandaté pour vous approcher. "
                      "Ils sont prêts à vous offrir un poste de Managing Director avec "
                      "un package à 7 chiffres. Intéressé pour en discuter ?")},
            {"delay": 6, "category": "desk",
             "sender": "Marcus Vale",
             "subject": "Alors, ce poste chez nous ?",
             "body": ("J'ai entendu dire que tu avais été approché. Laisse-moi te "
                      "donner un conseil : ici, tu construis TA carrière. Là-bas, "
                      "tu seras juste un numéro. Et puis... tu ne voudrais pas que "
                      "je rachète ta firme sans toi pour la défendre, non ?")},
            {"delay": 8, "category": "desk",
             "sender": "Votre Mentor",
             "subject": "Fidélité",
             "body": ("Je sais que vous avez été approché. C'est normal, vous êtes "
                      "bon. Mais la loyauté paie dans ce métier — pas tout de suite, "
                      "mais toujours. Restez, continuez à construire, et vous verrez "
                      "que les opportunités viendront à vous sans avoir à changer "
                      "de crémerie.")},
        ],
        "effect": {"rep": 2, "cash": 0.0,
                   "reason": "A refusé une offre de débauchage — loyauté remarquée"},
    },
]
