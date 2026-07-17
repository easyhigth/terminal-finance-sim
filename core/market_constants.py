"""
market_constants.py — paramètres de calibration, fonctions pures et la classe
Crisis du moteur de marché (core/market.py). Extrait verbatim de market.py
(aucun changement de logique) pour garder le moteur stochastique (Market.step()
et ses _step_*) isolé du reste : ce module ne contient QUE des constantes et
des fonctions pures (aucune dépendance à un état de RandomState), donc aucun
risque de désynchroniser la séquence de tirages rng déterministe du jeu.
"""
import numpy as np

HIST_LEN = 400          # ~5.4 ans d'historique conservé (pour les graphes)

# Passé reconstruit AVANT le jour 1 d'une nouvelle partie : les graphes ont ainsi
# de l'ancienneté dès le début (analyse technique, vol, bêta, corrélations...).
# Le marché restant déterministe (graine, nb de pas), ce passé est simplement le
# fait de démarrer la carrière à market_step = WARMUP_STEPS.
STEPS_PER_YEAR = 73     # ~365 jours / DAYS_PER_STEP(5) — pas de marché par an
WARMUP_YEARS = 5
WARMUP_STEPS = WARMUP_YEARS * STEPS_PER_YEAR   # = 365 pas (~5 ans) de préhistoire

# Paramètres des facteurs (par pas ≈ une semaine de marché). Calibrés (sur 12
# graines, 10 ans) pour une PRIME DE RISQUE ACTIONS positive : action moyenne
# ~7%/an (vs cash ~3%, obligations IG ~5%), volatilité ~16%, indice phare ~16%
# (dominé par les grandes capi). Voir tests/test_market.py.
MU_WORLD = 0.0011       # dérive de marché (prime de risque actions)
VOL_WORLD = 0.017
VOL_SECTOR = 0.012
VOL_REGION = 0.010
DRIFT_MULT = 0.2        # atténue les dérives propres des sociétés (anti sur-bull)

# ---- queues épaisses (fat tails) ----------------------------------------
# Les facteurs (monde/secteur/région) et le bruit idiosyncratique ne sont plus
# gaussiens : ils suivent une loi de Student (rng.standard_t), dont les queues
# sont plus épaisses qu'une gaussienne pour un même écart-type — des mouvements
# extrêmes y sont rares mais nettement plus probables que sous une gaussienne
# (kurtosis excédentaire = 6/(df-4) pour df>4). On choisit un df bas (4-6) pour
# un effet perceptible, et on RE-NORMALISE le tirage par son écart-type
# théorique sqrt(df/(df-2)) pour que la volatilité par pas reste calibrée
# EXACTEMENT comme avant (mêmes VOL_WORLD/VOL_SECTOR/VOL_REGION/sigma) : seule
# la FORME de la distribution change, pas son second moment.
T_DF_WORLD = 5      # degrés de liberté du facteur monde (le plus déterminant)
T_DF_SECTOR = 6
T_DF_REGION = 6
T_DF_IDIO = 6        # bruit spécifique de chaque société


def _t_scale(df):
    """Facteur multiplicatif pour ramener un tirage standard_t(df) à un
    écart-type unitaire (variance théorique de Student = df/(df-2), df>2)."""
    return 1.0 / np.sqrt(df / (df - 2.0))


_T_SCALE_WORLD = _t_scale(T_DF_WORLD)
_T_SCALE_SECTOR = _t_scale(T_DF_SECTOR)
_T_SCALE_REGION = _t_scale(T_DF_REGION)
_T_SCALE_IDIO = _t_scale(T_DF_IDIO)

# ---- sauts rares (jump-diffusion), structurels, SOUS les crises scénarisées --
# En plus des queues épaisses du bruit courant, on injecte un saut discret rare
# sur le facteur MONDE (et un peu sur secteurs/régions) — la part « événement
# extrême crédible mais rare » du brief (krach éclair, défaut surprise...).
# Couche structurelle indépendante de core.scenarios.Crisis (qui reste le
# système scénarisé/narratif au-dessus) : ce saut est un AUTRE tirage rng,
# consommé À CHAQUE pas (probabilité testée systématiquement, jamais sautée),
# pour ne jamais désynchroniser la séquence de tirages d'un pas à l'autre.
JUMP_PROBA = 0.012          # ~1.2 %/pas -> en moyenne quelques fois par an
JUMP_MAGNITUDE_MEAN = 0.045  # ampleur moyenne (log-rendement) du saut sur F_monde
JUMP_MAGNITUDE_VOL = 0.02    # dispersion de l'ampleur autour de la moyenne
JUMP_DOWN_BIAS = 0.8         # probabilité qu'un saut soit baissier (krachs > booms)

# ---- effet de levier asymétrique (vol clustering, type GJR-GARCH) ----------
# Dans les marchés réels, une mauvaise nouvelle (rendement négatif) augmente la
# volatilité FUTURE plus qu'une bonne nouvelle de même ampleur (« leverage
# effect » : une baisse de cours augmente le levier financier des entreprises,
# ce qui les rend plus risquées ; + effets de panique/liquidité asymétriques).
# On modélise ceci par un état d'« écart de volatilité » du facteur MONDE,
# multiplicatif autour de 1.0, qui :
#   - revient vers 1.0 (sa valeur neutre = volatilité de base VOL_WORLD) à
#     chaque pas avec une vitesse ASYM_VOL_MEAN_REV (mean reversion, persiste
#     sur plusieurs pas -> clustering, pas un effet d'un seul pas) ;
#   - est poussé À LA HAUSSE par le carré du dernier choc MONDE non-régime
#     (la part "bruit", hors dérive/régime/crise scénarisée), avec un gain
#     ASYM_VOL_DOWN_GAIN si ce choc était négatif, ASYM_VOL_UP_GAIN (plus
#     faible) s'il était positif -> asymétrie du "levier".
# Le facteur world_shock (Crisis scénarisées) et le saut structurel (jump) ne
# sont PAS inclus dans le choc qui alimente cette mise à jour : ce sont déjà
# des chocs explicitement pilotés (vol_mult / scénario), on ne veut pas une
# double comptabilisation, seulement capturer la réaction du marché au BRUIT
# courant (Student-t) du facteur monde.
# Calibration conservatrice : la variance stationnaire de ce processus reste
# proche de 1.0 (voir tests/test_market.py) pour ne pas faire dériver la
# volatilité longue-terme — seule sa DISTRIBUTION DANS LE TEMPS change
# (clustering après une mauvaise nouvelle), pas sa moyenne.
ASYM_VOL_MEAN_REV = 0.12        # vitesse de retour vers 1.0 par pas (~8 pas de demi-vie)
ASYM_VOL_DOWN_GAIN = 1.8        # gain de réaction après un choc monde négatif
ASYM_VOL_UP_GAIN = 0.9          # gain de réaction après un choc monde positif (< down)
ASYM_VOL_MAX_MULT = 2.5         # plafond du multiplicateur de vol (anti-explosion)
ASYM_VOL_MIN_MULT = 0.5         # plancher du multiplicateur de vol
# Les gains DOWN/UP sont ensuite divisés par leur moyenne (cf. step()) pour
# que l'impact moyen attendu (sur un choc symétrique en signe) reste 1.0 :
# seule l'ASYMÉTRIE down/up (leur ratio) influence la volatilité de long
# terme, pas leur niveau moyen — sans cette normalisation, la moyenne des
# deux gains à elle seule biaiserait la moyenne stationnaire de l'état.
_ASYM_VOL_GAIN_AVG = (ASYM_VOL_DOWN_GAIN + ASYM_VOL_UP_GAIN) / 2.0

# ---- corrélations dynamiques (diversification dégradée en stress) --------
# Dans la réalité, la diversification (sectorielle/régionale/spécifique)
# fonctionne bien en période calme mais s'effondre en stress : « les
# corrélations vont à 1 en crise ». Le modèle de facteurs actuel ne produit
# QUE de la corrélation structurelle figée (mêmes beta/b_secteur/b_région en
# permanence) ; on la rend ici DYNAMIQUE en faisant varier, à chaque pas, le
# poids relatif du facteur MONDE (partagé par toutes les sociétés) face aux
# facteurs secteur/région/idiosyncratique (propres à un sous-ensemble), en
# fonction d'un niveau de stress courant.
#
# stress_level (0=calme, 1=stress max) est dérivé de signaux déjà calculés,
# PAS d'une métrique inventée séparément :
#   - world_vol_mult_state (chantier 6) : proxy de stress déjà lissé/persistant
#     (clustering de volatilité du facteur monde) -> normalisé sur sa plage
#     [1.0 (neutre), ASYM_VOL_MAX_MULT] ;
#   - le régime courant (Volatil/Récession) qui ajoute un plancher de stress
#     cohérent avec la toile de fond lente (même hors pic ponctuel de vol).
#
# Mélange : pour les facteurs secteur/région/idio, on injecte une fraction w
# (croissante avec le stress) d'une version du facteur monde RE-NORMALISÉE à
# l'écart-type de chacun, EN PLUS du tirage propre (pas à sa place) :
#   F_X_blend = sqrt(1-w²)·F_X + w·F_world_scaled_to_var(F_X)
# Ce choix précis (plutôt qu'une simple moyenne pondérée (1-w)/w) préserve
# EXACTEMENT la variance MARGINALE de chaque facteur F_X pour tout w (les
# deux termes sont indépendants par construction et de variance respective
# (1-w²)·v_X et w²·v_X -> somme v_X). Mais cela introduit nécessairement de
# la covariance entre F_secteur_blend/F_région_blend/eps_blend (ils partagent
# tous le même w·F_monde) : LE RISQUE TOTAL d'une société (somme des 4 jambes
# du rendement) augmenterait donc mécaniquement avec w si on s'arrêtait là —
# alors que seule la STRUCTURE de corrélation doit changer (cf. brief), pas
# le risque total. On corrige donc la jambe non-monde (secteur+région+idio)
# par un facteur multiplicatif c(w) — calculé par société, en clos, à partir
# des variances/poids propres à CHAQUE société (beta_i, b_secteur_i,
# b_région_i, sigma_i) — qui annule EXACTEMENT cette inflation de variance
# (résolution d'une équation du second degré en c, cf. tests). Au global,
# pour CHAQUE société : Var(rendement total) reste égale à sa valeur à w=0,
# pour tout w — seule la corrélation CROISÉE entre sociétés (via le terme
# partagé w·F_monde, lui non corrigé) augmente avec le stress.
STRESS_VOLMULT_NEUTRAL = 1.0
STRESS_REGIME_FLOOR = {"Expansion": 0.0, "Calme": 0.0, "Volatil": 0.35, "Récession": 0.55}
STRESS_BLEND_W_MAX = 0.85   # poids max du monde dans le mélange (jamais 1.0 -> il
                            # reste toujours un résidu de diversification, même
                            # en stress extrême, comme dans la réalité)


def _stress_level(world_vol_mult_state, regime):
    """Niveau de stress courant (0..1), combinaison continue de l'état
    d'asymétrie de volatilité (chantier 6, déjà lissé/persistant) et d'un
    plancher dépendant du régime de fond courant."""
    vol_excess = max(0.0, world_vol_mult_state - STRESS_VOLMULT_NEUTRAL)
    vol_span = max(1e-9, ASYM_VOL_MAX_MULT - STRESS_VOLMULT_NEUTRAL)
    vol_stress = min(1.0, vol_excess / vol_span)
    regime_floor = STRESS_REGIME_FLOOR.get(regime, 0.0)
    return min(1.0, max(vol_stress, regime_floor))


def _blend_factor_toward_world(own, world_centered, w, own_std, world_std, eps=1e-12):
    """F_X_blend = sqrt(1-w²)·own + w·world_centered_rescalé_à_std(own).

    `own` : array (secteurs, régions, ou sociétés pour eps) déjà à son
    échelle calibrée habituelle. `world_centered` : scalaire, partie centrée
    (bruit+saut, hors dérive) du facteur monde du pas. `own_std`/`world_std` :
    écarts-types THÉORIQUES calibrés (pas mesurés sur l'échantillon du pas :
    plus stable, et permet le calcul EXACT du facteur de correction c(w) en
    aval, qui suppose ces variances connues a priori). Préserve exactement la
    variance THÉORIQUE de own (les deux termes sont d'écarts-types
    sqrt(1-w²)·own_std et w·own_std, donc de variance totale own_std² — la
    corrélation introduite avec le monde, elle, ne s'annule pas)."""
    if w <= 0.0:
        return np.asarray(own, dtype=np.float64)
    if world_std < eps:
        return np.asarray(own, dtype=np.float64)
    world_scaled = world_centered * (own_std / world_std)
    return np.sqrt(max(0.0, 1.0 - w * w)) * own + w * world_scaled


def nonworld_variance_correction(w, v_nonworld0, s_cross, t_cross, beta, world_std):
    """Facteur multiplicatif c(w) appliqué à la jambe non-monde (secteur +
    région + idio) du rendement, qui annule EXACTEMENT l'inflation de
    variance introduite par `_blend_factor_toward_world` sur cette jambe (cf.
    commentaire ci-dessus pour la dérivation). `v_nonworld0`, `s_cross`,
    `t_cross` sont des constantes PAR SOCIÉTÉ (calculées une fois, cf.
    Market.__init__), `beta` le beta de la société, `world_std` l'écart-type
    calibré du facteur monde au pas (VOL_WORLD*vol_mult*world_vol_mult_state).

    Dérivation : avec L = b_sec·F_sec_blend + b_reg·F_reg_blend + sigma·eps_blend,
    Var(L) = v_nonworld0 + w²·s_cross, Cov(F_monde, L) = w·world_std·t_cross.
    On cherche c tel que Var(beta·F_monde + c·L) == Var(beta·F_monde + L)|w=0
    == beta²·world_std² + v_nonworld0, ce qui donne l'équation du second degré
    c²·(v_nonworld0 + w²·s_cross) + 2·c·beta·w·world_std·t_cross - v_nonworld0 = 0,
    dont la racine positive (c(0)=1) est retenue."""
    denom = v_nonworld0 + w * w * s_cross
    safe_denom = np.where(denom < 1e-15, 1.0, denom)
    b_term = beta * w * world_std * t_cross
    disc = b_term * b_term + denom * v_nonworld0
    c = (-b_term + np.sqrt(np.maximum(0.0, disc))) / safe_denom
    return np.where(denom < 1e-15, 1.0, c)


# Régimes de marché — toile de fond lente (déterministe) par-dessus les crises.
# Chaque régime module la dérive et la volatilité du facteur MONDE. Les écarts
# entre régimes sont volontairement marqués (et leur persistance élevée, cf.
# REGIME_TRANSITIONS) pour que des phases bull/bear durables émergent, lisibles
# et exploitables par le market timing — au-delà des chocs ponctuels (Crisis).
REGIMES = {
    "Expansion":  {"drift": 0.0008,  "vol": 0.85, "label": "Expansion"},
    "Calme":      {"drift": 0.0001,  "vol": 0.75, "label": "Marché calme"},
    "Volatil":    {"drift": -0.0004, "vol": 1.70, "label": "Marché volatil"},
    "Récession":  {"drift": -0.0016, "vol": 2.00, "label": "Récession"},
}
# Matrice de transition (par pas ≈ 1 semaine) : forte probabilité de rester dans
# le régime courant -> durée moyenne d'un cycle de l'ordre de plusieurs trimestres
# (1/(1-p_auto) pas), pour des phases identifiables plutôt que du bruit régime à
# régime. Les voisins probables restent cohérents (Expansion <-> Calme,
# Volatil <-> Récession) ; un retournement direct Expansion <-> Récession est rare.
REGIME_TRANSITIONS = {
    "Expansion":  [("Expansion", 0.96), ("Calme", 0.025), ("Volatil", 0.015)],
    "Calme":      [("Calme", 0.95), ("Expansion", 0.035), ("Volatil", 0.015)],
    "Volatil":    [("Volatil", 0.92), ("Calme", 0.04), ("Récession", 0.04)],
    "Récession":  [("Récession", 0.94), ("Volatil", 0.05), ("Calme", 0.01)],
}

# Résultats trimestriels (« earnings ») — saison échelonnée, déterministe
EARN_PERIOD = 13        # ~13 pas (semaines) = un trimestre ; report échelonné
SURPRISE_VOL = 0.05     # écart-type de la surprise de résultats (en % de croissance)
EARN_PRICE_K = 0.9      # conversion surprise -> choc de cours du jour de publication
EARN_NEWS_THRESH = 0.06 # |surprise| au-delà de laquelle on génère une news

# ---- anticipation / pré-positionnement (chantier 13) -----------------------
# Le marché ne devine jamais parfaitement les résultats, mais une fraction des
# acteurs ("smart money") se positionne par anticipation à mesure que la date
# de publication approche, créant un léger drift directionnel AVANT le print —
# phénomène documenté empiriquement ("pre-earnings announcement drift"). La
# PROCHAINE surprise et la PROCHAINE guidance de chaque société sont donc
# déterminées À L'AVANCE, au pas même où le print précédent tombe (un seul
# tirage rng par société par cycle, jamais une fraction de tirage -> aucun
# risque de désynchronisation de la séquence rng). Un petit drift, croissant
# à mesure qu'on approche de la date, est appliqué CHAQUE PAS dans la fenêtre
# d'anticipation, dans le sens de cette surprise déjà tirée (+ un biais issu
# de la guidance du cycle précédent, cf. plus bas). Magnitude volontairement
# modeste : c'est de la couleur de marché (le joueur ne peut pas en déduire le
# print à coup sûr), pas un oracle.
EARN_ANTICIPATION_WINDOW = 4     # pas avant la publication où le drift démarre
EARN_ANTICIPATION_K = 0.10       # fraction de la surprise "pricée" par pas d'anticipation
                                  # (cumulé sur la fenêtre, reste modeste vs le gap du print)

# ---- guidance (prévisions données par l'entreprise) -------------------------
# Composante indépendante (en bonne partie) de la surprise du trimestre écoulé :
# un beat peut s'accompagner d'une guidance prudente et inversement (réalisme,
# crée des dilemmes de lecture). Tirage rng propre, impact prix propre (plus
# petit que le gap de surprise), et vient biaiser le drift d'anticipation du
# PROCHAIN cycle (la guidance d'aujourd'hui nourrit les attentes de demain).
GUIDANCE_VOL = 0.045              # écart-type du signal de guidance
GUIDANCE_SURPRISE_CORR = 0.35     # corrélation partielle avec la surprise du trimestre
GUIDANCE_PRICE_K = 0.35           # impact prix de la guidance (< EARN_PRICE_K du gap)
GUIDANCE_TO_ANTICIPATION_K = 0.6  # poids de la guidance dans le biais d'anticipation suivant
GUIDANCE_RAISE_THRESH = 0.012     # |guidance| au-delà de laquelle on parle de relevée/abaissée
GUIDANCE_LABELS = {"up": "relevée", "flat": "maintenue", "down": "abaissée"}

# ---- révisions d'analystes entre deux publications --------------------------
# Petits évènements de révision, déterministes (seed-derived), entre deux
# trimestres : nudge modeste des attentes + petit choc de cours, distinct
# d'un vrai print de résultats (pas de mise à jour du CA/marges sous-jacents).
REVISION_PROBA = 0.05            # probabilité par pas, par société (hors fenêtre d'annonce)
REVISION_VOL = 0.012             # écart-type du choc de révision
REVISION_PRICE_K = 0.5           # conversion révision -> choc de cours

# ---- drift post-annonce (PEAD) ----------------------------------------------
# Les marchés réels sous-réagissent à l'annonce : le cours continue de dériver
# dans le sens de la surprise pendant plusieurs semaines après le print (« Post
# Earnings Announcement Drift », phénomène documenté). Modélisé comme un état
# persistant par société, injecté en plus du gap du jour J, qui décroît
# géométriquement vers 0.
PEAD_HORIZON_STEPS = 8            # ~2 mois (8 semaines) avant extinction quasi totale
PEAD_DECAY = 0.75                 # décroissance multiplicative par pas (^8 pas -> proche 0)
PEAD_K = 0.16                     # fraction de la surprise injectée en drift cumulé PEAD


CRISIS_SEVERE_SEVERITY = 1.35  # seuil au-delà duquel une crise est jugée "majeure"
CRISIS_COOLDOWN_STEPS = 5      # accalmie forcée après une crise majeure (pas de nouveau choc)

# Courbe des taux : modèle à 3 facteurs (Nelson-Siegel) NIVEAU / PENTE /
# COURBURE, plutôt qu'une simple prime de terme statique. À l'état neutre
# (régime Calme, croissance = mean macro, stress nul), pente et courbure
# cycliques sont nulles par construction : la courbe se réduit exactement à
# l'ancienne prime de terme fixe (short + CURVE_TERM_PREMIUM*years), pour ne
# pas changer les niveaux de rendement déjà calibrés (cf. tests/test_market.py).
#
#   y(tau) = [short + CURVE_TERM_PREMIUM*tau]                     (legacy, niveau+terme, inchangé)
#          + slope_cyclique   * h1(tau)                            (pentification/inversion)
#          + curvature_cyclique * g2(tau)                          (bosse mi-courbe)
#
# où g1/h1/g2 sont les charges de Nelson-Siegel (forme "Diebold-Li", où le
# facteur pente charge le LONG terme et non le court -- convention choisie ici
# pour que slope_cyclique>0 == pentification normale, slope_cyclique<0 ==
# inversion, lisible directement comme dans le brief) :
#   g1(tau) = (1 - exp(-tau/lambda)) / (tau/lambda)      -> 1 en tau=0, 0 en tau=inf
#   h1(tau) = 1 - g1(tau)                                 -> 0 en tau=0, 1 en tau=inf
#   g2(tau) = g1(tau) - exp(-tau/lambda)                  -> 0 en tau=0 ET tau=inf, max en mi-courbe
# (lambda fixe la maturité où la courbure est maximale ; cf. CURVE_NS_LAMBDA).
#
# Pente et courbure sont chacune un état PERSISTANT et lissé (même logique que
# world_vol_mult_state, chantier 6) : elles ne sautent pas instantanément à
# leur cible macro/régime à chaque pas, elles s'en approchent progressivement
# (mean-reversion), pour une dynamique réaliste de la courbe qui ne se
# redessine pas en un seul pas. Mises à jour dans Market.step() (déterministe,
# AUCUN tirage rng supplémentaire : fonctions pures du régime/macro/stress
# déjà calculés ce pas-ci). Le NIVEAU reste le short rate + prime de terme
# (macro["rate"], déjà mean-reverting via son propre AR(1)) : pas dupliqué en
# un 3e état, pour ne pas introduire une double dynamique sur la même grandeur.
CURVE_TENORS = {"3M": 0.25, "2Y": 2.0, "5Y": 5.0, "10Y": 10.0, "30Y": 30.0}
CURVE_TERM_PREMIUM = 0.0015
CURVE_NS_LAMBDA = 5.0    # maturité (années) où la charge de courbure est maximale

# pentification en expansion (le marché anticipe une croissance soutenue),
# aplatissement/inversion en marché volatil/récession (le marché anticipe des
# baisses de taux directeur futures) — cible INSTANTANÉE de la composante
# slope, appliquée via la charge NS h1 (remplace l'ancien poids linéaire capé
# à 10 ans). Amplitudes calibrées (x2 vs l'ancien biais linéaire) pour que la
# pente 10Y-2Y résultante (après charge h1, qui sature progressivement plutôt
# que linéairement) reste du même ordre de grandeur que l'ancien modèle.
_REGIME_SLOPE_BIAS = {"Expansion": 0.0056, "Calme": 0.0, "Volatil": -0.013, "Récession": -0.030}

# courbure cyclique : la "bosse" de mi-courbe s'accentue avec l'incertitude
# (stress de marché, cf. Market.last_stress_level, chantier 7) — un marché
# calme a une courbure quasi nulle, un marché stressé/incertain en a une plus
# marquée en mi-courbe (le court terme intègre une détente monétaire imminente,
# le long terme reste arrimé à l'inflation de long terme, d'où une bosse ~5 ans).
CURVE_CURVATURE_STRESS_GAIN = 0.012   # amplitude de courbure (décimal) à stress=1.0

# vitesse de retour à la cible instantanée (par pas) des états persistants
# pente/courbure -- même constante que world_vol_mult_state (chantier 6) pour
# une demi-vie comparable (~ quelques pas), cohérente avec le reste du moteur.
CURVE_FACTOR_MEAN_REV = 0.18
# bornes anti-explosion des états persistants (mêmes unités que les cibles ;
# couvrent la cible max théorique : régime extrême + croissance extrême).
CURVE_SLOPE_BOUND = 0.05
CURVE_CURV_BOUND = 0.03


def _curve_ns_loadings(years, lam=CURVE_NS_LAMBDA):
    """Charges de Nelson-Siegel (h1, g2) pour une maturité `years` (>=0).
    h1 (pente) croît de 0 (court terme) vers 1 (long terme) ; g2 (courbure)
    est nulle aux deux extrémités et maximale en mi-courbe."""
    tau = max(1e-6, float(years)) / lam
    decay = np.exp(-tau)
    g1 = (1.0 - decay) / tau
    h1 = 1.0 - g1
    g2 = g1 - decay
    return h1, g2


def _curve_slope_target(regime, growth):
    """Cible instantanée de la composante PENTE (décimal), nulle à l'état
    neutre (régime Calme, growth==2.0 -> growth_bias==0)."""
    growth_bias = (growth - 2.0) * 0.003
    return _REGIME_SLOPE_BIAS.get(regime, 0.0) + growth_bias


def _curve_curvature_target(stress_level):
    """Cible instantanée de la composante COURBURE (décimal), nulle hors
    stress (marché calme) -- cf. Market.last_stress_level (chantier 7)."""
    return CURVE_CURVATURE_STRESS_GAIN * max(0.0, min(1.0, stress_level))

# Spreads de crédit IG/HY — niveaux de référence (en points de base), utilisés
# comme indicateurs macro centraux de stress de marché (core.bonds les lit pour
# faire varier le coût d'emprunt des émetteurs notés, core.scenarios pour faire
# dépendre la probabilité de crise de conditions macro cohérentes).
BASE_CREDIT_IG_BPS = 90.0
BASE_CREDIT_HY_BPS = 380.0

# tension ambiante de fond par régime (toile de fond lente, cf. _step_regime) —
# base du niveau de tension affiché au joueur, avant prise en compte des crises actives.
_REGIME_BASE_TENSION = {"Expansion": 8.0, "Calme": 4.0, "Volatil": 42.0, "Récession": 58.0}


class Crisis:
    """Un scénario de crise actif : chocs additionnels sur des facteurs, sur N pas."""
    def __init__(self, name, steps, world=0.0, regions=None, sectors=None, vol_mult=1.0,
                 severity=1.0, kind="bad"):
        self.name = name
        self.steps_left = steps
        self.total_steps = steps
        self.world = world                      # choc additif sur F_monde / pas
        self.regions = regions or {}            # {region_name: choc additif}
        self.sectors = sectors or {}            # {sector_name: choc additif}
        self.vol_mult = vol_mult                # amplificateur de volatilité
        self.severity = severity                # intensité tirée à l'origine (cf. scenarios.py)
        self.kind = kind                         # "bad"/"good" — pour la narration du postmortem
        self.start_nw = None                    # snapshot patrimoine net, posé par l'appelant

# ----- ÉPOQUES DE MARCHÉ (core/market.py) ----------------------------------
# Tirée d'un rng DÉDIÉ dérivé de la seed (ne consomme jamais le rng du
# marché) : ~10 % des graines vivent une « décennie perdue » où la dérive
# monde nette devient légèrement négative — le buy-and-hold passif y PERD,
# et les outils défensifs (short, options, obligations, cash) deviennent la
# seule voie. NB : sur ces graines, les prix diffèrent des versions du jeu
# antérieures à l'époque (assumé et signalé, cf. CLAUDE.md déterminisme).
LOST_DECADE_PROB = 0.10
LOST_DECADE_DRIFT = -0.0016   # ajouté à MU_WORLD (0.0011) -> dérive nette < 0
