# OEM Orders Management System

Django-based system for managing purchase orders, delivery notes, claims, and production tracking with automated PDF parsing.

## 🚀 Features

- **PDF Parsing**: Automated PO parsing for multiple customers (Donki, Lopia)
- **Purchase Order Management**: Track and manage customer orders
- **Quotation System**: Create and manage quotations with status tracking
- **Delivery Note Generation**: Generate delivery notes from orders
- **Claims Management**: Track and process customer claims
- **Production Dashboard**: Real-time production monitoring
- **Store Matrix**: Multi-store product allocation
- **Role-based Access Control**: Secure user permissions

## 📦 Supported Customers

### PDF Parsers
- **Donki (Thailand) Co., Ltd.** - `donki_v1`
- **Lopia Trading Co., Ltd.** - `lopia_v1`

Each parser automatically extracts:
- Store information (code, name)
- Order details (PO number, date)
- Line items (barcode, description, quantity, amount)

## 🛠️ Technology Stack

- **Backend**: Django 4.x
- **Database**: PostgreSQL / SQLite
- **PDF Processing**: pdfplumber
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: PythonAnywhere

## 📋 Quick Start

### Local Development

```bash
# Clone repository
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput

# Run development server
python manage.py runserver
```

Visit: `http://localhost:8000`

### Testing

```bash
# Run all tests
python manage.py test

# Test specific parser
python manage.py test apps.parsers.tests.test_lopia_parser -v 2

# Test in shell
python manage.py shell
>>> from apps.parsers.registry import get_parser
>>> parser = get_parser("lopia_v1")
>>> result = parser.parse("PO_Lopia.pdf")
```

## 🌐 PythonAnywhere Deployment

### Quick Deployment (Recommended)

```bash
# SSH into PythonAnywhere
cd ~
git clone https://github.com/kittichaisangpayung-arch/oem-orders.git
cd oem-orders

# Edit username in script
nano deploy_to_pythonanywhere.sh
# Change: PYTHONANYWHERE_USERNAME="your-username"

# Run deployment
chmod +x deploy_to_pythonanywhere.sh
./deploy_to_pythonanywhere.sh
```

### Manual Deployment

See detailed instructions in:
- **[BASH_COMMANDS.md](BASH_COMMANDS.md)** - Complete bash command reference
- **[PYTHONANYWHERE_DEPLOYMENT.md](PYTHONANYWHERE_DEPLOYMENT.md)** - Step-by-step deployment guide

### Update Deployment

```bash
cd ~/oem-orders
chmod +x update_pythonanywhere.sh
./update_pythonanywhere.sh
```

Then reload your web app from PythonAnywhere dashboard.

## 📁 Project Structure

```
oem-orders/
├── apps/
│   ├── claims/              # Claims management
│   ├── core/                # Core models and utilities
│   ├── dashboard/           # Production dashboard
│   ├── ingestion/           # Data ingestion
│   ├── manage_data/         # Data management
│   ├── parsers/             # PDF parsers
│   │   ├── base.py         # Parser interface
│   │   ├── donki.py        # Donki parser
│   │   ├── lopia.py        # Lopia parser
│   │   ├── registry.py     # Parser registry
│   │   └── tests/          # Parser tests
│   └── quotations/          # Quotation system
├── config/                  # Django settings
├── templates/               # HTML templates
├── staticfiles/             # Collected static files
├── fixtures/                # Seed data
├── deploy_to_pythonanywhere.sh    # Deployment script
├── update_pythonanywhere.sh       # Update script
├── create_wsgi_config.sh          # WSGI generator
└── requirements.txt               # Python dependencies
```

## 📖 Documentation

- **[LOPIA_PARSER_IMPLEMENTATION.md](LOPIA_PARSER_IMPLEMENTATION.md)** - Lopia parser documentation
- **[PYTHONANYWHERE_DEPLOYMENT.md](PYTHONANYWHERE_DEPLOYMENT.md)** - Deployment guide
- **[BASH_COMMANDS.md](BASH_COMMANDS.md)** - Command reference
- **[SUMMARY.md](SUMMARY.md)** - Project summary

## 🧪 Adding a New Customer Parser

1. Create parser file: `apps/parsers/your_customer.py`
2. Inherit from `BasePOParser`
3. Implement `parse()` method
4. Register with `@register("customer_v1")`
5. Add import in `apps/parsers/apps.py`
6. Create tests in `apps/parsers/tests/`

Example:
```python
from .base import BasePOParser, ParsedPO
from .registry import register

@register("newcustomer_v1")
class NewCustomerParser(BasePOParser):
    def parse(self, pdf_path: str) -> ParsedPO:
        # Your parsing logic
        pass
```

## 🔒 Security

- Set `DEBUG=False` in production
- Use strong `SECRET_KEY`
- Configure `ALLOWED_HOSTS` properly
- Keep dependencies updated
- Protect sensitive files (.env, credentials)

## 📊 Database Models

- **Customer**: Customer information with parser mapping
- **Product**: Product catalog with barcodes
- **Store**: Store locations and details
- **PurchaseOrder**: Customer orders
- **Quotation**: Sales quotations with items
- **DeliveryNote**: Delivery documentation
- **Claim**: Customer claims and returns
- **ProductionClaim**: Production tracking

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -m 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit pull request

## 📝 License

This project is proprietary software.

## 👥 Contact

- Repository: https://github.com/kittichaisangpayung-arch/oem-orders
- Issues: https://github.com/kittichaisangpayung-arch/oem-orders/issues

## 🎯 Recent Updates

- ✅ Added Lopia parser support (2024)
- ✅ Enhanced quotation system with status tracking
- ✅ Improved deployment automation scripts
- ✅ Comprehensive testing suite for parsers
