# 🧠 Smart SCID

**توسعه نرمافزاری مصاحبه (Software Development of the Interview)**

> A Django-based web platform that digitizes the SCID-5-CV (Structured Clinical Interview for DSM-5, Clinician Version) — providing clinicians with a guided, rule-driven diagnostic interview system.

---

## 📖 What is Smart SCID?

Smart SCID transforms the paper-based SCID-5-CV interview into an interactive digital system. A clinician registers, creates a patient record, fills out the **Overview** section (demographics, treatment history, suicidal ideation, etc.), and then conducts structured diagnostic interviews module by module. The system enforces **skip logic** (jump rules) based on the patient's answers, automatically navigates the SCID-5 decision tree, and calculates preliminary diagnoses at the end of each module.

All clinical content and questions are in **Persian (Farsi)**.

---

## 📖 Table of Contents

1. [How It Works](#-how-it-works)
2. [Project Structure](#-project-structure)
3. [Tech Stack](#-tech-stack)
4. [API Endpoints](#-api-endpoints)
5. [Module Status](#-module-status)
6. [Diagnosis Algorithm](#-diagnosis-algorithm)
7. [Jump Rules System](#-jump-rules-system)
8. [Output Format Reference](#-output-format-reference)
9. [Admin Panel & UI](#-admin-panel--ui)
10. [Roadmap — Next Modules](#-roadmap--next-modules)
11. [Installation](#-installation)
12. [Testing](#-testing)
13. [Database Schema](#-database-schema)

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

---

## 🏗️ Project Structure

```
smart_scid/
├── accounts/                    # User auth, patients, overview, notes
│   ├── models.py                # User, UserProfile, Patient, Overview, PatientNote
│   ├── api/v1/
│   │   ├── views.py             # Auth, patient, overview, notes API endpoints
│   │   ├── serializers.py       # API serializers
│   │   └── urls.py              # URL routing for accounts API
│   ├── serializers.py           # Shared serializers (used by interview app)
│   ├── admin.py                 # Custom admin panel configuration
│   └── tests.py                 # 35 tests
│
├── interview/                   # Interview engine & diagnostic modules
│   ├── models.py                # Interview, InterviewModule, Question, JumpRule, Answer
│   ├── api/v1/
│   │   ├── views.py             # Module, question, interview lifecycle, diagnosis API
│   │   ├── serializers.py       # Interview serializers
│   │   └── urls.py              # URL routing for interview API
│   ├── data/
│   │   ├── module_a.json        # Module A: 90 questions + 16 jump rules
│   │   ├── module_b.json        # Module B: 24 questions + 5 jump rules
│   │   ├── module_c.json        # Module C: 30 questions + 5 jump rules
│   │   └── module_d.json        # Module D: 28 questions + 9 jump rules
│   ├── management/commands/
│   │   └── load_interview_data.py   # Loads module data from JSON into database
│   ├── admin.py                 # Interview admin with inline questions & answers
│   └── tests.py                 # 21 tests
│
├── core/                        # Django project settings & root URL config
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
│
├── static/admin/css/
│   └── custom_admin.css         # Custom admin panel styling (dark/light mode)
│
├── manage.py
├── requirements.txt
└── README.md                    # ← This file (single source of truth)
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

## 📋 Module Status

### ✅ Module A — Mood Episodes

**90 questions** (A1–A90), **16 jump rules**, auto-diagnosis for Depression, Mania, Hypomania.

| Section | Questions | Topic |
|---------|-----------|-------|
| Current Major Depression | A1–A14 | DSM-5 MDE criteria, functional impairment, exclusions |
| Past Major Depression | A15–A28 | History, severity, episode count |
| Current Manic Episode | A29–A40 | Elevated mood, grandiosity, risky behavior, exclusions |
| Current Hypomanic Episode | A41–A53 | 4-day threshold, observable change, exclusions |
| Past Manic Episode | A54–A65 | Historical mania verification |
| Past Hypomanic Episode | A66–A77 | Historical hypomania verification |
| Persistent Depressive Disorder | A78–A90 | 2-year chronic depression, associated symptoms |

### ✅ Module B — Psychotic and Associated Symptoms

**24 questions** (B1–B24), **5 jump rules**, symptom profile output.

| Section | Questions | Topic |
|---------|-----------|-------|
| Delusions | B1–B11 | Reference, persecutory, grandiose, somatic, guilt, jealous, religious, erotomanic, thought control |
| Hallucinations | B12–B17 | Auditory, visual, tactile, somatic, gustatory, olfactory |
| Disorganized Speech/Behavior | B18–B19 | Loose associations, tangentiality, disorganized behavior |
| Catatonia | B20 | Stupor, grimacing, posturing, stereotypy, mutism, negativism |
| Negative Symptoms | B21–B22 | Avolition, diminished emotional expressiveness |
| Exclusion Criteria | B23–B24 | Due to medical condition, due to substance |

### ✅ Module C — Differential Diagnosis of Psychotic Disorders

**30 questions** (C1–C30), **5 jump rules**, differential diagnosis output.

| Questions | Disorder | Criteria |
|-----------|----------|----------|
| C1 | Gate question | Psychosis outside mood episodes? |
| C2–C6 | Schizophrenia | All 5 DSM-5 criteria (A through E) |
| C7–C8 | Schizophreniform | Same as SZ but duration 1–6 months |
| C9–C12 | Schizoaffective | Mood episode + psychosis overlap |
| C13–C17 | Delusional Disorder | Delusions ≥1 month without SZ criteria |
| C18 | (text) | Delusion type specifier |
| C19–C21 | Brief Psychotic Disorder | 1 day – 1 month, full recovery |
| C22–C25 | Other Specified | Doesn't meet any specific criteria |
| C26–C30 | Chronology | Current vs remission for each disorder |

### ✅ Module D — Differential Diagnosis of Mood Disorders

**28 questions** (D1–D28), **9 jump rules**, differential diagnosis output.

| Questions | Track | Criteria |
|-----------|-------|----------|
| D1 | Gate question | Clinically significant mood symptoms? |
| D2–D7, D25 | Bipolar I | Manic episode + exclusions + severity + chronology |
| D8–D16, D26 | Bipolar II | MDE + hypomanic episode + exclusions + severity + chronology |
| D17–D21, D27 | MDD | Depressed mood + exclusions + severity + chronology |
| D22–D24, D28 | Other Depressive | Subthreshold symptoms + distress + exclusions + chronology |

### ✅ Module E — Substance Use Disorders

**35 questions** (E1–E22, E37–E49), **12 jump rules**, alcohol + substance use disorder diagnosis with severity classification.

| Section | Questions | Topic |
|---------|-----------|-------|
| Alcohol Gate | E1 | ≥6 drinks in past 12 months? (→ E14 if false) |
| Alcohol Use Disorder Criteria | E2–E12 | 11 DSM-5 criteria: impaired control, social impairment, risky use, tolerance, withdrawal |
| Alcohol Threshold | E13 | ≥2 criteria met? (→ always E14) |
| Substance Gate | E14 | Any non-alcohol substance use? (→ END if false) |
| Substance Screening | E15–E22 | 8 substance classes: sedatives, cannabis, stimulants, opioids, PCP, hallucinogens, inhalants, other (→ E37 if true) |
| Primary Substance ID | E37 | Free text: which substance caused most problems |
| Substance Use Disorder Criteria | E38–E48 | 11 DSM-5 criteria (same as alcohol, for primary substance) |
| Substance Threshold | E49 | ≥2 criteria met? |

**Severity Classification** (DSM-5): Mild = 2–3, Moderate = 4–5, Severe = 6+

---

## 🧠 Diagnosis Algorithm

### Architecture

```
InterviewProgressView.post()
  ├── Save / update Answer
  ├── _get_next_question()
  │     ├── Evaluate JumpRules for current question (first match wins)
  │     └── Fall-through: next question by order
  └── If no next question → mark completed → _calculate_diagnosis()
```

**Module detection** is done via module name pattern matching in `_calculate_diagnosis()`:

```python
if 'Mood Episodes' in interview.module.name:                     # Module A
elif 'Differential Diagnosis of Psychotic' in interview.module.name:  # Module C
elif 'Mood Disorders' in interview.module.name:                  # Module D
elif 'Psychotic' in interview.module.name:                       # Module B
```

> ⚠️ Module C must be checked before Module B because both contain "Psychotic" in the name.
> Module D must be checked after Module C because Module D's name also contains "Differential Diagnosis".

### Answer Value Format

| question_type | value format | accessor property |
|---|---|---|
| `boolean` | `{"boolean": true}` | `answer.boolean_value` |
| `text` | `{"text": "..."}` | `answer.text_value` |
| `number` | `{"number": 5}` | `answer.number_value` |
| `multiple_choice` | `{"text": "choice_label"}` | `answer.text_value` |

### Module A — Diagnosis Logic

```python
# Depression: need A1 + 4 of A2-A9 (5 total including A1)
depression_criteria = ['A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'A7', 'A8', 'A9']
depression.diagnosed = count >= 5

# Mania: need A29 + 3 of A30-A38 (4 total including A29)
mania_criteria = ['A29', 'A30', 'A31', 'A32', 'A33', 'A34', 'A35', 'A36', 'A37', 'A38']
mania.diagnosed = count >= 4

# Hypomania: need A41 + 3 of A42-A50 (4 total including A41)
hypomania_criteria = ['A41', 'A42', 'A43', 'A44', 'A45', 'A46', 'A47', 'A48', 'A49', 'A50']
hypomania.diagnosed = count >= 4
```

### Module B — Symptom Profile

Module B produces a **symptom profile**, NOT a specific diagnosis. The note in the output states that Module C is required for differential diagnosis.

```python
delusion_ids = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11']
hallucination_ids = ['B12', 'B13', 'B14', 'B15', 'B16', 'B17']
disorganized_ids = ['B18', 'B19']
catatonic_ids = ['B20']
negative_ids = ['B21', 'B22']
```

### Module C — Decision Tree

```
C1: Psychotic symptoms outside mood episodes?
  │
  ├── NO → Psychotic Mood Disorder → proceed to Module D
  │
  └── YES → evaluate C2–C25
            │
            ├─ C2-C6: Schizophrenia (5/5) → C26
            ├─ C7-C8: Schizophreniform (2/2) → C27
            ├─ C9-C12: Schizoaffective (4/4) → C28
            ├─ C13-C17: Delusional (5/5) → C18(type) + C29
            ├─ C19-C21: Brief Psychotic (3/3) → C30
            ├─ C22-C25: Other Specified (4/4)
            └─ None met → Undifferentiated
```

**Priority:** First matching disorder wins (Schizophrenia > Schizophreniform > ... > Other Specified).

### Module D — Decision Tree

```
D1: Clinically significant mood symptoms?
  │
  ├── NO → no significant mood symptoms → END
  │
  └── YES ↓
D2: Manic episode criteria met?
  ├── YES → Bipolar I track (D3-D7, D25)
  └── NO → D8: At least one MDE?
              ├── NO → D22 (Other Depressive)
              └── YES → D9: Hypomanic episode?
                          ├── NO → MDD track (D17-D21, D27)
                          └── YES → D10-D14: Bipolar II criteria
                                      ├── ALL YES → Bipolar II (D15-D16, D26)
                                      └── ANY NO → MDD track (D17-D21, D27)
```

**Priority:** Bipolar I > Bipolar II > MDD > Other Depressive > Unspecified.

### Module C Jump Rules

| From | Condition | To | Meaning |
|------|-----------|-----|---------|
| C1 | `answer == false` | END | Only mood psychosis → end, go to Module D |
| C2 | `criteria_count < 2` of C2-C6 | C13 | SZ criterion A not met → skip to Delusional |
| C6 | `criteria_count_met >= 4` of C2-C6 | C9 | Full SZ criteria met → skip to Schizoaffective |
| C8 | `answer == false` | C9 | Schizophreniform not met → Schizoaffective |
| C12 | `answer == false` | C13 | Schizoaffective not met → Delusional |

### Module D Jump Rules

| From | Condition | To | Meaning |
|------|-----------|-----|---------|
| D1 | `answer == false` | END | No significant mood symptoms |
| D2 | `answer == false` | D8 | No manic episode → assess BP-II/MDD |
| D5 | `answer == false` | D25 | BP-I confirmed, no current episode → chronology |
| D7 | `text, match=""` | D25 | BP-I severity entered → chronology |
| D9 | `answer == false` | D17 | No hypomanic episode → assess MDD |
| D11 | `answer == false` | D17 | Hypomanic < 4 days → not BP-II |
| D15 | `answer == false` | D26 | BP-II confirmed, no current depressive → chronology |
| D16 | `text, match=""` | D26 | BP-II severity entered → chronology |
| D21 | `text, match=""` | D27 | MDD severity entered → chronology |

### Module E — Diagnosis Logic

```python
# Phase 1: Alcohol Use Disorder (E1-E12)
# Gate: E1=True (≥6 drinks in past year)
# Criteria: E2-E12 (11 DSM-5 criteria, is_criteria=True)
# Threshold: E13 (≥2 criteria met)
# Severity: mild (2-3), moderate (4-5), severe (6+)

# Phase 2: Substance Screening (E14-E22)
# Gate: E14=True (any non-alcohol substance)
# Screening: E15-E22 (8 substance classes)
# Tracks which substances were reported

# Phase 3: Substance Use Disorder (E37-E49)
# Primary substance: E37 (free text)
# Criteria: E38-E48 (11 DSM-5 criteria)
# Threshold: E49 (≥2 criteria met)
# Severity: same thresholds as alcohol
```

### Module E Jump Rules

| From | Condition | To | Meaning |
|------|-----------|-----|---------|
| E1 | `answer == false` | E14 | No alcohol → skip to substance screening |
| E13 | always | E14 | After alcohol threshold → continue to substance screening |
| E14 | `answer == false` | END | No substances → end interview |
| E15–E21 | `answer == true` | E37 | Substance reported → primary substance ID |
| E22 | `answer == true` | E37 | Other substance reported → primary substance ID |
| E22 | `answer == false` | END | No substances reported → end interview |

### Module F — Diagnosis Logic

```python
# 4 independent anxiety disorders, each assessed sequentially:

# 1. Panic Disorder (F1-F7)
# Gate: F1=True (panic attack in past month)
# Criteria: F2 (persistent worry or behavioral change)
# Exclusions: F3 (not substance), F4 (not medical), F5 (not other disorder)
# All must be true → diagnosed
# Severity: F6 (text), Chronology: F7 (text)

# 2. Agoraphobia (F8-F19)
# Gate: F8=True (fear of ≥2 situations)
# Situations: F9-F13 (transport, open, enclosed, queues, alone) — count ≥2
# Criteria: F14 (avoidance/distress), F15 (disproportionate fear)
# Exclusions: F16 (not substance/medical), F17 (not other disorder)
# Gate + ≥2 situations + F14 + F15 + F16 + F17 → diagnosed
# Severity: F18 (text), Chronology: F19 (text)

# 3. Social Anxiety Disorder (F20-F28)
# Gate: F20=True (fear of social situations)
# Criteria: F21 (fear of negative evaluation), F22 (persistent fear), F23 (avoidance)
# Exclusions: F24 (disproportionate — checked but not exclusionary),
#             F25 (not substance/medical), F26 (not other disorder)
# All must be true → diagnosed
# Severity: F27 (text), Chronology: F28 (text)

# 4. Generalized Anxiety Disorder (F29-F40)
# Gate: F29=True (excessive worry ≥6 months)
# Criteria: F30 (difficulty controlling worry)
# Associated symptoms: F31-F36 (restlessness, fatigue, concentration,
#                       irritability, muscle tension, sleep) — count ≥3
# Exclusions: F37 (not substance/medical), F38 (not other disorder)
# Gate + F30 + ≥3 symptoms + F37 + F38 → diagnosed
# Severity: F39 (text), Chronology: F40 (text)
```

### Module F Jump Rules

| From | Condition | To | Meaning |
|------|-----------|-----|---------|
| F1 | `answer == false` | F8 | No panic attacks → skip to Agoraphobia |
| F6 | `text, match=""` | F7 | Severity entered → chronology |
| F7 | `text, match=""` | F8 | Chronology entered → Agoraphobia |
| F8 | `answer == false` | F20 | No agoraphobia → skip to Social Anxiety |
| F18 | `text, match=""` | F19 | Severity entered → chronology |
| F19 | `text, match=""` | F20 | Chronology entered → Social Anxiety |
| F20 | `answer == false` | F29 | No social anxiety → skip to GAD |
| F27 | `text, match=""` | F28 | Severity entered → chronology |
| F28 | `text, match=""` | F29 | Chronology entered → GAD |
| F29 | `answer == false` | END | No GAD → end interview |
| F39 | `text, match=""` | F40 | Severity entered → chronology |

---

## 🔄 Jump Rules System

**Model:** `JumpRule` (see `interview/models.py`)

Each rule links a `from_question` → `to_question` (nullable; `null` = end interview).

**Evaluation order:** Rules for the current question are evaluated in database order. The **first match wins**. If no rule matches, sequential next question by `order`.

### Condition Types

| condition_type | logic | returns True when |
|---|---|---|
| `boolean` | `answer.boolean_value == metadata.expected_value` | answer matches expected |
| `multiple_choice` | `answer.text_value == metadata.expected_value` | text matches |
| `text` | `metadata.match_pattern in answer.text_value` | substring match |
| `range` | `metadata.min_value <= answer.number_value <= metadata.max_value` | number in range |
| `criteria_count` | `count(positive answers in metadata.question_ids) < metadata.min_count` | count is BELOW threshold (skip trigger) |
| `criteria_count_met` | `count(positive answers in metadata.question_ids) >= metadata.min_count` | count is AT or ABOVE threshold (proceed trigger) |

> **Key distinction:**
> - `criteria_count` → triggers when criteria are **NOT** met (used for skip-ahead)
> - `criteria_count_met` → triggers when criteria **ARE** met (used for conditional routing)

### metadata Field Reference

```json
{
  "expected_value": true,
  "question_ids": ["B1"],
  "min_count": 1,
  "match_pattern": "text",
  "min_value": 0,
  "max_value": 100,
  "note": "human-readable description"
}
```

---

## 📊 Output Format Reference

### Module-Specific Fields

| Module | Key Fields |
|--------|------------|
| A | `depression`, `mania`, `hypomania` (each: `diagnosed`, `symptoms_counted`, `required_symptoms_count`, `criteria_met`) |
| B | `psychotic_symptoms` (grouped by type), `exclusion_factors`, `note` |
| C | `diagnosis` (string), `details`, `criteria_summary` (6 disorders), `module_b_symptoms`, optionally `psychotic_mood_disorder` + `note` |
| D | `diagnosis` (string), `details`, `criteria_summary` (4 mood disorders), `module_a_episodes`, optionally `no_significant_mood_symptoms` + `note` |
| E | `alcohol` (`diagnosed`, `symptoms_counted`, `severity`), `substances_screened` (`any_substance_used`, `substances_reported`), `substance_use_disorder` (`diagnosed`, `primary_substance`, `symptoms_counted`, `severity`) |

### Chronology Fields

| Module | Disorder | Chronology Question | Field |
|--------|----------|---------------------|-------|
| C | Schizophrenia | C26 | `details.current` |
| C | Schizophreniform | C27 | `details.current` |
| C | Schizoaffective | C28 | `details.current` |
| C | Delusional | C29 | `details.current` |
| C | Brief Psychotic | C30 | `details.current` |
| D | Bipolar I | D25 | `details.current` |
| D | Bipolar II | D26 | `details.current` |
| D | MDD | D27 | `details.current` |
| D | Other Depressive | D28 | `details.current` |

### Key Question ID Quick Reference

| Module | Gate / Entry | Criteria Questions | Exclusion | Chronology |
|--------|--------------|--------------------|-----------|------------|
| A | A1, A15, A29, A41, A54, A66, A78 | A2-A9, A17-A25, A30-A38, A42-A50, A55-A63, A67-A75, A79-A84 | A12, A27, A40, A53, A65, A77, A89 | A28, A53, A65, A77 |
| B | B1 (delusions), B12 (hallucinations) | B2-B11, B13-B17, B18-B22 | B23, B24 | — |
| C | C1 (psychosis outside mood) | C2-C6, C7-C8, C9-C12, C13-C17, C19-C21, C22-C25 | C6, C8, C12, C17, C24 | C26-C30 |
| D | D1 (mood symptoms gate) | D2, D8-D11, D17, D22 | D3-D4, D10, D12-D14, D18-D19, D23-D24 | D25-D28 |
| E | E1 (alcohol gate), E14 (substance gate) | E2-E12 (alcohol), E38-E48 (substance) | — | — |

---

## 🎨 Admin Panel & UI

### Custom Styling

The admin panel uses `static/admin/css/custom_admin.css` with a comprehensive CSS variable theming system supporting both light and dark modes.

**Key CSS variables:**
- `--sc-primary`, `--sc-primary-gradient`, `--sc-primary-dark` — Brand colors
- `--sc-bg-body`, `--sc-bg-card`, `--sc-bg-input` — Background layers
- `--sc-text-primary`, `--sc-text-secondary`, `--sc-text-white` — Text colors
- `--sc-border`, `--sc-shadow-sm/md/lg` — Borders & shadows
- `--sc-danger` — Delete/error color (#EF4444)

**Dark mode:** Toggled via Django's theme system (`data-theme="dark"` on `<html>`).

### Admin UI Improvements (July 2025)

The admin panel has been extensively customized:

1. **Tabular Inline Layout:**
   - ID column (A1, A2, etc.) shown with `display: table-cell !important` overriding Django's `.hidden` class
   - Question text column (`td.original`) uses `font-size: 0` trick to hide text nodes while keeping the "Change" link visible via `.inlinechangelink { font-size: 11px }`
   - Column widths compacted: `is_criteria` 35px, `has_jump_logic` 50px, `criteria_number` 45px, `order` 35px, `delete` 45px

2. **Form Fields:**
   - All inputs, textareas, and selects have `min-height: 42px` and `padding: 10px 14px`
   - File inputs styled with custom `::file-selector-button` using primary color
   - Select2 containers also sized to `min-height: 42px`

3. **Buttons:**
   - All `.button` / `input[type="submit"]` elements: `min-height: 42px`, `padding: 10px 20px`
   - Delete button (`.submit-row a.deletelink`): solid red (`background-image: none`), `min-height: 42px`

4. **Sidebar:**
   - All child elements forced transparent to prevent white background leaks
   - Dark/light mode properly coordinated via CSS variables

5. **Dark Mode:**
   - Full dark mode support with separate variable overrides
   - Django theme toggle integration (`data-theme="dark"`)

---

## 🗺️ Roadmap — Next Modules

### Current Status

| Module | Status | Questions | Jump Rules | Diagnosis |
|--------|--------|-----------|------------|-----------|
| A — Mood Episodes | ✅ Done | 90 | 16 | Depression, Mania, Hypomania |
| B — Psychotic Symptoms | ✅ Done | 24 | 5 | Symptom Profile |
| C — Differential Psychotic | ✅ Done | 30 | 5 | SZ, Schizophreniform, Schizoaffective, Delusional, Brief Psychotic |
| D — Differential Mood | ✅ Done | 28 | 9 | Bipolar I, Bipolar II, MDD, Other Depressive |
| E — Substance Use Disorders | ✅ Done | 35 | 12 | Alcohol Use Disorder, Substance Use Disorder (severity: Mild/Moderate/Severe) |
| F — Anxiety Disorders | ✅ Done | 40 | 11 | Panic Disorder, Agoraphobia, Social Anxiety, GAD |

### Next Modules to Implement

| Module | Name | Est. Questions | Priority | Dependencies |
|--------|------|----------------|----------|--------------|
| **G** | Obsessive-Compulsive & Related | ~20-25 | Medium | Module F (anxiety) |
| **H** | Trauma- & Stressor-Related | ~20-30 | Medium | Module A (mood), Module F (anxiety) |
| **I** | Somatic Symptom & Related | ~20-25 | Low | None |
| **J** | Feeding & Eating Disorders | ~20-25 | Low | None |
| **K** | Sleep-Wake Disorders | ~25-30 | Low | Module A (mood), Module E (substance) |
| **L** | Gender Dysphoria | ~10-15 | Low | None |
| **M** | Disruptive, Impulse-Control | ~15-20 | Low | None |

### Implementation Checklist (per module)

1. **Research & Data Entry**
   - [ ] Map SCID-5-CV section questions to JSON format
   - [ ] Identify gate questions, criteria groups, exclusion criteria
   - [ ] Define jump rules based on SCID-5 decision tree

2. **JSON File Creation**
   - [ ] Create `interview/data/module_X.json` following existing format
   - [ ] Include: module metadata, questions (with types/choices/criteria flags), jump rules

3. **Data Loading**
   - [ ] Add filename to `MODULE_FILES` in `load_interview_data.py`
   - [ ] Run `python manage.py load_interview_data`
   - [ ] Verify questions and jump rules loaded correctly

4. **Diagnosis Algorithm**
   - [ ] Add diagnosis branch in `_calculate_diagnosis()` in `views.py`
   - [ ] Use unique name pattern (check order against existing modules)
   - [ ] Implement criteria counting and diagnosis decision tree
   - [ ] Add cross-module data lookup if needed (e.g., Module E references Module A)

5. **Testing**
   - [ ] Write tests in `interview/tests.py` following `ModuleCInterviewTests` pattern
   - [ ] Test: interview start, progress, jump logic, completion, diagnosis output
   - [ ] Run full test suite: `python manage.py test accounts interview --verbosity=2`

6. **Documentation**
   - [ ] Add module section to this README
   - [ ] Document diagnosis logic, jump rules, output format
   - [ ] Update the Key Question ID Quick Reference table

### Cross-Module Dependencies

```
Module A (Mood) ──────┬──→ Module D (Differential Mood)
                      │
Module B (Psychotic) ─┼──→ Module C (Differential Psychotic)
                      │
                      ├──→ Module E (Substance) ✅
                      │
Module F (Anxiety) ───┼──→ Module G (OCD) [planned]
                      │
                      └──→ Module H (Trauma) [planned]
```

### Adding a New Condition Type

If the existing condition types don't cover your jump rule logic:

1. Add the type to `JumpRule.CONDITION_TYPES` in `interview/models.py`
2. Add the evaluation logic in `_evaluate_jump_condition()` in `views.py`
3. Document it in the [Condition Types](#condition-types) table above

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

# Load interview data (Modules A–D)
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

## 📝 Changelog

### July 2025

- **Module E** — Substance Use Disorders (35 questions, 12 jump rules, Alcohol/Substance Use Disorder diagnosis with DSM-5 severity classification)
- **Module D** — Differential Diagnosis of Mood Disorders (28 questions, 9 jump rules, Bipolar I/II/MDD diagnosis)
- **Module C** — Differential Diagnosis of Psychotic Disorders (30 questions, 5 jump rules, SZ/Schizophreniform/Schizoaffective/Delusional diagnosis)
- **Admin UI overhaul** — Tabular inline layout fixes, ID column visibility, form field sizing, dark mode, delete button styling
- **Swagger schemas** — Named schemas for interview views

### Earlier

- **Module B** — Psychotic and Associated Symptoms (24 questions, 5 jump rules, symptom profile)
- **Module A** — Mood Episodes (90 questions, 16 jump rules, Depression/Mania/Hypomania diagnosis)
- **Core platform** — JWT auth, OTP, patient management, overview, clinical notes

---

## 👨‍💻 Author

**Mohammad Hossein Esnavandi** — Project Lead & Clinical Architecture

---

## 🙏 Acknowledgments

- Based on the **Structured Clinical Interview for DSM-5® Disorders — Clinician Version (SCID-5-CV)** by the American Psychiatric Association.
- Built with Django and Django REST Framework.
