Bank Management System (Flask + SQLite)

Overview
This project is a simple banking management web application built with Flask and SQLite.
It supports two roles:
- Admin: create/delete customers and view all transactions.
- Customer: view account details, deposit, withdraw, and transfer funds.

Main Features
- Login/logout with role-based dashboard
- Admin customer management
- Auto account creation for new customers
- Deposit, withdrawal, and transfer operations
- Transaction history for admin and customer
- Basic validation for username, name, phone, and positive amount checks

Project Structure
- app.py: Flask application and routes
- banking.sql: Reference SQL schema and queries
- templates/: HTML pages
- static/style.css: Styling

Requirements
- Python 3.9+
- Flask
- Werkzeug

Quick Start
1) Open terminal in project folder.
2) Install dependencies:
   pip install flask werkzeug
3) Run app:
   python app.py
4) Open browser:
   http://127.0.0.1:5000

Default Admin Login
- Username: admin
- Password: admin123

Database
- SQLite file: banking.db
- It is created automatically when app.py runs for the first time.

Notes
- This is a learning/demo project.
- Do not use hardcoded secrets and default credentials in production.
