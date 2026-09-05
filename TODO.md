# BenX Cross-Platform Feature Parity TODO
Approved plan: Add GTK4 features to web + web features to GTK4. Progress tracked here.

## Current Status
- [x] Analyzed all files (web: index.html/script.js/styles.css; GTK: beautiful_gtk4.py etc.)
- [x] Plan approved by user
- [ ] Step 1: Create TODO.md ✅

## Breakdown (Execute Sequentially)

### Phase 1: GTK4 Enhancements (beautiful_gtk4.py)
1. [x] Add model ComboBox + agent Switch above input (use Config.MODELS, pass to AI) ✅
2. [x] Implement simple markdown parser (bold **, code ``` w/copy btns) in add_chat_message ✅
3. [x] Add net KB/s (psutil.net_io delta) + CPU temp (sensors_temperatures) to stats ✅
4. [ ] Add suggestion chips Gtk.FlowBox below input ("Scan project" etc. → prefill)
3. [ ] Add net KB/s (psutil.net_io delta) + CPU temp (sensors_temperatures) to stats
4. [ ] Add suggestion chips Gtk.FlowBox below input ("Scan project" etc. → prefill)
5. [ ] Add toast system (Gtk.Popover for alerts)
6. [ ] Load history: ai_engine.conversation_history[-20] on startup

### Phase 2: Web Enhancements (index.html, script.js, styles.css, main.py)
7. [ ] Add /api/models endpoint in main.py (from Config.MODELS)
8. [ ] Add /api/toggle_wake, /api/toggle_sysaudio, /api/toggle_call in main.py (log/proxy)
9. [ ] JS: Compact resize (420x560 always-top div), notif bar (minimize), toggle btns → API
10. [ ] HTML/CSS: Meet overlay template + compact/notif styles matching GTK
11. [ ] JS: Window modes (full/compact/min) w/resize/hide/positioning

### Phase 3: Test & Polish
12. [ ] Test GTK: python run_gtk4.py → verify new UI/model/agent/chips etc.
13. [ ] Test Web: bash run_web.sh → verify sync + new toggles/overlay
14. [ ] Cross-test: Send msg GTK → see in web (2s poll), vice versa
15. [ ] Linter/fix + attempt_completion

**Next:** Reply "next" or specify step # to execute (e.g. "do 1-3"). Edits use edit_file w/exact diffs.

