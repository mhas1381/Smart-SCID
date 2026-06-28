# 🧠 Smart SCID

**توسعه نرم‌افزاری مصاحبه (Software Development of the Interview)**

> A Django-based web platform that digitizes the SCID-5-CV (Structured Clinical Interview for DSM-5, Clinician Version) — providing clinicians with a guided, rule-driven diagnostic interview system.

---

## 📖 What is Smart SCID?

Smart SCID transforms the paper-based SCID-5-CV interview into an interactive digital system. A clinician registers, creates a patient record, fills out the **Overview** section (demographics, treatment history, suicidal ideation, etc.), and then conducts structured diagnostic interviews module by module. The system enforces **skip logic** (jump rules) based on the patient's answers, automatically navigates the SCID-5 decision tree, and calculates preliminary diagnoses at the end of each module.

All clinical content and questions are in **Persian (Farsi)**.

---

## 🔬 How It Works

### The Interview Flow

```
Register/Login → Create Patient → Fill Overview → Start Module Interview → Answer Questions → Auto-Diagnosis
```

1. **Authentication**: Clinician registers with phone number + password, or logs in via OTP (SMS). JWT tokens are used for all subsequent API calls.

2. **Patient Management**: Clinician creates patient records. Each patient gets an auto-generated anonymized code (`P-YYYYMM-XXXXXX`) to protect identity.

3. **Overview (SCID-5-CV Introductory Section)**: Before starting the diagnostic modules, the clinician fills out the Overview — a comprehensive intake form covering:
   - Demographics & living situation
   - History of current illness
   - Treatment history (medications, hospitalizations)
   - Medical problems
   - **Suicidal ideation & behavior** (with branching logic)
   - Substance use & other current problems

4. **Module Interview**: The clinician starts a module (e.g., Module A — Mood Episodes). The system presents questions one by one. After each answer, **jump rules** are evaluated to determine the next question — skipping irrelevant sections based on the SCID-5 decision tree.

5. **Diagnosis Calculation**: When a module is completed, the system automatically evaluates the collected answers against DSM-5 criteria and returns a diagnosis result.

### Jump Logic (Skip Rules)

The core of the SCID-5 methodology. Each question can have conditional jump rules:

```
If patient answers "No" to A15 (past depression) → Skip to A29 (Mania section)
If patient answers "Yes" to A11 (medical cause) → Skip to A15 (past depression check)
```

Jump rules support these condition types:
- **boolean**: Direct true/false comparison
- **multiple_choice**: Match against a specific choice value
- **text**: Pattern matching in text answers
- **range**: Numeric range checks
- **criteria_count**: Count positive answers across a set of questions (e.g., "if fewer than 5 of A1–A9 are positive, skip")

### Diagnosis Criteria (Module A — Mood Episodes)

| Diagnosis | Rule |
|-----------|------|
| **Major Depressive Episode** | A1 (depressed mood) + ≥4 of A2–A9 (5 total criteria) |
| **Manic Episode** | A29 (elevated mood) + ≥3 of A30–A38 (4 total criteria) |
| **Hypomanic Episode** | A41 (elevated mood, 4+ days) + ≥3 of A42–A50 (4 total criteria) |

---

## 🏗️ Project Structure

```
smart_scid/
├── accounts/                    # User auth, patients, overview, notes
│   ├── models.py                # User, UserProfile, Patient, Overview, PatientNote
│   ├── api/v1/
│   │   ├── views.py             # Auth, patient, overview, notes API endpoints
│   │   ├── serializers.py       # API serializers (registration, OTP, patients, overview)
│   │   └── urls.py              # URL routing for accounts API
│   ├── serializers.py           # Shared serializers (used by interview app)
│   ├── admin.py                 # Custom admin panel configuration
│   └── tests.py                 # 35 tests (auth, patients, overview, notes)
│
├── interview/                   # Interview engine & diagnostic modules
│   ├── models.py                # Interview, InterviewModule, Question, JumpRule, Answer
│   ├── api/v1/
│   │   ├── views.py             # Module, question, interview lifecycle, diagnosis API
│   │   ├── serializers.py       # Interview serializers
│   │   └── urls.py              # URL routing for interview API
│   ├── data/
│   │   └── module_a.json        # Module A data: 90 questions + 15 jump rules
│   ├── management/commands/
│   │   └── load_interview_data.py   # Loads module data from JSON into database
│   ├── admin.py                 # Interview admin with inline questions & answers
│   └── tests.py                 # 21 tests (interview flow, jump logic, diagnosis)
│
├── core/                        # Django project settings & root URL config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── diagnosis/                   # (Planned) Diagnostic algorithms & scoring
├── patients/                    # (Planned) Patient app — currently empty
├── interview_sessions/          # (Planned) Session management — currently empty
├── utils/                       # SMS integration (sms.py) & validators
│
├── manage.py
├── requirements.txt
└── README.md
```

---

## 🚀 Tech Stack

| Technology | Purpose |
|------------|---------|
| **Django 5.2** | Core web framework |
| **Django REST Framework 3.17** | REST API |
| **Simple JWT** | Token-based authentication |
| **drf-spectacular** | OpenAPI/Swagger documentation |
| **SQLite** | Database (PostgreSQL ready) |
| **SMS.ir** | OTP via SMS (mock mode for development) |

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/accounts/register/` | Register with phone + password |
| `POST` | `/api/accounts/token/` | Login (phone + password) → JWT |
| `POST` | `/api/accounts/token/refresh/` | Refresh access token |
| `POST` | `/api/accounts/auth/send-otp/` | Send OTP to phone number |
| `POST` | `/api/accounts/auth/verify-otp/` | Verify OTP → authenticate |
| `POST` | `/api/accounts/auth/set-password/` | Set/change password |

### User Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/accounts/me/` | Current user info |
| `GET/PUT/PATCH` | `/api/accounts/profile/` | Manage profile |

### Patients & Notes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/accounts/patients/` | List/create patients |
| `GET/PUT/PATCH/DELETE` | `/api/accounts/patients/{id}/` | Patient detail |
| `GET/POST` | `/api/accounts/patients/{id}/notes/` | Patient notes |

### Overview (SCID-5-CV Intake)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/accounts/overview-questions/` | Dynamic question schema from model |
| `GET/POST` | `/api/accounts/patients/{id}/overviews/` | List/create overviews |
| `GET/PUT/PATCH` | `/api/accounts/overviews/{id}/` | Overview detail |

### Interview Modules & Questions

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/interviews/modules/` | List active modules |
| `GET` | `/api/interviews/modules/{id}/` | Module detail |
| `GET` | `/api/interviews/questions/?module_id=` | Questions (filterable) |
| `GET` | `/api/interviews/questions/{id}/` | Question detail |

### Interview Lifecycle

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/interviews/interviews/` | List clinician's interviews |
| `GET` | `/api/interviews/interviews/{id}/` | Interview detail + answers |
| `POST` | `/api/interviews/interviews/start/` | Start new interview |
| `POST` | `/api/interviews/interviews/{id}/progress/` | Submit answer → get next question |
| `POST` | `/api/interviews/interviews/{id}/pause/` | Pause interview |
| `POST` | `/api/interviews/interviews/{id}/resume/` | Resume interview |
| `GET` | `/api/interviews/interviews/{id}/summary/` | Completed interview summary + diagnosis |

### Jump Rules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/interviews/jump-rules/` | List all jump rules |
| `GET` | `/api/interviews/jump-rules/{id}/` | Jump rule detail |

---

## 📋 Module A — Mood Episodes (Implemented)

Module A contains **90 questions** (A1–A90) organized into 7 sections:

| Section | Questions | Topic |
|---------|-----------|-------|
| Current Major Depression | A1–A14 | DSM-5 MDE criteria, functional impairment, exclusions |
| Past Major Depression | A15–A28 | History, severity, episode count |
| Current Manic Episode | A29–A40 | Elevated mood, grandiosity, risky behavior, exclusions |
| Current Hypomanic Episode | A41–A53 | 4-day threshold, observable change, exclusions |
| Past Manic Episode | A54–A65 | Historical mania verification |
| Past Hypomanic Episode | A66–A77 | Historical hypomania verification |
| Persistent Depressive Disorder | A78–A90 | 2-year chronic depression, associated symptoms |

**16 jump rules** implement the SCID-5 decision tree for conditional navigation (14 active; 2 reference Module B which is not yet implemented).

---

## 📦 Installation

### Prerequisites

- Python 3.10+
- pip

### Steps

```bash
# Clone
git clone https://github.com/mhas1381/Smart-SCID.git
cd Smart-SCID

# Virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/macOS

# Dependencies
pip install -r requirements.txt

# Migrate database
python manage.py makemigrations
python manage.py migrate

# Load Module A interview data
python manage.py load_interview_data

# Create admin user
python manage.py createsuperuser

# Run server
python manage.py runserver
```

### Access Points

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000/api/` | API root |
| `http://127.0.0.1:8000/admin/` | Django admin panel |
| `http://127.0.0.1:8000/swagger/` | Swagger UI |
| `http://127.0.0.1:8000/api/schema/redoc/` | ReDoc |

---

## 🧪 Testing

```bash
python manage.py test accounts interview --verbosity=2
```

**56 tests** covering:
- User registration, login, OTP flow
- Patient CRUD, soft delete, access control
- Overview creation, branching logic, updates
- Interview start, progress, pause/resume, completion
- Jump rule evaluation
- Diagnosis calculation
- Serializer output validation

---

## 📊 Database Schema

### Core Models

- **User** / **UserProfile**: Custom auth with phone number as identifier. Profile stores role (admin/clinician/researcher), license number, specialization.
- **Patient**: Demographics with auto-generated anonymized code. Soft-delete support.
- **Overview**: ~40 fields mapping to SCID-5-CV intake sections. JSONField for treatment history.
- **PatientNote**: Clinician observations with note types (general/progress/follow_up/referral).
- **InterviewModule**: Named modules (e.g., "Module A — Mood Episodes") with versioning.
- **Question**: Questions with CharField PKs (e.g., "A1"), criteria flags, and jump logic flags.
- **JumpRule**: Conditional routing between questions with JSON metadata.
- **Answer**: JSONField-based answers with typed properties (`boolean_value`, `text_value`, `number_value`).
- **Interview**: Session linking patient + clinician + module, with status tracking and current question pointer.

---

## 📝 Development Status

### ✅ Completed

- [x] JWT + OTP authentication system
- [x] Patient management (CRUD + soft delete + anonymized codes)
- [x] SCID-5-CV Overview section (demographics, treatment, suicidal ideation, substances)
- [x] Clinical notes system
- [x] Interview engine (start, progress, pause, resume, complete)
- [x] **Module A — Mood Episodes** (90 questions, 15 jump rules, auto-diagnosis)
- [x] Jump rule evaluation (boolean, multiple_choice, text, range)
- [x] Diagnosis calculation for Depression, Mania, Hypomania
- [x] Custom admin panel with inline editing
- [x] OpenAPI/Swagger documentation (Persian descriptions)
- [x] 56 passing tests

### 🚧 In Progress

- [ ] **Module B — Psychotic and Associated Symptoms**

### 📋 Planned

- [ ] Module C–M (additional SCID-5-CV modules)
- [ ] Cross-module diagnostic summary
- [ ] PDF clinical report generation
- [ ] Psychometric data aggregation

---

## 📚 API Documentation

Interactive docs available at:
- **Swagger UI**: `/swagger/`
- **ReDoc**: `/api/schema/redoc/`

---

## 👨‍💻 Author

**Mohammad Hossein Esnavandi** — Project Lead & Clinical Architecture

---

## 🙏 Acknowledgments

- Based on the **Structured Clinical Interview for DSM-5® Disorders — Clinician Version (SCID-5-CV)** by the American Psychiatric Association.
- Built with Django and Django REST Framework.
