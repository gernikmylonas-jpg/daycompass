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
- [x] Docker Compose: Postgres + FastAPI container μαζί — `docker compose --profile full up -d --build` (api + worker + beat + Postgres + Redis)
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

- [x] WebSocket endpoint στο FastAPI (native υποστήριξη, δεν χρειάζεται extra library)
- [x] Live ενημέρωση leaderboard όταν κάποιος κάνει check-in
- [x] Reconnect logic στο frontend

## Φάση 8 — Pomodoro Sessions

- [x] Μοντέλο `PomodoroSession` (τύπος: work/reading, διάρκεια, ολοκληρώθηκε)
- [x] Timer UI (25/5 λεπτά ρυθμιζόμενο)
- [x] Ιστορικό sessions + στατιστικά

## Φάση 9 — Steps & Sleep (Χειροκίνητη Καταγραφή)

- [x] Μοντέλα `StepLog`, `SleepLog` (χειροκίνητη εισαγωγή αρχικά)
- [x] UI για ημερήσια καταχώρηση βημάτων/ύπνου
- [x] Ενσωμάτωση στο ενιαίο σύστημα πόντων

## Πολυγλωσσία (i18n) — ✅ Ολοκληρώθηκε (ανάμεσα στις Φάσεις 9 και 10)

- [x] vue-i18n με 4 γλώσσες: Αγγλικά, Ισπανικά, Γαλλικά, Ελληνικά (τα es/fr/el τυποποιούνται από το en — ένα κλειδί που λείπει σπάει το `vue-tsc`)
- [x] Κουμπί επιλογής γλώσσας στο header με σημαία χώρας προέλευσης (inline SVG: 🇬🇧 🇪🇸 🇫🇷 🇬🇷 — τα flag emoji δεν εμφανίζονται στα Windows)
- [x] Η επιλογή αποθηκεύεται (localStorage), προεπιλογή από τη γλώσσα του browser, fallback στα αγγλικά
- [x] Μήνες/ημέρες/ημερομηνίες μέσω `Intl`, μεταφρασμένα μηνύματα σφαλμάτων backend και ονόματα badges
- [ ] Αυτόματο test κάλυψης κλειδιών/μηνυμάτων (προς το παρόν έλεγχος με script + `vue-tsc`)

> Κάθε νέο UI κείμενο από εδώ και πέρα προστίθεται και στις 4 γλώσσες (`frontend/src/i18n/locales/`).

---

## UI Πυξίδας — ✅ Ολοκληρώθηκε (ανάμεσα στις Φάσεις 10 και 11)

- [x] Home ως πραγματικό καντράν πυξίδας (κλίμακα, Β/Α/Ν/Δ, κεντρικός κύκλος με τους πόντους) — τα γράμματα ακολουθούν τη γλώσσα
- [x] Κέρσορας-βελόνα: δείχνει πάντα τον εσωτερικό κύκλο, πάνω του ηρεμεί προς Βορρά· κρύβεται πάνω σε πεδία κειμένου, μεγαλώνει πάνω σε κουμπιά, απενεργοποιείται σε οθόνες αφής
- [x] Μενού «Ρυθμίσεις» με 7 στυλ πυξίδας: Κλασική (προεπιλογή), Μοντέρνα, Ρετρό, Ναυτική, Εξερευνητή, Νυχτερινή/Neon, Μινιμαλ — και διακόπτη για τον κέρσορα
- [x] Θέματα μέσω σημασιολογικών tokens (`bg-page`, `bg-surface`, `bg-primary`) — ένα νέο στυλ είναι ένα block στο `frontend/src/style.css` + μία εγγραφή στο `stores/settings.ts`
- [x] Οκτώ κατευθύνσεις στο καντράν: Β/Α/Ν/Δ με τα habits, **ΝΔ = Pomodoro**, και τα ΒΑ / ΝΑ / ΒΔ δεσμευμένα ως «σύντομα» (διακεκομμένα μενταγιόν)
- [x] Μεγάλο κεντρικό καντράν (γεμίζει το ύψος της οθόνης)· οι κάρτες ανοίγουν **μόνο όταν πατήσεις το γράμμα**, στην πλευρά της κατεύθυνσης (ΝΔ/Δ/ΒΔ αριστερά, οι υπόλοιπες δεξιά· σε κινητό από κάτω)
- [x] Κάθε γράμμα έχει δαχτυλίδι προόδου (habits ολοκληρωμένα σήμερα / sessions Pomodoro από 4)
- [x] Ο εσωτερικός κύκλος ακολουθεί τον κέρσορα· η βελόνα έχει φυσική ελατηρίου, ripple στο κλικ, count-up στους πόντους
- [x] Προσβασιμότητα: έλεγχος αντίθεσης WCAG AA σε όλα τα 7 στυλ (0 αποτυχίες), skip link, landmarks, ετικέτες σε πεδία/εικονίδια, `role=alert/status`, πληκτρολόγιο στα μενού και στο καντράν (Enter ανοίγει, Esc κλείνει και γυρνά η εστίαση), `prefers-reduced-motion`, `forced-colors`
- [x] **ΒΔ = Groups**, **ΝΑ = Ημερολόγιο** (ανοίγουν ως κάρτες στο καντράν)· τα Βήματα & ύπνος μπήκαν ως επιλογή μέσα στον **Βορρά**. Οι σύνδεσμοι αυτών (και του Pomodoro) αφαιρέθηκαν από την πάνω γραμμή — οι παλιές σελίδες `/groups`, `/calendar`, `/pomodoro`, `/wellness` μένουν μόνο ως άμεσοι σύνδεσμοι
- [x] Το κέντρο είναι σύμβολο (διαφορετικό σε κάθε στυλ) που οδηγεί στη σελίδα **Πόντοι & badges** (`/progress`) με ανάλυση πόντων ανά πηγή
- [x] Στις μοίρες του καντράν φωτίζεται ό,τι βρίσκεται κοντά στη διεύθυνση του κέρσορα, με ένδειξη μοιρών (π.χ. `55°`) — ο εσωτερικός κύκλος δεν κουνιέται πια
- [x] **Νυχτερινή λειτουργία** (Φωτεινή / Σκοτεινή / Όπως η συσκευή) για κάθε στυλ — 14 παλέτες, όλες ελεγμένες για αντίθεση WCAG AA
- [x] Ημερολόγιο 2000–2100 με επιλογή έτους/μήνα και **σημειώσεις ανά μέρα** (γενέθλια με ετήσια επανάληψη, υπενθυμίσεις, γεγονότα, σημειώσεις)
- [x] **Οι ρυθμίσεις ακολουθούν τον λογαριασμό** (στυλ, λειτουργία, κέρσορας, γλώσσα) σε κάθε browser/συσκευή
- [x] Πατώντας το όνομα DayCompass πάνω αριστερά ανοίγουν απλές οδηγίες για κάθε κατεύθυνση
- [x] **Ημερομηνίες παντού ημέρα / μήνας / έτος** (`dd/mm/yyyy`) με δικό μας πεδίο ημερομηνίας (το native του browser ακολουθεί το λειτουργικό)
- [x] **Νότος → Journal:** γραφή + ηχογράφηση φωνής (MediaRecorder), διάθεση, επεξεργασία/διαγραφή, αναπαραγωγή, ιδιωτικό ανά λογαριασμό
- [x] **Ανατολή → Ημερολόγια: Σελήνη & εκλείψεις:** φάσεις σελήνης ανά μέρα (2000–2100), εκλείψεις Ηλίου/Σελήνης, ισημερίες/ηλιοστάσια και βροχές διαττόντων με το φεγγαρόφωτο της κορύφωσης — υπολογισμός στη συσκευή με αλγορίθμους Meeus, ελεγμένος με 15 γνωστές εκλείψεις και φάσεις
- [ ] Email υπενθύμιση για τις σημειώσεις ημερολογίου την ημέρα τους (Celery job, όπως οι υπενθυμίσεις habits)
- [ ] Journal: κρυπτογράφηση σε ηρεμία (σήμερα αποθηκεύεται στη βάση χωρίς κρυπτογράφηση), εξαγωγή
- [ ] Αστρονομία: ορατότητα εκλείψεων ανά τοποθεσία, ανατολή/δύση ηλίου και σελήνης, supermoon
- [ ] Άλλα ημερολόγια στην Ανατολή (π.χ. εορτολόγιο, αργίες) — να οριστεί ποια
- [ ] Να οριστεί τι θα μπει στη ΒΑ (είναι ακόμα δεσμευμένη)

---

## Φάση 10 — Background Jobs & Reminders

- [x] Celery + Redis setup
- [x] Καθημερινή υπενθύμιση αν δεν έγινε check-in — email, opt-in από το Home, στη γλώσσα του χρήστη, 20:00 (ρυθμιζόμενο)
- [x] Νυχτερινό recalculation streaks/βαδίων (ασφαλές fallback) — 03:30: backfill πόντων στόχων, επανέλεγχος badges (streaks), αναφορά drift πόντων (μόνο log, δεν διορθώνει)

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
