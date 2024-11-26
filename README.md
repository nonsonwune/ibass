# Naija! Find Uni

A comprehensive web platform designed to help students find and explore Nigerian universities and courses. The platform provides an intuitive interface for discovering educational institutions across Nigeria's 36 states.

## Features

- **Institution Discovery**: Search and filter through 170+ universities across Nigeria
- **Course Explorer**: Access information about 1000+ courses
- **Location-based Search**: Find institutions by state and region
- **Interactive UI**: Modern, responsive interface with smooth animations
- **User Authentication**: Secure user accounts and personalized experiences
- **Admin Dashboard**: Comprehensive management interface for administrators

## Technology Stack

- **Backend**: Flask (Python web framework)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Frontend**: HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login
- **Forms**: Flask-WTF
- **Email**: Flask-Mail
- **Caching**: Flask-Caching
- **Migration**: Flask-Migrate
- **Monitoring**: Sentry SDK

## Project Structure

```
ibass1/
├── app/                    # Main application package
│   ├── forms/             # Form definitions
│   ├── models/            # Database models
│   ├── routes/            # Route handlers
│   ├── static/            # Static assets (CSS, JS, images)
│   ├── templates/         # HTML templates
│   ├── utils/             # Utility functions
│   └── views/             # View functions
├── migrations/            # Database migrations
├── scripts/              # Utility scripts
├── instance/             # Instance-specific configurations
└── logs/                 # Application logs
```

## Setup and Installation

1. Clone the repository:
```bash
git clone [repository-url]
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env` file:
```
FLASK_APP=wsgi.py
FLASK_ENV=development
DATABASE_URL=postgresql://[username]:[password]@localhost/[dbname]
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## Development

- Use `flask db migrate` to generate new migrations
- Use `flask db upgrade` to apply migrations
- Run tests with `python -m pytest`

## Deployment

The application is configured for deployment with Gunicorn and includes a Procfile for platform deployment.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the terms of the license included in the repository.

## Acknowledgments

- Contributors and maintainers
- Nigerian Universities Database
- Educational Institution Partners
