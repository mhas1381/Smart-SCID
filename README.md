## 📄 README.md (نسخه انگلیسی کامل)

```markdown
# 🧠 Smart SCID

**Structured Clinical Interview for DSM-5 Disorders — Digital Version**

> A comprehensive web-based platform for conducting SCID-5-CV interviews, managing patients, and generating clinical diagnoses.

---

## 📖 Overview

Smart SCID is a Django-based web application designed to digitize the Structured Clinical Interview for DSM-5 Disorders (SCID-5-CV). It provides a modern, user-friendly interface for clinicians to conduct standardized diagnostic interviews, manage patient records, and track interview progress.

### 🎯 Key Features

| Feature | Description |
|---------|-------------|
| **🔐 Authentication** | Secure JWT-based authentication with OTP verification via SMS |
| **👤 User Management** | Role-based access control (Admin, Clinician, Researcher) |
| **👥 Patient Management** | Complete CRUD operations with auto-generated unique codes |
| **📋 SCID-5-CV Overview** | Persian-translated interview questions with structured data storage |
| **📝 Clinical Notes** | Add notes and observations during interviews |
| **📊 Progress Tracking** | Monitor interview completion per module |
| **📚 OpenAPI Documentation** | Full Swagger/ReDoc documentation with Persian examples |
| **🖥️ Admin Panel** | Customized Django admin with professional styling |
| **🧪 Testing** | Comprehensive test suite with 40+ passing tests |

---

## 🏗️ Architecture

```
smart_scid/
├── accounts/              # User authentication, patients, overview
│   ├── models.py          # User, UserProfile, Patient, Overview, PatientNote
│   ├── api/v1/            # REST API endpoints
│   └── admin.py           # Custom admin interface
├── interviews/            # Core interview modules (coming soon)
├── diagnosis/             # Diagnostic algorithms (coming soon)
├── core/                  # Project configuration
└── utils/                 # Shared utilities (SMS, etc.)
```

---

## 🚀 Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **Django 4.2** | Web framework |
| **Django REST Framework** | REST API development |
| **Simple JWT** | JWT authentication |
| **drf-spectacular** | OpenAPI/Swagger documentation |
| **SQLite** | Development database (PostgreSQL ready) |

### Authentication
- JWT tokens for stateless authentication
- OTP verification via SMS (mock mode for development)
- Phone number as primary identifier

### Documentation
- Swagger UI at `/api/schema/swagger-ui/`
- ReDoc at `/api/schema/redoc/`
- Full Persian translations for clinical content

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- pip
- virtualenv (recommended)

### Steps

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/smart-scid.git
cd smart-scid
```

2. **Create and activate virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
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
- API: `http://127.0.0.1:8000/api/`
- Admin: `http://127.0.0.1:8000/admin/`
- Swagger: `http://127.0.0.1:8000/api/schema/swagger-ui/`

---

## 🔧 Configuration

### Environment Variables (.env)

```env
# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=smart_scid_db
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# SMS Configuration
SMS_IR_API_KEY=your-sms-api-key
SMS_IR_VERIFY_TEMPLATE_ID=100000
SMS_MOCK_MODE=True  # Set False for production
OTP_CACHE_TIMEOUT=120
OTP_LENGTH=5
```

---

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/accounts/register/` | Register new user |
| `POST` | `/api/accounts/token/` | Login with phone & password |
| `POST` | `/api/accounts/token/refresh/` | Refresh JWT token |
| `POST` | `/api/accounts/auth/send-otp/` | Send OTP to phone |
| `POST` | `/api/accounts/auth/verify-otp/` | Verify OTP and authenticate |
| `POST` | `/api/accounts/auth/set-password/` | Set password for new user |

### User Profile

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/accounts/me/` | Get current user info |
| `GET/POST/PUT/PATCH` | `/api/accounts/profile/` | Manage user profile |

### Patients

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/accounts/patients/` | List or create patients |
| `GET/PUT/PATCH/DELETE` | `/api/accounts/patients/{id}/` | Manage specific patient |
| `GET/POST` | `/api/accounts/patients/{id}/notes/` | Manage patient notes |

### Overview (SCID-5-CV)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/accounts/overview-questions/` | Get all questions in Persian |
| `GET/POST` | `/api/accounts/patients/{id}/overviews/` | List or create overviews |
| `GET/PUT/PATCH` | `/api/accounts/overviews/{id}/` | Manage specific overview |

---

## 🧪 Testing

### Run all tests
```bash
python manage.py test accounts --verbosity=2
```

### Run specific test class
```bash
python manage.py test accounts.tests.UserModelTest
```

### Test coverage
- ✅ 40+ tests passing
- ✅ Model tests
- ✅ API tests
- ✅ Authentication tests
- ✅ Integration tests

---

## 📁 Project Structure

```
smart_scid/
├── accounts/
│   ├── api/
│   │   └── v1/
│   │       ├── openapi/
│   │       │   └── schema.py      # Swagger schemas
│   │       ├── serializers.py     # API serializers
│   │       ├── urls.py            # API routes
│   │       └── views.py           # API views
│   ├── migrations/
│   ├── admin.py                   # Admin panel
│   ├── apps.py
│   ├── models.py                  # Data models
│   ├── signals.py                 # Signals
│   ├── tests.py                   # Test suite
│   └── urls.py
├── core/
│   ├── settings.py                # Project settings
│   └── urls.py                    # Root URLs
├── utils/
│   ├── sms.py                     # SMS utilities
│   └── __init__.py
├── static/                        # Static files
├── templates/                     # Templates
├── manage.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## 🗄️ Database Schema

### Core Models

#### User
- `phone_number` (primary identifier)
- `email`, `first_name`, `last_name`
- `is_staff`, `is_active`, `is_superuser`

#### UserProfile
- `user` (OneToOne)
- `role` (admin, clinician, researcher)
- `birth_date`, `gender`
- `license_number`, `specialization`, `organization`

#### Patient
- `patient_code` (auto-generated)
- `first_name`, `last_name`
- `phone_number`, `email`, `birth_date`
- `gender`, `marital_status`, `education`, `occupation`
- `address`, `emergency_contact`
- `created_by` (clinician)

#### Overview (SCID-5-CV)
- `patient` (FK)
- `clinician` (FK)
- Demographic: `living_with`, `living_place`, `employment_status`
- History: `presenting_problem`, `onset_circumstances`
- Treatment: `first_treatment_age`, `psychiatric_hospitalization`
- Medical: `physical_health`, `current_medications`
- Suicidal: `wished_dead`, `suicide_attempt`, `self_harm`
- Other: `mood_description`, `alcohol_use`, `drug_use`

#### PatientNote
- `patient` (FK)
- `clinician` (FK)
- `content`, `note_type`

---

## 🎨 Admin Panel

The admin panel includes:
- Custom CSS styling with modern design
- Role-based display
- Patient list with quick actions
- Overview management with section grouping
- Note management with preview

Access at: `http://127.0.0.1:8000/admin/`

---

## 📝 Development Status

### ✅ Completed
- ✅ User authentication with JWT and OTP
- ✅ Patient management (CRUD)
- ✅ SCID-5-CV Overview section
- ✅ Patient notes
- ✅ Full admin panel
- ✅ API documentation with Swagger
- ✅ Comprehensive test suite
- ✅ Persian translations for clinical content

### 🚧 In Progress
- ⏳ Interview modules (A-J)
- ⏳ Jump logic for branching questions
- ⏳ Diagnostic calculation

### 📋 Planned
- 📋 Interview session management
- 📋 Module-based question flow
- 📋 Automatic diagnosis generation
- 📋 PDF report generation
- 📋 Multi-language support
- 📋 Mobile responsive frontend

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Convention

```
feat: new feature
fix: bug fix
docs: documentation
style: code style
refactor: code refactor
test: testing
chore: maintenance
```

---

## 📄 License

This project is licensed under the MIT License.

---

## 👨‍💻 Authors

- **Mohammad Hossein Esnavandi** - *Initial work*

---

## 🙏 Acknowledgments

- American Psychiatric Association for DSM-5 and SCID-5-CV
- Django and DRF communities
- All contributors and testers

---

## 📞 Contact

For questions or support, please contact:
- Email: your-email@example.com
- GitHub: [yourusername](https://github.com/yourusername)

---

## 📸 Screenshots

*(Coming soon)*

---

### 🧠 Smart SCID — Making mental health diagnosis smarter, faster, and more accurate.

---

**Made with ❤️ for the mental health community**
```

