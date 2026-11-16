# DayCompass — Οδικός Χάρτης Ανάπτυξης

Στρωματοποιημένος, phased πλάνο για μια εφαρμογή habit tracking + wellness
(steps, sleep, pomodoro) με social/gamification στοιχεία, κτισμένη σε
**Vue 3 + TypeScript** (frontend) και **FastAPI (Python)** (backend), με
**PostgreSQL** ως βάση δεδομένων.

---

## Φάση 0 — Σχεδιασμός (✅ Ολοκληρώθηκε)

- [x] Επιλογή stack: Vue 3 + FastAPI + PostgreSQL
- [x] Ονομασία project: **DayCompass**
- [x] Αρχικό σχήμα βάσης δεδομένων (ERD)
- [x] Απόφαση scope: MVP πρώτα, device integrations & mobile σε επόμενη φάση

---

## Φάση 1 — Backend Θεμέλια

- [x] Δημιουργία FastAPI project (`app/` δομή: `domain/`, `application/`, `infrastructure/`, `api/`)
- [x] Σύνδεση με PostgreSQL (SQLAlchemy) — ⏳ Alembic migrations λείπουν ακόμα (χρησιμοποιούμε `create_all`)
- [ ] Docker Compose: Postgres + FastAPI container μαζί
- [x] Μοντέλα: `User`, `Habit`, `CheckIn`
- [x] JWT authentication (register/login, ίδια λογική με το προηγούμενο project)
- [x] Automatic API docs (FastAPI το κάνει out-of-the-box — δεν χρειάζεται Swashbuckle setup)

## Φάση 2 — Frontend Θεμέλια

- [x] Vite + Vue 3 + TypeScript scaffold
- [x] Tailwind CSS setup
- [x] Login/Register σελίδες
- [x] Auth state management (Pinia — το Vue αντίστοιχο του Context API)
- [x] Βασικό layout + navigation

## Φάση 3 — Core Habit Tracking

- [x] CRUD για habits (δημιουργία, επεξεργασία, διαγραφή)
- [x] Καθημερινό check-in UI
- [x] Streak calculation (τρέχον streak + all-time best)
- [x] Heatmap — συνολικό και ανά habit

## Φάση 4 — Calendar View

- [x] Calendar component — αποφασίστηκε δικό μας (χωρίς `v-calendar`) για λιγότερες εξαρτήσεις
- [x] Μηνιαία/εβδομαδιαία προβολή check-ins
- [x] Προβολή πολλαπλών habits στο ίδιο calendar

## Φάση 5 — Points & Βασικό Gamification

- [x] `total_points` πεδίο στον χρήστη
- [x] Μηχανισμός βαθμολόγησης (πόντοι ανά check-in)
- [x] Πίνακας `Badge` + `UserBadge`
- [x] Λογική απονομής badges (π.χ. "7 μέρες συνεχόμενο streak")

## Φάση 6 — Groups & Challenges

- [x] Μοντέλα `Group`, `GroupMember`
- [x] Δημιουργία/συμμετοχή σε group
- [x] Static leaderboard (top χρήστες ανά group)

## Φάση 7 — Real-time Leaderboard

- [ ] WebSocket endpoint στο FastAPI (native υποστήριξη, δεν χρειάζεται extra library)
- [ ] Live ενημέρωση leaderboard όταν κάποιος κάνει check-in
- [ ] Reconnect logic στο frontend

## Φάση 8 — Pomodoro Sessions

- [x] Μοντέλο `PomodoroSession` (τύπος: work/reading, διάρκεια, ολοκληρώθηκε)
- [x] Timer UI (25/5 λεπτά ρυθμιζόμενο)
- [x] Ιστορικό sessions + στατιστικά

## Φάση 9 — Steps & Sleep (Χειροκίνητη Καταγραφή)

- [ ] Μοντέλα `StepLog`, `SleepLog` (χειροκίνητη εισαγωγή αρχικά)
- [ ] UI για ημερήσια καταχώρηση βημάτων/ύπνου
- [ ] Ενσωμάτωση στο ενιαίο σύστημα πόντων

## Φάση 10 — Background Jobs & Reminders

- [ ] Celery + Redis setup
- [ ] Καθημερινή υπενθύμιση αν δεν έγινε check-in
- [ ] Νυχτερινό recalculation streaks/βαδίων (ασφαλές fallback)

## Φάση 11 — Device Integrations (Backend-only, χωρίς native app)

- [ ] **Google Fit / Health Connect** — OAuth + REST API (βήματα, ύπνος, Android)
- [ ] **Fitbit** — OAuth + REST API
- [ ] **Oura Ring** — OAuth + REST API
- [ ] Πίνακας `DeviceConnection` (αποθήκευση tokens ανά χρήστη/provider)
- [ ] Ημερήσιο sync job (Celery) που τραβάει δεδομένα από συνδεδεμένες συσκευές

> ⚠️ Το **Apple HealthKit** δεν έχει REST API — χρειάζεται υποχρεωτικά native
> (Capacitor) εφαρμογή. Βλ. Φάση 12.

## Φάση 12 — Mobile Εφαρμογή (Capacitor)

- [ ] Ενσωμάτωση Capacitor πάνω στο υπάρχον Vue codebase
- [ ] Native build για Android
- [ ] Native build για iOS
- [ ] Apple HealthKit plugin integration (βήματα, ύπνος — μόνο μέσω native)
- [ ] Push notifications (αντί για email reminders στο mobile)

## Φάση 13 — Παραγωγή & Deployment

- [ ] Environment variables / secrets management (όχι hardcoded όπως στο προηγούμενο project)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Hosting: backend σε Render/Fly.io, frontend σε Vercel/Netlify
- [ ] Production database (managed PostgreSQL)
- [ ] README με πλήρεις οδηγίες build & deploy (ίδιο πρότυπο με το προηγούμενο project)

---

## Σημειώσεις για Αναφορά

- **Δωρεάν τοπική εκτέλεση frontend+backend ταυτόχρονα**: Docker Compose (προτεινόμενο, ήδη γνωστό) ή `concurrently` (npm) για γρήγορη dev εκτέλεση χωρίς containers.
- **Όνομα project**: DayCompass (προσωρινό — να ελεγχθεί ξανά πριν από δημόσια κυκλοφορία, αφού υπάρχει ήδη παρόμοιο branded site "Daily Compass" σε wellness χώρο).
- **Κρίσιμος περιορισμός**: Apple Health δεδομένα ΔΕΝ μπορούν να συγχρονιστούν χωρίς native (Capacitor) εφαρμογή — αυτό δεν είναι τεχνικό κενό μας, είναι σκόπιμος περιορισμός της Apple.
