# ☕ KOPPEE - Premium Coffee Shop & Management Platform

A modern, production-grade Django web application for an artisanal coffee roastery and café. KOPPEE provides customer-facing ordering, table reservations, contact inquiries, OTP-secured authentication, and a staff administration dashboard for live product and booking management.

---

## 🌟 Key Features

### 🛍️ Customer Experience
- **Interactive Menu & Catalog**: Categorized listing of handcrafted **Hot Coffee** and **Cold Coffee** items with dynamic image rendering and pricing.
- **Online Table Reservation**: Real-time table booking with conflict-prevention (duplicate slot detection) and automated email confirmations.
- **Inquiry & Feedback Desk**: Contact messaging portal with immediate notification dispatch.
- **One-Time Registration OTP**: Two-factor signup email verification. Once registered, customers log in directly with **Email & Password** without OTP.
- **Dedicated Customer Login**: Clean, warm café-themed portal at `/login/`.

### 🛡️ Admin & Staff Dashboard
- **Strictly Protected Analytics Portal**: Protected by `@admin_required`. Customer accounts can NEVER open the dashboard.
- **Dedicated Admin Login**: High-security, dark-themed control portal at `/admin-login/`.
- **Direct Login (No OTP)**: Sign in instantly with **any Username / Email** (e.g. `admin`, `superadmin`, `manager` — valid email format zaroori nahi hai) aur **Password**.
- **Live Metrics**: Real-time counters for active products, table bookings, customer messages, and registered users.
- **Product Management (CRUD)**: Easily add, edit, or remove coffee products with image uploads and validation.
- **Reservation Manager**: Review, update, or cancel customer table bookings.
- **User Account Management**: Directly activate, deactivate, or delete customer accounts inside the custom admin.
- **Create Admin from Dashboard**: Dedicated `+ Create Admin` button in the users section (`/dashboard/users/create-admin/`) to add new Superadmins or Staff Admins with custom usernames/emails and instant activation.

---

## 🚀 Quickstart Guide

### 1. Setup Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 3. Apply Migrations
```powershell
python manage.py migrate
```

### 4. Create Admin Account
```powershell
python manage.py setup_admin --email admin@koppee.com --password admin123
```

### 5. Run Server
```powershell
python manage.py runserver
```
- Customer Portal: `http://127.0.0.1:8000/login/`
- Admin Dashboard: `http://127.0.0.1:8000/admin` (or `/admin/`)
- Admin Login Portal: `http://127.0.0.1:8000/admin-login/`

---

## 🧪 Running Automated Tests

```powershell
$env:DB_ENGINE="sqlite3"; python manage.py test products
```
