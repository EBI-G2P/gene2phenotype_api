# Gene2Phenotype (G2P) API

The Gene2Phenotype API provides a RESTful service to access evidence-based gene-disease models, curated from the literature by experts.
It is part of the Gene2Phenotype project, established by David FitzPatrick in 2012 with the aim of accelerating the diagnosis of children with developmental disorders. In 2014, the database moved from the University of Edinburgh to EMBL-EBI and a dedicated website was launched to improve data accessibility. G2P has been generalised to cover other disease areas and extended to capture additional information to provide a more detailed understanding of disease mechanism. To read more about the project please visit the [G2P website](https://www.ebi.ac.uk/gene2phenotype/about/project).

API documentation is available at [Gene2Phenotype API Documentation](https://www.ebi.ac.uk/gene2phenotype/api/).

### Requirements

- Python 3.10+
- MySQL 8

### Installation

```bash
git clone https://github.com/EBI-G2P/gene2phenotype_api.git
cd gene2phenotype_api
pip install -r requirements.txt
```

### Configuration

All configuration settings should be set in the config.ini file. Here's an example configuration:

```ini
[email]
from=<from>
host=<host>
port=<port>
mailing_list=<your_mailing_list>
send_to_mailing_list=True

[settings]
DEBUG = False
ALLOWED_HOSTS = []
CSRF_TRUSTED_ORIGINS = []
CORS_ALLOWED_ORIGINS = []
AUTH_COOKIE_SECURE = False
STATIC_ROOT =
STATIC_URL = <your_static_url>

[g2p]
version=<version>
```

### Usage

1. Configure your environment by updating the config.ini file.
2. Configure your environment variables (including database credentials):
   - `SECRET_KEY`
   - `PROJECT_CONFIG_PATH`
   - `DB_ENGINE`
   - `DB_NAME`
   - `DB_USERNAME`
   - `DB_PASSWORD`
   - `DB_HOST`
   - `DB_PORT`
3. Run the server:

```bash
python manage.py runserver
```
