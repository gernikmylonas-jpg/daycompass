# Notes for Claude Code (DayCompass)

## Keep the private "hidden readme" up to date
`docs/hidden/` holds a private, educational guide (git-ignored). It describes every file of the project and what it affects.
Whenever you **add, rename, delete or change what a file does**:
1. Update its entry in `docs/hidden/desc_backend.py` or `docs/hidden/desc_frontend.py` (what it is, what it affects).
2. Run `python docs/hidden/build.py` (the import/endpoint/API lists are regenerated from the code).
3. `backend/tests/test_hidden_readme.py` (or `python docs/hidden/build.py --check`) fails if a file is undocumented or the document is stale.

Also refresh the private conversation export when asked: `python docs/hidden/export_conversation.py`.

## Other rules of this project
- Nothing happens unless the user chose it (reminders, wallpapers, offline, push, quests, cycle tracking… are all opt-in).
- Every UI text goes into all four locale files (`en`, `es`, `fr`, `el`).
- Schema changes need an Alembic migration (a test checks it) and an entry in the account export/delete (`routers/account.py`).
- The user commits and pushes themselves; do not commit unless asked.
