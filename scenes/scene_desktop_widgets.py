"""
scene_desktop_widgets.py — Mixin des overlays « ambiants » du bureau
(DesktopWidgetsMixin) : carte d'accueil, bandeau du tutoriel guidé, widget
patrimoine, carte « Bilan du trimestre », widget « À FAIRE ». Extrait de
`scene_desktop.py` pour limiter sa taille (même principe que les mixins
`scenes/scene_terminal_*.py` du terminal) ; mixé dans `DesktopScene` aux
côtés de `DesktopMenusMixin`.

Ces méthodes ne dessinent RIEN de permanent : elles vivent au-dessus des
fenêtres, informent en un coup d'œil (patrimoine, trimestre, prochaine
étape du tutoriel) même quand tout est fermé/minimisé.
"""
import pygame

from core import config, desktop_onboarding, desktop_tutorial
from core import portfolio_margin as pm_mod
from core.i18n import get_lang
from scenes.scene_desktop_common import _L, TASKBAR_H, TOPBAR_H
from ui import fonts, widgets


class DesktopWidgetsMixin:
    # ------------------------------------------------------ tutoriel guidé
    def _check_tutorial(self):
        """Valide l'étape courante du tutoriel de prise en main dès que l'état
        du bureau la satisfait (fenêtre ouverte, ancrage…) — détection sur
        l'ÉTAT, pas sur le clic, comme le parcours du terminal."""
        if not desktop_onboarding.seen() or desktop_tutorial.done():
            return
        cur = desktop_tutorial.active_step(self)
        if cur is None:
            return
        _idx, step = cur
        try:
            ok = bool(step["check"](self))
        except Exception:
            ok = False
        if not ok:
            return
        if desktop_tutorial.advance():
            self.app.notify(_L("Tutoriel terminé — le poste de travail est à vous !",
                               "Tutorial complete — the workstation is yours!"), "prestige")
        else:
            self.app.notify(_L("Étape validée ✓", "Step complete ✓"), "good")

    def _draw_onboarding(self, surf):
        """Carte d'accueil (1re visite du bureau) : quelques repères pour
        comprendre le poste de travail. NON modale — se referme au clic."""
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        surf.blit(shade, (0, 0))
        W, H = 560, 320
        x = (config.SCREEN_WIDTH - W) // 2
        y = (config.SCREEN_HEIGHT - H) // 2
        card = pygame.Rect(x, y, W, H)
        self._onboard_card = card
        pygame.draw.rect(surf, config.COL_PANEL, card, border_radius=8)
        pygame.draw.rect(surf, config.COL_AMBER, card, 2, border_radius=8)
        widgets.draw_text(surf, _L("Bienvenue sur votre poste de travail",
                                   "Welcome to your workstation"),
                          (x + 24, y + 20), fonts.head(bold=True), config.COL_AMBER)
        lines = [
            _L("• Les icônes ouvrent des APPLICATIONS en fenêtres déplaçables.",
               "• Icons open APPLICATIONS as draggable windows."),
            _L("• Glissez une fenêtre vers un bord pour l'ancrer ; double-clic sur",
               "• Drag a window to an edge to snap it; double-click the title bar"),
            _L("  la barre de titre pour l'agrandir. Alt+Tab pour changer de fenêtre.",
               "  to maximize. Alt+Tab to switch windows."),
            _L("• Le TERMINAL (icône dédiée) reste le moteur : le temps s'écoule même",
               "• The TERMINAL (its own icon) stays the engine: time flows even when"),
            _L("  fenêtre fermée. ⏸/▶▶ en haut à droite règlent la vitesse.",
               "  its window is closed. ⏸/▶▶ top-right control speed."),
            _L("• Clic DROIT sur une icône, une fenêtre ou le fond : menu d'actions.",
               "• RIGHT-click an icon, a window or the background: action menu."),
            _L("• Le widget en bas à droite suit votre patrimoine en direct.",
               "• The bottom-right widget tracks your net worth live."),
            _L("• Ctrl+/ cherche dans vos positions, watchlist, inbox, mandats et deals.",
               "• Ctrl+/ searches your positions, watchlist, inbox, mandates and deals."),
        ]
        ly = y + 58
        for ln in lines:
            widgets.draw_text(surf, ln, (x + 24, ly), fonts.small(), config.COL_TEXT)
            ly += 24
        btn = pygame.Rect(x + W - 160, y + H - 44, 136, 30)
        self._onboard_btn = btn
        hov = btn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_AMBER if hov else config.COL_PANEL_HEAD, btn, border_radius=5)
        pygame.draw.rect(surf, config.COL_AMBER, btn, 1, border_radius=5)
        widgets.draw_text(surf, _L("Commencer", "Get started"), btn.center,
                          fonts.small(bold=True), config.COL_BG if hov else config.COL_AMBER,
                          align="center")

    def _draw_tutorial(self, surf):
        """Bandeau du tutoriel guidé (au-dessus des fenêtres) + halo pulsé sur
        l'icône visée par l'étape courante."""
        cur = desktop_tutorial.active_step(self)
        if cur is None:
            self._tuto_skip_rect = None
            return
        idx, step = cur
        total = len(desktop_tutorial.STEPS)
        W, H = 700, 46
        x = (config.SCREEN_WIDTH - W) // 2
        y = TOPBAR_H + 6
        band = pygame.Rect(x, y, W, H)
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 238))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, config.COL_AMBER, band, 1, border_radius=6)
        widgets.draw_text(surf, _L(f"TUTORIEL {idx + 1}/{total}", f"TUTORIAL {idx + 1}/{total}"),
                          (x + 12, y + 6), fonts.tiny(bold=True), config.COL_CYAN)
        widgets.draw_text(surf, desktop_tutorial.step_title(step),
                          (x + 110, y + 5), fonts.small(bold=True), config.COL_AMBER)
        widgets.draw_text(surf, widgets.fit_text(desktop_tutorial.step_hint(step),
                                                 fonts.tiny(), W - 130),
                          (x + 12, y + 26), fonts.tiny(), config.COL_TEXT)
        skip = pygame.Rect(band.right - 78, y + 5, 68, 18)
        self._tuto_skip_rect = skip
        hov = skip.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, skip, border_radius=4)
        pygame.draw.rect(surf, config.COL_BORDER, skip, 1, border_radius=4)
        widgets.draw_text(surf, _L("Passer", "Skip"), skip.center, fonts.tiny(bold=True),
                          config.COL_TEXT_DIM, align="center")
        # halo pulsé sur l'icône cible (si l'étape en désigne une)
        target = step.get("target")
        info = self._icon_rects.get(target) if target else None
        if info:
            r = info[0]
            pulse = 3 + (pygame.time.get_ticks() // 180) % 4
            pygame.draw.rect(surf, config.COL_AMBER, r.inflate(pulse * 2, pulse * 2), 2,
                             border_radius=10)

    def _draw_ambient(self, surf):
        """Widget « ambiant » du bureau (coin bas-droit, au-dessus de la barre
        des tâches, sous les fenêtres) : patrimoine net, cash, levier et une
        mini-courbe de `player.cash_history` — le pouls du compte reste visible
        même quand toutes les fenêtres sont fermées ou minimisées. Cliquer ouvre
        le portefeuille (fenêtre « book »)."""
        p = self.app.gs.player
        m = self.app.market
        cur = config.CONTINENTS[p.continent]["currency"]
        W, H = 208, 96
        x = config.SCREEN_WIDTH - W - 16
        y = config.SCREEN_HEIGHT - TASKBAR_H - H - 12
        r = pygame.Rect(x, y, W, H)
        self._ambient_rect = r
        hov = r.collidepoint(pygame.mouse.get_pos())
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 232))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, config.COL_AMBER if hov else config.COL_BORDER, r, 1, border_radius=6)
        nw = pm_mod.net_worth(p, m) if m else p.cash
        lev = pm_mod.leverage(p, m) if m else 0.0
        widgets.draw_text(surf, "PATRIMOINE NET", (x + 10, y + 8), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        # variation depuis le début de l'historique (couleur up/down)
        hist = [v for v in (p.cash_history or []) if v]
        base = hist[0] if hist else nw
        up = nw >= base
        widgets.draw_text(surf, widgets.format_money(nw, cur), (x + 10, y + 20),
                          fonts.small(bold=True), config.COL_UP if up else config.COL_DOWN)
        widgets.draw_text(surf, f"Cash {widgets.format_money(p.cash, cur)}", (x + 10, y + 40),
                          fonts.tiny(), config.COL_TEXT)
        levcol = config.COL_DOWN if lev > 2.0 else config.COL_AMBER if lev > 1.0 else config.COL_TEXT_DIM
        widgets.draw_text(surf, f"Levier {lev:.2f}x", (x + 10, y + 54), fonts.tiny(bold=True), levcol)
        # mini-sparkline du patrimoine
        spark = pygame.Rect(x + 10, y + H - 20, W - 20, 14)
        if len(hist) >= 2:
            gcol = config.COL_UP if hist[-1] >= hist[0] else config.COL_DOWN
            widgets.draw_series(surf, spark, hist[-40:], gcol, baseline=False,
                                show_extrema=False, y_fmt=None)

    # -------------------------------------------------- bilan du trimestre
    def _quarter_card_pending(self):
        """Dernier bilan de trimestre non encore acquitté (dict), ou None.
        Posé par GameState.advance_step (flags['last_quarter_report']),
        acquitté par flags['quarter_report_ack'] — persiste donc au save."""
        p = self.app.gs.player
        rep = p.flags.get("last_quarter_report")
        if not rep or not rep.get("total"):
            return None
        if p.flags.get("quarter_report_ack") == rep.get("quarter"):
            return None
        return rep

    def _ack_quarter_card(self):
        p = self.app.gs.player
        rep = p.flags.get("last_quarter_report") or {}
        p.flags["quarter_report_ack"] = rep.get("quarter")

    def _draw_quarter_card(self, surf):
        """Carte de synthèse au changement de trimestre : objectifs atteints,
        récompenses, attribution de performance par source — un moment de
        respiration dans le temps continu, refermé d'un clic."""
        rep = self._quarter_card_pending()
        p = self.app.gs.player
        cur = config.CONTINENTS[p.continent]["currency"]
        W, H = 440, 300
        x = (config.SCREEN_WIDTH - W) // 2
        y = (config.SCREEN_HEIGHT - H) // 2
        card = pygame.Rect(x, y, W, H)
        self._qcard_rects = {"card": card}
        shadow = pygame.Surface((W + 10, H + 10), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 130))
        surf.blit(shadow, (x + 4, y + 5))
        pygame.draw.rect(surf, config.COL_PANEL, card, border_radius=8)
        pygame.draw.rect(surf, config.COL_CYAN, card, 2, border_radius=8)
        widgets.draw_text(surf, _L(f"BILAN DU TRIMESTRE T{rep.get('quarter', '?')}",
                                   f"QUARTER Q{rep.get('quarter', '?')} REVIEW"),
                          (x + 20, y + 16), fonts.head(bold=True), config.COL_CYAN)
        ly = y + 52
        done, total = rep.get("done", 0), rep.get("total", 0)
        col = config.COL_UP if done == total else config.COL_AMBER if done else config.COL_DOWN
        widgets.draw_text(surf, _L(f"Objectifs : {done}/{total} atteints",
                                   f"Objectives: {done}/{total} met"),
                          (x + 20, ly), fonts.small(bold=True), col)
        ly += 24
        if rep.get("rep") or rep.get("cash"):
            widgets.draw_text(surf, _L(f"Récompenses : +{rep.get('rep', 0)} rép · "
                                       f"+{widgets.format_money(rep.get('cash', 0), cur)}",
                                       f"Rewards: +{rep.get('rep', 0)} rep · "
                                       f"+{widgets.format_money(rep.get('cash', 0), cur)}"),
                              (x + 20, ly), fonts.small(), config.COL_TEXT)
            ly += 24
        # attribution de performance : d'où vient la variation du trimestre
        attribution = getattr(p, "last_quarter_attribution", None) or {}
        entries = sorted(attribution.items(), key=lambda kv: -abs(kv[1]))[:4]
        if entries:
            ly += 4
            widgets.draw_text(surf, _L("D'OÙ VIENT LA PERFORMANCE",
                                       "WHERE PERFORMANCE CAME FROM"),
                              (x + 20, ly), fonts.tiny(bold=True), config.COL_TEXT_DIM)
            ly += 20
            for cat, delta in entries:
                sign = "+" if delta >= 0 else ""
                ccol = config.COL_UP if delta >= 0 else config.COL_DOWN
                widgets.draw_text(surf, cat.capitalize(), (x + 28, ly), fonts.tiny(), config.COL_TEXT)
                widgets.draw_text(surf, f"{sign}{widgets.format_money(delta, cur)}",
                                  (x + W - 28, ly), fonts.tiny(bold=True), ccol, align="right")
                ly += 18
        mp = pygame.mouse.get_pos()
        ok_btn = pygame.Rect(x + W - 110, y + H - 44, 90, 30)
        car_btn = pygame.Rect(x + W - 260, y + H - 44, 140, 30)
        self._qcard_rects["ok"] = ok_btn
        self._qcard_rects["career"] = car_btn
        for r, label, accent in ((car_btn, _L("Carrière →", "Career →"), config.COL_TEXT_DIM),
                                 (ok_btn, "OK", config.COL_CYAN)):
            hov = r.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, r, border_radius=5)
            pygame.draw.rect(surf, accent, r, 1, border_radius=5)
            widgets.draw_text(surf, label, r.center, fonts.small(bold=True), accent, align="center")

    def _todo_widget_height(self):
        """Hauteur du widget « À FAIRE » (0 si vide) — calculée à part pour
        que `_draw_calendar_widget` puisse empiler sa propre carte juste
        au-dessus sans dépendre de l'ordre de dessin."""
        from core import todo as todo_mod
        items = todo_mod.suggestions(self.app.gs.player, self.app.market)
        if not items:
            return 0
        return 26 + 20 * len(items) + 6

    def _draw_todo(self, surf):
        """Widget « À FAIRE » (au-dessus du widget patrimoine, sous les
        fenêtres) : les actions en attente les plus prioritaires
        (core/todo.py), chacune cliquable vers la scène concernée — la boucle
        de jeu reste lisible même toutes fenêtres fermées."""
        from core import todo as todo_mod
        self._todo_rects = []
        items = todo_mod.suggestions(self.app.gs.player, self.app.market)
        if not items:
            return
        W = 260
        row_h = 20
        H = 26 + row_h * len(items) + 6
        x = config.SCREEN_WIDTH - W - 16
        # juste au-dessus du widget patrimoine (208x96 + marge, cf. _draw_ambient)
        y = config.SCREEN_HEIGHT - TASKBAR_H - 96 - 12 - H - 8
        r = pygame.Rect(x, y, W, H)
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 232))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=6)
        widgets.draw_text(surf, _L("À FAIRE", "TO DO"), (x + 10, y + 6),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        mp = pygame.mouse.get_pos()
        colors = {"warn": config.COL_AMBER, "bad": config.COL_DOWN, "info": config.COL_CYAN}
        iy = y + 24
        for it in items:
            row = pygame.Rect(x + 4, iy, W - 8, row_h)
            self._todo_rects.append((row, it["scene"]))
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            col = colors.get(it["kind"], config.COL_TEXT)
            pygame.draw.circle(surf, col, (row.x + 8, row.centery), 3)
            widgets.draw_text(surf, widgets.fit_text(it["label"], fonts.tiny(), W - 32),
                              (row.x + 18, row.y + 4), fonts.tiny(), config.COL_TEXT)
            iy += row_h

    # -------------------------------------- résumé condensé « en votre absence »
    def _absence_digest_pending(self):
        """Résumé condensé des notifications reçues depuis la dernière
        consultation (`app.notes.history`, cf. ui/notifications.py) — ne se
        propose que quand le bureau est "vide" (aucune fenêtre hormis le
        Terminal, ouvert ou non) : le joueur revient d'une absence plutôt que
        d'être en train de travailler activement dans une fenêtre. Renvoie
        None si rien de nouveau ou si le bureau n'est pas vide."""
        others = [w for w in self.wm.windows if w.key != "scene:terminal"]
        if others:
            return None
        history = self.app.notes.history
        seen = self.app.gs.player.flags.get("absence_digest_seen", 0)
        if len(history) <= seen:
            return None
        return history[seen:]

    def _ack_absence_digest(self):
        self.app.gs.player.flags["absence_digest_seen"] = len(self.app.notes.history)

    def _draw_absence_digest(self, surf):
        """Carte « EN VOTRE ABSENCE » : les notifications reçues depuis la
        dernière fois que le bureau était vide, groupées par catégorie
        (bonne/mauvaise nouvelle/alerte/info) + les 5 plus récentes en clair —
        pour ne pas avoir à rouvrir plusieurs fenêtres pour reconstituer ce
        qui s'est passé pendant que rien n'était ouvert."""
        entries = self._absence_digest_pending() or []
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 130))
        surf.blit(shade, (0, 0))
        W, H = 460, 320
        x = (config.SCREEN_WIDTH - W) // 2
        y = (config.SCREEN_HEIGHT - H) // 2
        card = pygame.Rect(x, y, W, H)
        self._digest_rects = {"card": card}
        pygame.draw.rect(surf, config.COL_PANEL, card, border_radius=8)
        pygame.draw.rect(surf, config.COL_PRESTIGE, card, 2, border_radius=8)
        widgets.draw_text(surf, _L("EN VOTRE ABSENCE", "WHILE YOU WERE AWAY"),
                          (x + 20, y + 16), fonts.head(bold=True), config.COL_PRESTIGE)
        counts = {}
        for e in entries:
            counts[e["kind"]] = counts.get(e["kind"], 0) + 1
        colors = {"good": config.COL_UP, "bad": config.COL_DOWN, "warn": config.COL_AMBER,
                  "info": config.COL_CYAN, "prestige": config.COL_PRESTIGE}
        labels = {"good": _L("bonnes nouvelles", "good news"),
                  "bad": _L("mauvaises nouvelles", "bad news"),
                  "warn": _L("alertes", "warnings"),
                  "info": _L("infos", "info"),
                  "prestige": _L("évènements notables", "notable events")}
        ly = y + 54
        widgets.draw_text(surf, _L(f"{len(entries)} notification(s) reçue(s)",
                                   f"{len(entries)} notification(s) received"),
                          (x + 20, ly), fonts.small(bold=True), config.COL_TEXT)
        ly += 26
        for kind in ("bad", "warn", "good", "prestige", "info"):
            n = counts.get(kind, 0)
            if not n:
                continue
            col = colors.get(kind, config.COL_TEXT)
            pygame.draw.circle(surf, col, (x + 26, ly + 6), 4)
            widgets.draw_text(surf, f"{n} {labels[kind]}", (x + 38, ly),
                              fonts.tiny(bold=True), col)
            ly += 20
        ly += 8
        widgets.draw_text(surf, _L("DERNIERS MESSAGES", "LATEST MESSAGES"),
                          (x + 20, ly), fonts.tiny(bold=True), config.COL_TEXT_DIM)
        ly += 20
        for e in entries[-5:]:
            widgets.draw_text(surf, widgets.fit_text(e["text"], fonts.tiny(), W - 40),
                              (x + 20, ly), fonts.tiny(),
                              colors.get(e["kind"], config.COL_TEXT))
            ly += 18
        ok_btn = pygame.Rect(x + W - 110, y + H - 44, 90, 30)
        more_btn = pygame.Rect(x + W - 250, y + H - 44, 130, 30)
        self._digest_rects["ok"] = ok_btn
        self._digest_rects["more"] = more_btn
        mp = pygame.mouse.get_pos()
        for r, label, accent in ((more_btn, _L("Tout voir →", "See all →"), config.COL_TEXT_DIM),
                                 (ok_btn, "OK", config.COL_PRESTIGE)):
            hov = r.collidepoint(mp)
            pygame.draw.rect(surf, config.COL_PANEL_HEAD if hov else config.COL_PANEL, r, border_radius=5)
            pygame.draw.rect(surf, accent, r, 1, border_radius=5)
            widgets.draw_text(surf, label, r.center, fonts.small(bold=True), accent, align="center")

    # --------------------------------------------------- indicateur de risque
    def _draw_risk_badge(self, surf, bar):
        """Pastille de risque unifiée (levier/marge/concentration, cf.
        core/risk_indicator.py) — TOUJOURS dans la barre supérieure, donc
        jamais recouverte par une fenêtre. Cliquer ouvre le portefeuille ;
        survoler détaille les raisons dans une bulle. Renvoie le bord GAUCHE
        de la zone dessinée (pour que le badge difficulté voisin s'y cale)."""
        from core import risk_indicator as RI
        p = self.app.gs.player
        m = self.app.market
        if m is None:
            self._risk_badge_rect = None
            return bar.right - 12
        info = RI.assess(p, m)
        colors = {RI.LEVEL_OK: config.COL_UP, RI.LEVEL_WARN: config.COL_AMBER,
                  RI.LEVEL_DANGER: config.COL_DOWN}
        labels = {RI.LEVEL_OK: _L("OK", "OK"), RI.LEVEL_WARN: _L("ATTENTION", "CAUTION"),
                  RI.LEVEL_DANGER: _L("DANGER", "DANGER")}
        col = colors[info["level"]]
        label = labels[info["level"]]
        font = fonts.tiny(bold=True)
        w = font.size(label)[0] + 22
        r = pygame.Rect(bar.right - 12 - w, 6, w, 20)
        self._risk_badge_rect = r
        self._risk_badge_reasons = " · ".join(info["reasons"])
        hov = r.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surf, config.COL_PANEL if hov else config.COL_PANEL_HEAD, r, border_radius=4)
        pygame.draw.rect(surf, col, r, 1, border_radius=4)
        pygame.draw.circle(surf, col, (r.x + 10, r.centery), 4)
        widgets.draw_text(surf, label, (r.x + 18, r.y + 4), font, col)
        if hov:
            widgets.draw_tooltip(surf, self._risk_badge_reasons, pygame.mouse.get_pos())
        return r.x

    # --------------------------------------------- assistant « que faire ? »
    def _draw_assistant_card(self, surf):
        """Carte « ASSISTANT » (F1) : au lieu de laisser le joueur deviner
        quoi faire parmi les nombreuses icônes du bureau, affiche EN GRAND la
        seule action la plus prioritaire (`core/todo.py::suggestions`, déjà
        triée), en langage simple, avec un bouton pour y aller directement —
        le widget « À FAIRE » (compact, coin bas-droit) reste la vue
        d'ensemble ; cette carte est le raccourci "je ne sais pas quoi faire,
        dis-moi juste LA prochaine étape"."""
        from core import todo as todo_mod
        p = self.app.gs.player
        items = todo_mod.suggestions(p, self.app.market)
        shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 130))
        surf.blit(shade, (0, 0))
        W, H = 460, 200
        x = (config.SCREEN_WIDTH - W) // 2
        y = (config.SCREEN_HEIGHT - H) // 2
        card = pygame.Rect(x, y, W, H)
        self._assistant_rects = {"card": card}
        pygame.draw.rect(surf, config.COL_PANEL, card, border_radius=8)
        pygame.draw.rect(surf, config.COL_CYAN, card, 2, border_radius=8)
        widgets.draw_text(surf, _L("ASSISTANT — QUE FAIRE ?", "ASSISTANT — WHAT NOW?"),
                          (x + 20, y + 16), fonts.head(bold=True), config.COL_CYAN)
        close = pygame.Rect(card.right - 34, y + 14, 20, 20)
        self._assistant_rects["close"] = close
        hov_c = close.collidepoint(pygame.mouse.get_pos())
        widgets.draw_text(surf, "×", close.center, fonts.head(bold=True),
                          config.COL_TEXT if hov_c else config.COL_TEXT_DIM, align="center")
        ly = y + 60
        if items:
            top = items[0]
            colors = {"warn": config.COL_AMBER, "bad": config.COL_DOWN, "info": config.COL_CYAN}
            col = colors.get(top["kind"], config.COL_TEXT)
            for ln in widgets.wrap_text_lines(top["label"], fonts.small(bold=True), W - 40):
                widgets.draw_text(surf, ln, (x + 20, ly), fonts.small(bold=True), col)
                ly += 24
            ly += 8
            n_more = len(items) - 1
            if n_more:
                widgets.draw_text(surf, _L(f"+ {n_more} autre(s) action(s) en attente",
                                           f"+ {n_more} more pending action(s)"),
                                  (x + 20, ly), fonts.tiny(), config.COL_TEXT_DIM)
            btn = pygame.Rect(x + 20, y + H - 46, 160, 32)
            self._assistant_rects["go"] = (btn, top["scene"])
            hov = btn.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, config.COL_AMBER if hov else config.COL_PANEL_HEAD, btn, border_radius=5)
            pygame.draw.rect(surf, config.COL_AMBER, btn, 1, border_radius=5)
            widgets.draw_text(surf, _L("Y aller →", "Go there →"), btn.center,
                              fonts.small(bold=True), config.COL_BG if hov else config.COL_AMBER,
                              align="center")
        else:
            widgets.draw_text(surf, _L("Rien d'urgent : tout est sous contrôle.",
                                       "Nothing urgent: everything's under control."),
                              (x + 20, ly), fonts.small(bold=True), config.COL_UP)
            ly += 28
            widgets.draw_text(surf, _L("Vous pouvez surveiller le marché ou passer",
                                       "You can watch the market or move on"),
                              (x + 20, ly), fonts.tiny(), config.COL_TEXT_DIM)
            ly += 18
            widgets.draw_text(surf, _L("à autre chose en attendant.", "to something else meanwhile."),
                              (x + 20, ly), fonts.tiny(), config.COL_TEXT_DIM)

    def _handle_assistant_event(self, event):
        """Gère les clics/touches de la carte Assistant — appelé par
        `handle_event` tant que `self._assistant_open` est vrai (capture tout
        en priorité, comme les autres cartes modales du bureau)."""
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_F1):
            self._assistant_open = False
            return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            close = self._assistant_rects.get("close")
            if close and close.collidepoint(event.pos):
                self._assistant_open = False
                return True
            go = self._assistant_rects.get("go")
            if go:
                btn, scene = go
                if btn.collidepoint(event.pos):
                    self._assistant_open = False
                    self._open_scene_window(scene)
                    return True
            card = self._assistant_rects.get("card")
            if card and not card.collidepoint(event.pos):
                self._assistant_open = False
            return True
        return False

    def _calendar_widget_height(self):
        """Hauteur du widget « CALENDRIER » (0 si vide) — cf. `_todo_widget_height`,
        même besoin pour que `_draw_checklist_widget` empile sa carte au-dessus."""
        events = sorted(self.app.gs.player.macro_events, key=lambda e: e["resolve_step"])[:3]
        if not events:
            return 0
        return 26 + 20 * len(events) + 6

    def _draw_calendar_widget(self, surf):
        """Widget « CALENDRIER » (au-dessus du widget « À FAIRE », sous les
        fenêtres) : les 3 prochains évènements macro programmés
        (core/macrocal.py, player.macro_events) avec un compte à rebours en
        jours — rappel discret sans avoir à ouvrir la fenêtre Calendrier
        dédiée. Cliquer l'ouvre (comme le widget patrimoine → portefeuille)."""
        p = self.app.gs.player
        m = self.app.market
        self._calendar_rect = None
        events = sorted(p.macro_events, key=lambda e: e["resolve_step"])[:3]
        if not events:
            return
        W = 260
        row_h = 20
        H = 26 + row_h * len(events) + 6
        x = config.SCREEN_WIDTH - W - 16
        todo_h = self._todo_widget_height()
        todo_gap = 8 if todo_h else 0
        y = config.SCREEN_HEIGHT - TASKBAR_H - 96 - 12 - todo_h - todo_gap - H - 8
        r = pygame.Rect(x, y, W, H)
        self._calendar_rect = r
        hov = r.collidepoint(pygame.mouse.get_pos())
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 232))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, config.COL_AMBER if hov else config.COL_BORDER, r, 1, border_radius=6)
        widgets.draw_text(surf, _L("CALENDRIER", "CALENDAR"), (x + 10, y + 6),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        step_now = m.step_count if m else 0
        iy = y + 24
        for ev in events:
            steps_left = max(0, ev["resolve_step"] - step_now)
            days_left = steps_left * config.DAYS_PER_STEP
            row = pygame.Rect(x + 4, iy, W - 8, row_h)
            col = config.COL_WARN if days_left <= config.DAYS_PER_STEP else config.COL_TEXT_DIM
            widgets.draw_text(surf, f"J-{days_left}", (row.x, row.y + 4),
                              fonts.tiny(bold=True), col)
            widgets.draw_text(surf, widgets.fit_text(ev["event_type"], fonts.tiny(), W - 60),
                              (row.x + 42, row.y + 4), fonts.tiny(), config.COL_TEXT)
            iy += row_h

    # -------------------------------------------- checklist de routine (pense-bête)
    def _draw_checklist_widget(self, surf):
        """Widget « ROUTINE DU JOUR » (au-dessus du widget CALENDRIER, sous
        les fenêtres) : quelques actions de base à cocher soi-même
        (core/daily_checklist.py) — un pense-bête pour un joueur qui débute,
        pas une contrainte (rien n'empêche de jouer sans les cocher). Se
        réduit tout seul une fois tout coché pour la journée, désactivable
        définitivement dans les Réglages une fois maîtrisée."""
        from core import daily_checklist as DC
        p = self.app.gs.player
        self._checklist_rects = []
        if not DC.is_enabled(p) or DC.all_done_today(p):
            return
        lang = get_lang()
        items = DC.items_for_today(p, lang)
        W = 260
        row_h = 20
        H = 26 + row_h * len(items) + 6
        x = config.SCREEN_WIDTH - W - 16
        todo_h = self._todo_widget_height()
        todo_gap = 8 if todo_h else 0
        cal_h = self._calendar_widget_height()
        cal_gap = 8 if cal_h else 0
        y = (config.SCREEN_HEIGHT - TASKBAR_H - 96 - 12 - todo_h - todo_gap
             - cal_h - cal_gap - H - 8)
        r = pygame.Rect(x, y, W, H)
        panel = pygame.Surface((W, H), pygame.SRCALPHA)
        panel.fill((*config.COL_PANEL, 232))
        surf.blit(panel, (x, y))
        pygame.draw.rect(surf, config.COL_BORDER, r, 1, border_radius=6)
        widgets.draw_text(surf, _L("ROUTINE DU JOUR", "DAILY ROUTINE"), (x + 10, y + 6),
                          fonts.tiny(bold=True), config.COL_TEXT_DIM)
        mp = pygame.mouse.get_pos()
        iy = y + 24
        for it in items:
            row = pygame.Rect(x + 4, iy, W - 8, row_h)
            self._checklist_rects.append((row, it["id"]))
            if row.collidepoint(mp):
                pygame.draw.rect(surf, config.COL_PANEL_HEAD, row, border_radius=3)
            box = pygame.Rect(row.x + 4, row.centery - 6, 12, 12)
            pygame.draw.rect(surf, config.COL_UP if it["done"] else config.COL_TEXT_DIM, box, 1)
            if it["done"]:
                pygame.draw.line(surf, config.COL_UP, (box.x + 2, box.centery),
                                 (box.centerx, box.bottom - 2), 2)
                pygame.draw.line(surf, config.COL_UP, (box.centerx, box.bottom - 2),
                                 (box.right - 1, box.y + 1), 2)
            col = config.COL_TEXT_DIM if it["done"] else config.COL_TEXT
            widgets.draw_text(surf, widgets.fit_text(it["label"], fonts.tiny(), W - 40),
                              (row.x + 22, row.y + 4), fonts.tiny(), col)
            iy += row_h

    def _handle_checklist_click(self, pos):
        for row, item_id in getattr(self, "_checklist_rects", []):
            if row.collidepoint(pos):
                from core import daily_checklist as DC
                DC.toggle(self.app.gs.player, item_id)
                return True
        return False
