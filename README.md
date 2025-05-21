# ETP Lab Portal

## Overview

The ETP (Exception to Policy) Lab Portal is a web application designed to manage and track hardware and software inventory within a laboratory environment, with a focus on handling exceptions to policy. It provides tools for administrators and lab users to efficiently manage lab resources, track their status, and ensure compliance.

## Features

* **User Roles and Permissions:**
    * Admin: Full access to manage users, labs, and data.
    * Superuser: Extended permissions, typically limited to a specific lab.
    * User: Regular lab user with access to lab-specific data.
    * Guest: Limited, read-only, or temporary access.
* **Lab Management:**
    * View a list of all labs and their associated computers.
    * Track the status of computers requiring an ETP (Exception to Policy).
* **ETP Status Tracking:**
    * Visual representation of ETP status for devices (e.g., pending, submitted, needs info, completed).
* **Data Import/Export:**
    * Import and export data (CSV) for all labs (admin) or specific labs (lab users).
* **User Management (Admin):**
    * Add, edit, and deactivate users.
    * Assign roles and lab affiliations.
* **Lab-Specific Dashboards:**
    * Lab users can view and manage data specific to their assigned labs.
* **Authentication and Authorization:**
    * Secure, session-based authentication.
    * Role-based access control to restrict access to specific features.
* **Enhanced Field Code Legend:**
    * Standardized prefixes for Computer Name and Owner fields to provide better data management.

## Technical Details

* **Backend:** Python, Flask
* **Database:** SQLAlchemy (supports various databases, default is SQLite)
* **Templates:** Jinja2
* **Frontend**: HTML, CSS, Bootstrap
* **Containerization:** Docker

## Setup Instructions

### Prerequisites

* Python 3.x
* Docker (if you want to use the Docker setup)
* Git (if you want to clone the repository)

### Installation

1.  **Clone the repository (optional):**

    ```bash
    git clone [https://github.com/your-username/etp-labportal.git](https://github.com/your-username/etp-labportal.git)
    cd etp-labportal
    ```

2.  **Set up a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

4.  **Database setup:**
    * The application uses Flask-SQLAlchemy for database interactions. By default, it is configured to use a SQLite database.
    * To initialize the database:
    ```bash
    python setup_db.py
    ```

5.  **Configuration:**
    * The application uses a configuration file (`config.py`) to manage settings.  You can set environment variables or modify the  `config.py`  file directly.
    * Important variables:
        * `SECRET_KEY`:  Used for session management.  **Change this to a strong, random value in production!**
        * `DATABASE_URL`: The database connection string.

### Docker Setup (Alternative)

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/etp-labportal.git](https://github.com/your-username/etp-labportal.git)
    cd etp-labportal
    ```

2.  **Build and run the Docker containers:**

    ```bash
    docker-compose build
    docker-compose up
    ```

3.  **Access the application:**
    The application will be running at `http://localhost:5000`.

### Running the Application

If you set up the project without Docker:

```bash
flask run
```
The application will be accessible at http://localhost:5000.

Initial LoginThe application is configured with a default admin user for initial setup and development.

Username: admin

Password: admin_password

Important: You should change this password immediately, especially in a production environment.File Structureetp-

labportal/
├── app/
│   ├── __init__.py
│   ├── admin_routes.py
│   ├── auth_access_control.py
│   ├── auth_routes.py
│   ├── extensions.py
│   ├── lab_routes.py
│   ├── main_routes.py
│   ├── models.py
│   ├── templates/
│   │   ├── admin/
│   │   │   ├── manage_users.html
│   │   │   ├── add_user.html
│   │   │   ├── edit_user.html
│   │   │   └── etp_requests_dashboard.html
│   │   ├── lab/
│   │   │   ├── lab_dashboard.html
│   │   │   ├── admin_lab_selector.html
│   │   │   ├── user_lab_selector.html
│   │   │   ├── edit_computer.html
│   │   │   ├── import_csv_lab.html
│   │   │   └── export_csv_for_lab.html
│   │   ├── base.html
│   │   ├── conflicts.html
│   │   ├── import_csv.html
│   │   ├── index.html
│   │   └── login.html
│   ├── static/
│   │   └── css/
│   │       └── status.css
├── config.py
├── migrations/
├── requirements.txt
├── run.py
├── setup_db.py
└── README.md
ContributingContributions are welcome! If you'd like to contribute to this project, please follow these steps:Fork the repository.Create a new