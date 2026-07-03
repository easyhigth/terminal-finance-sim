"""
shortcuts_data_en.py — English keyboard shortcuts catalogue (mirror of
data/shortcuts_data.SECTIONS). Accessed via data.shortcuts_data.localized("en").
"""

SECTIONS_EN = [
    ("General — everywhere in the game", [
        ("ESC", "Go up one level: leaves a focused block, closes a floating "
                "window, clears a search, or returns to the previous screen"),
        ("TAB / SHIFT+TAB", "Move to the next/previous interactive block or zone"),
        ("↑ / ↓ / ← / →", "Move the focus based on the real on-screen position of "
                           "the blocks or list/grid items"),
        ("ENTER", "Enter the focused block (1st press) then activate the focused "
                  "inner item (2nd press) — equivalent to a click"),
        ("Letters/digits", "Type into the active search field (blinking cursor = "
                            "editable field) ; filters the displayed list live"),
        ("BACKSPACE", "Delete the last character of the search field"),
        ("Mouse wheel", "Scroll a list or panel under the cursor"),
        ("Keyboard focus", "WHITE bracketed outline = keyboard focus (distinct from "
                            "the cyan mouse hover and the amber selection)"),
    ]),
    ("Lists, grids and catalogues — most screens", [
        ("↑ / ↓ / ← / →", "Select the previous/next item (row, card or grid cell "
                           "depending on the screen: Inbox, Explorer, Academy/Tutorials/"
                           "Certifications, Glossary, Deals, Mandates, Continent picker, "
                           "MORE, command palette…)"),
        ("ENTER", "Activate the selected item: open, buy, load, accept or launch "
                   "depending on the screen — always equivalent to a click"),
        ("Letters/digits", "Filter the list when the screen has a search field"),
        ("ESC", "Clear the current search, otherwise return to the previous screen"),
    ]),
    ("Per-screen exceptions", [
        ("Explorer / Shop — CTRL+F", "Browser-style: gives keyboard focus back to the "
            "search field (handy from the quantity field in Shop) and scrolls back to "
            "the top of the filtered list — search itself is already typable without "
            "any prior action, like most screens"),
        ("Shop — TAB", "Toggles the input focus between search and quantity"),
        ("Team — TAB", "Toggles the focus between the recruitment catalogue and the "
                        "current team ; ENTER hires or fires depending on the active pane"),
        ("Exam / Cert — TAB or ← / →", "Toggles the focus between the exam card and "
                                        "the certification card"),
        ("Mandates — D", "Decline the selected mandate offer (ENTER accepts it)"),
        ("Saves — (mouse only)", "Deleting a save remains intentionally mouse-only, "
            "to avoid accidentally losing a career"),
    ]),
    ("Terminal (main hub) — hierarchical navigation", [
        ("Letters/digits (console focus)", "Type a command on the CMD> line "
            "— the focus is in the console by default, so typing works "
            "immediately as before"),
        ("ENTER (console focus)", "Run the typed command"),
        ("↑ / ↓ (console focus)", "Recall previous/next commands from history"),
        ("TAB (console focus)", "Auto-complete the current command"),
        ("PAGE UP / PAGE DOWN", "Scroll the console history"),
        ("ESC (console focus)", "Goes up to block level (the console stays selected, "
            "white outline visible) — a 2nd ESC at block level opens the menu"),
        ("TAB (block level)", "Moves to the next block: CONSOLE → INDICES → "
            "HEALTH → COMPANIES → CAREER → FEED (SHIFT+TAB to go back)"),
        ("↑ / ↓ / ← / → (block level)", "Moves the focus to the nearest block in "
            "that direction, based on its real position on screen"),
        ("ENTER (INDICES/COMPANIES block)", "Enters the block: the arrow keys "
            "then navigate its inner rows (indices, followed companies)"),
        ("ENTER (HEALTH/CAREER/FEED block)", "Opens the associated scene directly "
            "(these blocks have no navigable inner content)"),
        ("ENTER (inner item)", "Activates the item: opens "
            "an index's chart, opens a followed company's sheet"),
        ("ESC (block level, inside a block)", "Goes back up from the inner content "
            "to block level (e.g. leaves the indices list without leaving the terminal)"),
        ("Worked example", "Focus on the CONSOLE block (empty) → ESC to go up to "
            "block level → ↓ to reach the block below (INDICES) → ENTER to enter it "
            "→ ↑/↓ to pick an index → ENTER to open its chart"),
    ]),
    ("Direct CTRL+letter shortcuts (terminal)", [
        ("COMMAND_NAME", "Each shortcut below corresponds to a typeable "
                         "command in the console (e.g. SHOP, INBOX, NEWS, MORE, SHORTCUTS…)"),
        ("CTRL+M / P / I / N / J", "Market / Portfolio / Inbox / News / Mission"),
        ("CTRL+A / D / F / E", "Mandates / Deals / M&A / Decide"),
        ("CTRL+X / B / T / L / G", "Exam-Cert / Shop / Spreadsheet / Academy / Glossary"),
        ("CTRL+O / S / H / K", "Start menu (all pages) / Save / Help / Command palette"),
        ("CTRL+SHIFT+letter", "Pages only available from the start menu (e.g. CTRL+SHIFT+E "
            "Explorer, +C Career, +B Detailed book, +H History, +T Team, "
            "+R Risk/VaR, +A Macro calendar, +V Annual review, +L Rivals, +S Stress test, "
            "+W Saves, +O Track/specialization) — see the start menu (CTRL+O) for "
            "the full list and search by name"),
        ("CTRL+1 / 2 / 3", "Quick-save to SLOT1/2/3, from any screen in the game "
            "(the SAVE command always saves to SLOT1 only)"),
        ("CTRL+SHIFT+1 / 2 / 3", "Quick-load from SLOT1/2/3, from any screen in the game "
            "(same slots as the SAVE command / Saves screen)"),
        ("Other pages", "Always reachable via CTRL+O (start menu) then arrows/search, "
            "or by typing their command directly (ETF, BONDS, CMDTY, CRYPTO, STRUCT, "
            "CREDIT, SWAP, GOV, FX, OPTIONS, IPO, GP, PA, ATTR, ALERT, QUANT, FRONTIER, "
            "HEDGE, ALM, TUTO, CERT…)"),
    ]),
    ("Desktop — icons as windows", [
        ("TAB / SHIFT+TAB / ↑↓←→", "Gives keyboard focus to a desktop icon (white outline, "
            "no window in front) — TAB cycles the grid in order, arrows move by real "
            "on-screen position ; ENTER launches the icon, ESC clears the focus"),
        ("CTRL+letter", "Directly opens the matching desktop icon as a window "
            "(same mnemonics as the terminal shortcuts above), no click needed — "
            "only if the icon is visible at the current grade"),
        ("CTRL+M / P / I / N / J", "Market / Portfolio / Inbox / News / Mission"),
        ("CTRL+A / D / X / B", "Mandates / Deals / Exam-Cert / Shop"),
        ("CTRL+O", "Toggles the start menu (all pages, searchable by name) — pages "
            "locked by grade show a padlock and an explanatory tooltip, others a short "
            "description on hover/focus"),
        ("CTRL+S / H", "Quick save (slot 1) / Help (commands)"),
        ("CTRL+/", "Global search — positions, watchlist, inbox, mandates, deals "
            "(not to be confused with CTRL+K, the general navigation palette)"),
        ("ALT+TAB / ALT+SHIFT+TAB", "Switches to the next/previous window (OS-style), "
            "whatever screen is currently in front"),
        ("CTRL+SHIFT+D", "Show desktop (Windows+D style): minimizes every open "
            "window ; a 2nd press restores exactly the ones that were open"),
        ("CTRL+SHIFT+Z", "Reopens the last closed window, with its original context "
            "(ticker, filters…) — not the terminal, always reachable via its own icon"),
        ("Right click", "Opens a context menu depending on the target: icon, a "
            "window's title bar, taskbar entry, or the desktop background"),
        ("Right click → Pin", "On a title bar/taskbar entry: keeps this window ALWAYS "
            "on top (small pin in its title bar), even when another window is "
            "focused — handy to keep the watchlist or portfolio visible at all times"),
        ("↑ / ↓ / ENTER / ESC (context menu)", "The context menu (right click) can also "
            "be navigated by keyboard — white outline on the highlighted item, ENTER "
            "activates it, ESC closes without doing anything"),
    ]),
    ("Floating windows and this panel", [
        ("ESC", "Closes the most recent floating window, or this panel if it's open"),
        ("↑ / ↓ / PAGE UP / PAGE DOWN", "Scroll the content (chart, sheet, "
                                        "shortcuts list…)"),
        ("(mouse)", "Drag the title bar to move the window/panel ; "
                    "✕ to close ; wheel to scroll"),
    ]),
]
