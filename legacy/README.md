# Legacy baseline scripts

These are the baseline Tkinter desktop scripts provided with the assignment.
They are kept **unchanged** (apart from normalising line endings to LF) for
traceability: every feature of the Flask application maps back to one of them.
They are **not** part of the application, the Docker image or the lint/test
scope.

## Version lineage

| Script | Features introduced | Ported to (Flask) |
|---|---|---|
| `Aceestver-1.0.py` | Program catalogue (Fat Loss, Muscle Gain, Beginner) with weekly workout and diet plan | `GET /api/programs`, `/programs` page |
| `Aceestver-1.1.py` | Client profile (name, age, weight), calorie estimate = weight × program factor, adherence slider | `POST /api/calculators/calories`, client calories |
| `Aceestver1.1.2.py` | In-memory client list, CSV export, adherence bar chart | Client list API/UI (CSV export out of scope) |
| `Aceestver2.0.1.py` | SQLite persistence for clients and weekly progress | `/api/clients` CRUD, `/api/clients/<name>/progress` |
| `Aceestver-2.1.2.py` | Identical to 2.0.1 | — |
| `Aceestver-2.2.1.py` | Progress chart per client | Progress list + bar view on client page |
| `Aceestver-2.2.4.py` | Height, goals (target weight/adherence), 4 program variants, workouts + exercises log, body metrics, BMI with risk category, client summary | Workouts, metrics, BMI, summary endpoints |
| `Aceestver-3.0.1.py` | Identical to 2.2.4 | — |
| `Aceestver-3.1.2.py` | Login window, rule-based "AI" program generator by experience level, PDF report | `/api/auth/*`, `POST /api/clients/<name>/program` (PDF out of scope) |
| `Aceestver-3.2.4.py` | Role-based login, membership status and renewal date | `GET /api/clients/<name>/membership` |

## Defects found in the baseline (fixed in the Flask port)

| Script | Defect | Resolution in Flask app |
|---|---|---|
| `Aceestver1.1.2.py` | `reset()` calls `_update_text(self.diet_text,)` with a missing argument → `TypeError` | Not applicable (no Tkinter UI); input handling covered by tests |
| `Aceestver-2.2.4.py` / `3.0.1.py` | `DROP TABLE clients` when the schema is outdated → silent data loss | Schema uses `CREATE TABLE IF NOT EXISTS` only; never drops data |
| `Aceestver-3.1.2.py` / `3.2.4.py` | Default `admin/admin` user stored with a plain-text password | Passwords stored as salted hashes; admin password configurable via environment |
| `Aceestver-3.2.4.py` | Uses `tk.simpledialog` without importing it → `AttributeError` | Not applicable (no Tkinter UI) |
| `Aceestver-3.1.2.py` / `3.2.4.py` | Program generator uses the global random state → not reproducible or testable | Generator takes an injectable, seedable random source |
| All | Client data keyed by free-text name, no referential integrity | Child tables reference `clients.id` with foreign keys and cascading deletes |
