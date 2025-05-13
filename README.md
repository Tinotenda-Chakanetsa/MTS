# MTS APP (Modern Tax System Application)

A comprehensive, modular, and extensible tax administration platform built with Python and Flask. Designed for government agencies and organizations to digitize and modernize tax operations, MTS APP streamlines tax processes for both administrators and taxpayers.

---

## Features

- **User Management & Authentication:**
  - Multiple user types (individuals, businesses, agents, staff, officials)
  - Role-based access control
- **Tax Registration & Filing:**
  - Taxpayer registration, tax type management, filing returns
- **Payment Processing:**
  - Tax payment workflows and integration points for payment gateways
- **Licensing:**
  - Business and special license management, issuance, and renewal
- **Audit Management:**
  - Start and track audits, with dedicated UI and routes
- **Reporting & Analytics:**
  - Comprehensive dashboards (tax collection, compliance, registration, audit, refunds, revenue, TADAT)
- **Document Management:** *(Planned/Partial)*
- **Notifications & Reminders:** *(Planned)*
- **Appeals & Disputes:** *(Planned)*
- **Calendar & Scheduling:** *(Planned)*
- **Bulk Data Operations:** *(Planned)*
- **Audit Trail & Logs:** *(Planned)*

---

## Technology Stack

- **Backend:** Python, Flask, SQLAlchemy, Flask-Migrate
- **Frontend:** Jinja2 templates, Bootstrap
- **Database:** SQLite (default, configurable)
- **Testing:** pytest (tests/ directory present)
- **Other:** dotenv for environment configuration

---

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd MTS\ APP

# Create a virtual environment
python -m venv env
source venv/bin/activate  # On Windows: env\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Initialization
```bash
# Initialize the database with default data
flask init-db
```

### Running the Application
```bash
python run.py
```

The app will be available at: http://localhost:5000/

---

## Usage

- Access the system at [http://localhost:5000/](http://localhost:5000/)
- Default admin login (change password in production!):
  - **Username:** Admin
  - **Password:** Password
- Explore modules: Tax, Licensing, Audit, Reporting, etc.

---

## Project Structure

```
MTS APP/
├── app/
│   ├── models/        # Data models
│   ├── routes/        # API/views
│   ├── services/      # Business logic
│   ├── templates/     # HTML templates
│   ├── static/        # Static files (CSS, JS)
│   └── ...
├── migrations/        # Database migrations
├── tests/             # Automated tests
├── requirements.txt   # Python dependencies
├── run.py             # Application entry point
└── README.md          # Project documentation
```

---

## Contributing

Contributions are welcome! To contribute:
- Fork the repository
- Create a new branch for your feature or bugfix
- Submit a pull request with a clear description
- Follow PEP8 and good code practices

---

## Roadmap / To-Do

- [ ] Notifications & Reminders
- [ ] Appeals & Disputes
- [ ] Calendar & Scheduling
- [ ] Document Management
- [ ] Bulk Data Operations
- [ ] Audit Trail & Logs
- [ ] Automated tests (populate `tests/`)
- [ ] Improve API documentation
- [ ] UI/UX enhancements

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Acknowledgements

This project was developed solely by TINOTENDA MARLVINE CHAKANETSA.

- Open source libraries (Flask, SQLAlchemy, etc.)

---

## Notes

This project is a work in progress and has room for improvement. Feedback and contributions are highly encouraged!
