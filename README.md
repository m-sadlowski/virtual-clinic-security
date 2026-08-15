# Virtual Clinic Security

Security-focused virtual clinic web application built with Python, Flask and SQLite.

The project was developed as a two-person university project focused on authentication, authorization, session security and protection against common web application vulnerabilities.

## Features

### Authentication & Sessions

* User registration and login
* Password hashing with PBKDF2-HMAC-SHA256 and individual salts
* Server-side session management
* Session expiration and logout
* Protection against brute-force login attempts

### Authorization

* Role-based access control for patients, doctors and staff
* Route protection using custom authorization decorators
* Restricted access to patient data
* Access control for medical notes and assigned patients

### Security

* CSRF protection for state-changing requests
* Parameterized SQL queries
* Secure session cookies
* Environment-based application secret
* Protection against excessive access to patient data

## Tech Stack

* Python
* Flask
* SQLite
* HTML / Jinja templates

## Running the Application

### 1. Clone the repository

```bash
git clone https://github.com/m-sadlowski/virtual-clinic-security.git
cd virtual-clinic-security
```

### 2. Create and activate a virtual environment

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set the application secret

Windows PowerShell:

```powershell
$env:SECRET_KEY="your-secret-key"
```

Linux / macOS:

```bash
export SECRET_KEY="your-secret-key"
```

### 5. Run the application

```bash
python run.py
```

The application will be available at the address displayed in the terminal.
