

```markdown
# 🧠 Smart SCID

**توسعه نرم افزاری مصاحبه (Software Development of the Interview)**

> A comprehensive web-based platform for conducting SCID-5-CV interviews, managing patients, and generating clinical diagnoses.

---

## 📖 Overview

Smart SCID is a Django-based web application designed to digitize the Structured Clinical Interview for DSM-5 Disorders (SCID-5-CV). It provides a modern, secure, and user-friendly interface for clinicians to conduct standardized diagnostic interviews, manage patient records, and track interview progress efficiently.

### 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **🔐 Authentication** | Secure JWT-based authentication with OTP verification via SMS. |
| **👤 User Management** | Role-based access control (Admin, Clinician, Researcher). |
| **👥 Patient Management** | Complete CRUD operations with auto-generated unique, anonymized codes. |
| **📋 SCID-5-CV Overview** | Persian-translated interview questions with structured data storage. |
| **📝 Clinical Notes** | Add notes and clinical observations dynamically during interviews. |
| **📊 Progress Tracking** | Monitor interview completion and status per diagnostic module. |
| **📚 OpenAPI Documentation** | Full Swagger/ReDoc documentation with Persian descriptions. |
| **🖥️ Admin Panel** | Customized Django admin with professional, role-based styling. |
| **🧪 Testing** | Comprehensive test suite with 40+ passing tests ensuring reliability. |

---

## 🔬 Research & Validation Methodology

This software is being developed and validated as a rigorous academic and clinical tool. To ensure the diagnostic accuracy, reliability, and clinical utility of the platform compared to the traditional paper-and-pencil method, the system is being evaluated using a **hybrid sample of 100 cases**. This robust validation process ensures the software meets high clinical standards for real-world psychiatric and psychological assessment.

---

## 🏗️ Architecture

```text
smart_scid/
├── accounts/              # User authentication, patients, overview, and notes
│   ├── models.py          # User, UserProfile, Patient, Overview, PatientNote
│   ├── api/v1/            # REST API endpoints & serializers
│   └── admin.py           # Custom admin interface
├── interviews/            # Core interview modules & skip logic (coming soon)
├── diagnosis/             # Diagnostic algorithms & scoring (coming soon)
├── core/                  # Project configuration & main settings
└── utils/                 # Shared utilities (SMS integration, validators, etc.)

```

---

## 🚀 Tech Stack

### Backend

| Technology | Purpose |
| --- | --- |
| **Django 4.2** | Core web framework |
| **Django REST Framework** | REST API architecture |
| **Simple JWT** | Stateless token-based authentication |
| **drf-spectacular** | OpenAPI/Swagger schema generation |
| **SQLite / PostgreSQL** | Database management |

### Authentication & Security

* JWT tokens for secure, stateless API communication.
* OTP verification via SMS (includes a mock mode for local development).
* Phone number utilized as the primary, regex-validated identifier.

### Documentation

* **Swagger UI**: Available at `/api/schema/swagger-ui/`
* **ReDoc**: Available at `/api/schema/redoc/`
* Full Persian translations integrated for clinical content and API descriptions.

---

## 📦 Installation

### Prerequisites

* Python 3.10+
* pip
* virtualenv (recommended)

### Steps

1. **Clone the repository**

```bash
git clone [https://github.com/yourusername/smart-scid.git](https://github.com/yourusername/smart-scid.git)
cd smart-scid

```

2. **Create and activate virtual environment**

```bash
python -m venv venv
# On Linux/macOS:
source venv/bin/activate  
# On Windows:
venv\Scripts\activate

```

3. **Install dependencies**

```bash
pip install -r requirements.txt

```

4. **Configure environment variables**

```bash
cp .env.example .env
# Edit .env with your specific local configuration

```

5. **Run migrations**

```bash
python manage.py makemigrations
python manage.py migrate

```

6. **Create superuser**

```bash
python manage.py createsuperuser

```

7. **Run development server**

```bash
python manage.py runserver

```

8. **Access the application**

* API Base: `http://127.0.0.1:8000/api/`
* Admin Panel: `http://127.0.0.1:8000/admin/`
* Swagger UI: `http://127.0.0.1:8000/api/schema/swagger-ui/`

---

## 🔧 Configuration (.env)

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL example)
DB_NAME=smart_scid_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# SMS Configuration
SMS_IR_API_KEY=your-sms-api-key
SMS_IR_VERIFY_TEMPLATE_ID=100000
SMS_MOCK_MODE=True  # Set to False for production
OTP_CACHE_TIMEOUT=120
OTP_LENGTH=5

```

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/accounts/auth/send-otp/` | Send OTP to phone |
| `POST` | `/api/accounts/auth/verify-otp/` | Verify OTP and authenticate |
| `POST` | `/api/accounts/register/` | Register new user |
| `POST` | `/api/accounts/token/` | Login with phone & password |
| `POST` | `/api/accounts/token/refresh/` | Refresh JWT token |

### User Profile & Patients

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET/PUT` | `/api/accounts/profile/` | Manage user profile |
| `GET/POST` | `/api/accounts/patients/` | List or create patients |
| `GET/PUT/DEL` | `/api/accounts/patients/{id}/` | Manage specific patient |
| `GET/POST` | `/api/accounts/patients/{id}/notes/` | Manage patient notes |

### Overview (SCID-5-CV)

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET/POST` | `/api/accounts/patients/{id}/overviews/` | List or create clinical overviews |
| `GET/PUT` | `/api/accounts/overviews/{id}/` | Manage specific overview data |

---

## 🧪 Testing

The project uses Django's built-in testing framework to ensure data integrity and API reliability.

**Run all tests:**

```bash
python manage.py test accounts --verbosity=2

```

**Test Coverage Includes:**

* ✅ Model validations and constraints
* ✅ API endpoint responses and status codes
* ✅ Authentication and OTP logic
* ✅ Signal triggers (e.g., auto-profile creation)

---

## 🗄️ Database Schema Highlights

* **User & Profile**: Separated `User` (auth) and `UserProfile` (clinical metadata) with strict regex validation for phone numbers and Iranian National Codes.
* **Patient**: Stores demographic and contact data securely with an auto-generated, untraceable `patient_code` to maintain confidentiality.
* **Overview**: A comprehensive model mapping directly to the SCID-5-CV introductory section (Demographics, Treatment History, Suicidal Ideation, etc.).
* **PatientNote**: Allows clinicians to categorize and store real-time interview observations.

---

## 📝 Development Status

### ✅ Phase 1: Completed

* User authentication infrastructure (JWT, OTP)
* Secure Patient Management (CRUD)
* Digital mapping of the SCID-5-CV Overview section
* Clinical notes system
* Customized Admin Panel
* OpenAPI documentation

### 🚧 Phase 2: In Progress

* Implementation of Clinical Modules (e.g., Mood Episodes)
* Algorithm-driven Skip Logic (Jump routing)
* Dynamic UI for module-based question flow

### 📋 Phase 3: Planned

* Automated diagnostic scoring and summary generation
* Psychometric data aggregation
* PDF clinical report generation

---

## 👨‍💻 Author

**Mohammad Hossein Esnavandi** *Project Lead & Clinical Architecture*

---

## 🙏 Acknowledgments

* Based on the Structured Clinical Interview for DSM-5® Disorders (SCID-5-CV) by the American Psychiatric Association.
* Built with Django and Django REST Framework.

---

**Made with ❤️ for the clinical psychology and psychiatric community.**

```

```
