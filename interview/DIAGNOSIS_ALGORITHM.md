# SCID-5-CV Diagnosis Algorithm — Smart-SCID

> **Purpose:** This document describes the diagnosis algorithm implemented in
> `interview/api/v1/views.py` (`_calculate_diagnosis` method).
> It is the single source of truth for how each module produces its diagnosis result.
> When adding a new module, follow the patterns documented here.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Answer Value Format](#answer-value-format)
3. [Jump Rules System](#jump-rules-system)
4. [Module A — Mood Episodes](#module-a--mood-episodes)
5. [Module B — Psychotic and Associated Symptoms](#module-b--psychotic-and-associated-symptoms)
6. [Module C — Differential Diagnosis of Psychotic Disorders](#module-c--differential-diagnosis-of-psychotic-disorders)
7. [Module D — Differential Diagnosis of Mood Disorders](#module-d--differential-diagnosis-of-mood-disorders)
8. [Module E+ — Future Modules](#module-e--future-modules)
9. [Output Format Reference](#output-format-reference)

---

## Architecture Overview

```
InterviewProgressView.post()
  ├── Save / update Answer
  ├── _get_next_question()
  │     ├── Evaluate JumpRules for current question (first match wins)
  │     └── Fall-through: next question by order
  └── If no next question → mark completed → _calculate_diagnosis()
```

**Module detection** is done via module name pattern matching in `_calculate_diagnosis`:

```python
if 'Mood Episodes' in interview.module.name:                     # Module A
elif 'Differential Diagnosis of Psychotic' in interview.module.name:  # Module C
elif 'Mood Disorders' in interview.module.name:                  # Module D
elif 'Psychotic' in interview.module.name:                       # Module B
```

> ⚠️ Module C must be checked before Module B because both contain "Psychotic" in the name.
> Module D must be checked after Module C because Module D's name also contains "Differential Diagnosis".

---

## Answer Value Format

All answers are stored in a JSONField `value` with a type discriminator:

| question_type | value format | accessor property |
|---|---|---|
| `boolean` | `{"boolean": true}` | `answer.boolean_value` |
| `text` | `{"text": "..."}` | `answer.text_value` |
| `number` | `{"number": 5}` | `answer.number_value` |
| `multiple_choice` | `{"text": "choice_label"}` | `answer.text_value` |

---

## Jump Rules System

**Model:** `JumpRule` (see `interview/models.py`)

Each rule links a `from_question` → `to_question` (nullable; `null` = end interview).

**Evaluation order:** Rules for the current question are evaluated in database order.
The **first match wins**. If no rule matches, sequential next question by `order`.

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
  "expected_value": true,       // for boolean/multiple_choice
  "question_ids": ["B1"],       // for criteria_count / criteria_count_met
  "min_count": 1,               // threshold for count-based conditions
  "match_pattern": "text",      // for text conditions
  "min_value": 0,               // for range conditions
  "max_value": 100,             // for range conditions
  "note": "human-readable description"  // always include for documentation
}
```

---

## Module A — Mood Episodes

**File:** `interview/data/module_a.json`
**Questions:** A1–A90 (7 sections)
**Module name pattern:** `'Mood Episodes' in name`

### Sections

| Section | Questions | Purpose |
|---|---|---|
| Current MDE | A1–A14 | Major Depressive Episode — current month |
| Past MDE | A15–A28 | Major Depressive Episode — lifetime |
| Current Mania | A29–A40 | Manic Episode — current |
| Current Hypomania | A41–53 | Hypomanic Episode — current |
| Past Mania | A54–A65 | Manic Episode — lifetime |
| Past Hypomania | A66–A77 | Hypomanic Episode — lifetime |
| Persistent Depressive | A78–A90 | Dysthymia / PDD (2+ years) |

### Diagnosis Logic

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

### Output

```json
{
  "module": "Module A - Mood Episodes",
  "depression": {
    "diagnosed": true,
    "symptoms_counted": 6,
    "required_symptoms_count": 5,
    "criteria_met": ["A1", "A2", "A4", "A6", "A7", "A8"]
  },
  "mania": { "diagnosed": false, ... },
  "hypomania": { "diagnosed": false, ... }
}
```

---

## Module B — Psychotic and Associated Symptoms

**File:** `interview/data/module_b.json`
**Questions:** B1–B24
**Module name pattern:** `'Psychotic' in name` (but NOT `'Differential Diagnosis'`)

### Question Groups

| Group | Questions | DSM-5 Category |
|---|---|---|
| Delusions | B1–B11 | Criterion A.1 |
| Hallucinations | B12–B17 | Criterion A.2 |
| Disorganized speech | B18 | Criterion A.3 |
| Disorganized behavior | B19 | Criterion A.4 |
| Catatonic behavior | B20 | Criterion A.4 |
| Negative symptoms | B21–B22 | Criterion A.5 |
| Exclusion: medical | B23 | Criterion E |
| Exclusion: substance | B24 | Criterion E |

### Diagnosis Logic

Module B produces a **symptom profile**, NOT a specific diagnosis.
The note in the output explicitly states that Module C is required for differential diagnosis.

```python
delusion_ids = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11']
hallucination_ids = ['B12', 'B13', 'B14', 'B15', 'B16', 'B17']
disorganized_ids = ['B18', 'B19']
catatonic_ids = ['B20']
negative_ids = ['B21', 'B22']
```

### Output

```json
{
  "module": "Module B - Psychotic and Associated Symptoms",
  "psychotic_symptoms": {
    "delusions":          { "present": true, "count": 3, "items": ["B1","B2","B9"] },
    "hallucinations":     { "present": true, "count": 1, "items": ["B12"] },
    "disorganized_speech_or_behavior": { "present": false, "items": [] },
    "catatonic_behavior": { "present": false, "items": [] },
    "negative_symptoms":  { "present": false, "items": [] }
  },
  "exclusion_factors": {
    "due_to_medical_condition": false,
    "due_to_substance": false
  },
  "note": "This is a symptom profile. Diagnosis (Schizophrenia, Schizoaffective, etc.) requires Module C."
}
```

---

## Module C — Differential Diagnosis of Psychotic Disorders

**File:** `interview/data/module_c.json`
**Questions:** C1–C30
**Module name pattern:** `'Differential Diagnosis' in name`

### Prerequisite

Module C requires a **completed Module B interview** for the same patient.
The diagnosis logic pulls Module B answers to include in the result as `module_b_symptoms`.

### Question Mapping

| Questions | Disorder | Criteria |
|---|---|---|
| C1 | Gate question | Psychosis outside mood episodes? |
| C2–C6 | Schizophrenia | All 5 DSM-5 criteria (A through E) |
| C7–C8 | Schizophreniform | Same as SZ but duration 1–6 months |
| C9–C12 | Schizoaffective | Mood episode + psychosis overlap |
| C13–C18 | Delusional Disorder | Delusions ≥1 month without SZ criteria |
| C18 | (text) | Delusion type specifier |
| C19–C21 | Brief Psychotic Disorder | 1 day – 1 month, full recovery |
| C22–C25 | Other Specified | Doesn't meet any specific criteria |
| C26 | Chronology: Schizophrenia | Current vs remission |
| C27 | Chronology: Schizophreniform | Current vs remission |
| C28 | Chronology: Schizoaffective | Current vs remission |
| C29 | Chronology: Delusional | Current vs remission |
| C30 | Chronology: Brief Psychotic | Current vs remission |

### Diagnosis Decision Tree

```
C1: Psychotic symptoms outside mood episodes?
  │
  ├── NO → Psychotic Mood Disorder → proceed to Module D
  │        Output: { psychotic_mood_disorder: true, note: "..." }
  │
  └── YES → evaluate C2–C25
            │
            ├─ C2-C6: Schizophrenia criteria
            │   All 5 positive? ──YES──→ Schizophrenia + C26
            │
            ├─ C7-C8: Schizophreniform
            │   Both positive? ──YES──→ Schizophreniform + C27
            │
            ├─ C9-C12: Schizoaffective
            │   All 4 positive? ──YES──→ Schizoaffective + C28
            │
            ├─ C13-C17: Delusional Disorder
            │   All 5 positive? ──YES──→ Delusional + C18(type) + C29
            │
            ├─ C19-C21: Brief Psychotic
            │   All 3 positive? ──YES──→ Brief Psychotic + C30
            │
            ├─ C22-C25: Other Specified
            │   All 4 positive? ──YES──→ Other Specified
            │
            └─ None met → Undifferentiated
```

> **Priority:** The first matching disorder wins (Schizophrenia > Schizophreniform > ... > Other Specified).

### Diagnosis Logic (code)

```python
# All criteria are evaluated independently
schizophrenia    = all(C2, C3, C4, C5, C6)       # 5/5
schizophreniform = all(C7, C8)                     # 2/2
schizoaffective  = all(C9, C10, C11, C12)         # 4/4
delusional       = all(C13, C14, C15, C16, C17)   # 5/5
brief_psychotic  = all(C19, C20, C21)             # 3/3
other_specified  = all(C22, C23, C24, C25)        # 4/4

# First match wins:
if schizophrenia:    → "Schizophrenia"
elif schizophreniform: → "Schizophreniform Disorder"
elif schizoaffective:  → "Schizoaffective Disorder"
elif delusional:       → "Delusional Disorder" + type from C18
elif brief_psychotic:  → "Brief Psychotic Disorder"
elif other_specified:  → "Other Specified Psychotic Disorder"
else:                  → "Undifferentiated"
```

### Jump Rules (Module C)

| From | Condition | To | Meaning |
|---|---|---|---|
| C1 | `answer == false` | END | Only mood psychosis → end, go to Module D |
| C2 | `criteria_count < 2` of C2-C6 | C13 | SZ criterion A not met → skip to Delusional |
| C6 | `criteria_count_met >= 4` of C2-C6 | C9 | Full SZ criteria met → skip to Schizoaffective |
| C8 | `answer == false` | C9 | Schizophreniform not met → Schizoaffective |
| C12 | `answer == false` | C13 | Schizoaffective not met → Delusional |

### Module B Symptom Lookup

Module C's diagnosis pulls the most recent completed Module B answers for the same patient:

```python
module_b = InterviewModule.objects.get(name__icontains='Psychotic and Associated')
b_answers = Answer.objects.filter(
    interview__patient=interview.patient,
    interview__module=module_b,
    interview__status='completed'
).order_by('-interview__completed_at')
```

### Output

```json
{
  "module": "Module C - Differential Diagnosis of Psychotic Disorders",
  "diagnosis": "Schizophrenia",
  "details": {
    "criteria_met": ["C2", "C3", "C4", "C5", "C6"],
    "current": true
  },
  "criteria_summary": {
    "schizophrenia":      { "met": true,  "criteria_positive": ["C2","C3","C4","C5","C6"] },
    "schizophreniform":   { "met": false, "criteria_positive": [] },
    "schizoaffective":    { "met": false, "criteria_positive": [] },
    "delusional_disorder":{ "met": false, "criteria_positive": [] },
    "brief_psychotic":    { "met": false, "criteria_positive": [] },
    "other_specified":    { "met": false, "criteria_positive": [] }
  },
  "module_b_symptoms": {
    "delusions_present": ["B1", "B2"],
    "hallucinations_present": ["B12"]
  }
}
```

---

## Module D — Differential Diagnosis of Mood Disorders

**SCID-5-CV Section**: pages 45-52
**Module name in DB**: `Module D - Differential Diagnosis of Mood Disorders`
**Questions**: D1-D28
**Gate question**: D1 (clinically significant mood symptoms not better explained by Schizoaffective Disorder)

### Decision Tree

```
D1 — Clinically significant mood symptoms not accounted for by Schizoaffective Disorder?
  ├── NO → no_significant_mood_symptoms → END
  └── YES ↓
D2 — Manic episode criteria met? [references Module A: A40/A65]
  ├── YES → Bipolar I track (D3-D7, D25)
  │   D3 — Not better explained by psychotic disorders?
  │   D4 — Not substance/medical?
  │     ├── ALL YES → Bipolar I Disorder confirmed
  │     │   D5 — Current episode active?
  │     │     ├── YES → D6 (episode type) → D7 (severity) → D25 (chronology)
  │     │     └── NO → D25 (chronology)
  │     └── ANY NO → Not Bipolar I → fall through to D8
  └── NO → Bipolar II / MDD track (D8-D28)
      D8 — At least one MDE?
        ├── NO → D22 (Other Depressive)
        └── YES ↓
      D9 — At least one hypomanic episode? [references Module A: A50/A76]
        ├── NO → MDD track (D17-D21, D27)
        └── YES ↓
      D10 — Never had a full manic episode?
      D11 — Hypomanic episode >= 4 consecutive days?
        ├── NO → MDD track (D17-D21, D27)
        └── YES ↓
      D12 — Clinically significant distress/impairment?
      D13 — Not substance/medical?
      D14 — Not better explained by psychotic disorders?
        ├── ALL YES → Bipolar II Disorder confirmed
        │   D15 — Current depressive episode?
        │     ├── YES → D16 (severity) → D26 (chronology)
        │     └── NO → D26 (chronology) [current hypomanic or unspecified]
        └── ANY NO → Not Bipolar II → MDD track (D17-D21, D27)
      D17 — At least 2 weeks of depressed mood or loss of interest?
      D18 — Clinically significant distress/impairment?
      D19 — Not substance/medical?
        ├── ALL YES → MDD confirmed
        │   D20 — Single episode or recurrent?
        │   D21 (severity) → D27 (chronology)
        └── ANY NO → D22 (Other Depressive)
      D22 — Depressive symptoms but don't meet full MDD/Persistent/PMDD?
      D23 — Clinically significant distress?
      D24 — Not substance/medical?
        ├── ALL YES → Other Specified Depressive Disorder → D28 (chronology)
        └── ANY NO → Undifferentiated mood disorder
```

### Diagnosis Priority

```
if bipolar_i (D2 + D3 + D4):
    → "اختلال دوقطبی نوع ۱" (Bipolar I Disorder)
    → includes: episode type from D6, severity from D7, chronology from D25
elif bipolar_ii (D8 + D9 + D10 + D11 + D12 + D13 + D14):
    → "اختلال دوقطبی نوع ۲" (Bipolar II Disorder)
    → includes: episode type from D15, severity from D16, chronology from D26
elif mdd (D17 + D18 + D19):
    → "اختلال افسردگی اساسی" (Major Depressive Disorder)
    → includes: single/recurrent from D20, severity from D21, chronology from D27
elif other_depressive (D22 + D23 + D24):
    → "سایر اختلالات افسردگی مشخص‌شده" (Other Specified Depressive Disorder)
    → includes: chronology from D28
else:
    → "اختلال خلقی نامشخص" (Unspecified Mood Disorder)
```

### Module A Episode Lookup

Module D references Module A data for cross-validation:
- Bipolar I: checks Module A manic criteria (A40/A65)
- Bipolar II: checks Module A hypomanic criteria (A50/A76)

When Module A has been completed for the same patient, the diagnosis output includes a `module_a_episodes` field summarizing:
- `depression_symptoms`: list of positive A1-A9
- `mania_symptoms`: list of positive A29-A38
- `hypomania_symptoms`: list of positive A41-A50

### Jump Rules (Module D)

| From | Condition | To | Meaning |
|---|---|---|---|
| D1 | `answer == false` | END | No significant mood symptoms → end module |
| D2 | `answer == false` | D8 | No manic episode → skip Bipolar I, assess BP-II/MDD |
| D5 | `answer == false` | D25 | BP-I confirmed, no current episode → chronology |
| D7 | `text, match=""` | D25 | BP-I severity entered (any text) → chronology |
| D9 | `answer == false` | D17 | No hypomanic episode → skip BP-II, assess MDD |
| D11 | `answer == false` | D17 | Hypomanic < 4 days → not BP-II, assess MDD |
| D15 | `answer == false` | D26 | BP-II confirmed, no current depressive → chronology |
| D16 | `text, match=""` | D26 | BP-II severity entered (any text) → chronology |
| D21 | `text, match=""` | D27 | MDD severity entered (any text) → chronology |

### Severity Questions (Text Type)

D7, D16, D21 are `text` type severity questions with `match_pattern=""`. Since empty string always matches any text input (`"" in "anytext"` = True), these jump rules act as unconditional "next" buttons — whatever the clinician types for severity, the jump triggers.

---

## Module E+ — Future Modules

When adding Module E (Substance Use), Module F, etc.:

1. **Create JSON file** in `interview/data/` following the format in existing modules
2. **Add filename** to `MODULE_FILES` in `load_interview_data.py`
3. **Add diagnosis branch** in `_calculate_diagnosis()`:
   - Use a unique name pattern that doesn't overlap with existing modules
   - Check order: more specific patterns first
4. **Add tests** in `interview/tests.py` following `ModuleCInterviewTests` pattern
5. **Update this document**

### Adding a New Condition Type

If the existing condition types don't cover your jump rule logic:

1. Add the type to `JumpRule.CONDITION_TYPES` in `interview/models.py`
2. Add the evaluation logic in `_evaluate_jump_condition()` in `views.py`
3. Document it in the [Condition Types](#condition-types) table above

---

## Output Format Reference

All diagnosis results share this top-level structure:

```python
{
    'module': str,           # module name
    # ... module-specific fields
}
```

### Module-Specific Fields

| Module | Key Fields |
|---|---|
| A | `depression`, `mania`, `hypomania` (each: `diagnosed`, `symptoms_counted`, `required_symptoms_count`, `criteria_met`) |
| B | `psychotic_symptoms` (grouped by type), `exclusion_factors`, `note` |
| C | `diagnosis` (string), `details`, `criteria_summary` (6 disorders), `module_b_symptoms`, optionally `psychotic_mood_disorder` + `note` |
| D | `diagnosis` (string), `details`, `criteria_summary` (4 mood disorders), `module_a_episodes`, optionally `no_significant_mood_symptoms` + `note` |

### Chronology Fields (Module C)

When a specific disorder is diagnosed, the corresponding chronology question is included:

| Disorder | Chronology Question | Field |
|---|---|---|
| Schizophrenia | C26 | `details.current` |
| Schizophreniform | C27 | `details.current` |
| Schizoaffective | C28 | `details.current` |
| Delusional | C29 | `details.current` |
| Brief Psychotic | C30 | `details.current` |

### Chronology Fields (Module D)

| Disorder | Chronology Question | Field |
|---|---|---|
| Bipolar I | D25 | `details.current` |
| Bipolar II | D26 | `details.current` |
| MDD | D27 | `details.current` |
| Other Depressive | D28 | `details.current` |

### Delusion Type Specifier (C18)

For Delusional Disorder, C18 is a `text` question storing the type:
`Persecutory` / `Grandiose` / `Jealous` / `Erotomanic` / `Somatic` / `Mixed` / `Unspecified`

Stored in `details.type`.

---

## Key Question ID Quick Reference

| Module | Gate / Entry | Criteria Questions | Exclusion | Chronology |
|---|---|---|---|---|
| A | A1, A15, A29, A41, A54, A66, A78 | A2-A9, A17-A25, A30-A38, A42-A50, A55-A63, A67-A75, A79-A84 | A12, A27, A40, A53, A65, A77, A89 | A28, A53, A65, A77 |
| B | B1 (delusions), B12 (hallucinations) | B2-B11, B13-B17, B18-B22 | B23, B24 | — |
| C | C1 (psychosis outside mood) | C2-C6, C7-C8, C9-C12, C13-C17, C19-C21, C22-C25 | C6, C8, C12, C17, C24 | C26-C30 |
| D | D1 (mood symptoms gate) | D2, D8-D11, D17, D22 | D3-D4, D10, D12-D14, D18-D19, D23-D24 | D25-D28 |
