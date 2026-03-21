import os
import sqlalchemy as sa

from dotenv import load_dotenv
from pathlib import Path

ENV = os.getenv('ENV', default='development')
BASE_DIR = Path(__file__).resolve().parent.parent.parent

if ENV == 'development':
    load_dotenv(BASE_DIR / '.env.dev')
    db_host = 'localhost'
else:
    load_dotenv(BASE_DIR / '.env.prod')
    db_host = os.getenv('POSTGRES_HOST', default='postgres-app')

db_port = os.getenv('POSTGRES_PORT', default='5432')
db_user = os.getenv('POSTGRES_USER', default='jmie_user')
db_password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB', default='jmie_db')

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DATABASE_URL = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

def seed_sources():
    engine = sa.create_engine(DATABASE_URL)

    seed_query = sa.text("""
        INSERT INTO sources (name, url, country, language, created_at, updated_at)
        VALUES
            ('LinkedIn EN', 'https://www.linkedin.com', 'US', 'en', NOW(), NOW()),
            ('LinkedIn PT', 'https://www.linkedin.com', 'BR', 'pt', NOW(), NOW()),
            ('Gupy PT', 'https://gupy.io', 'BR', 'pt', NOW(), NOW()),
            ('Remote.ok EN', 'https://remoteok.com', 'Global', 'en', NOW(), NOW())
        ON CONFLICT (name) DO NOTHING;
    """)

    with engine.connect() as conn:
        conn.execute(seed_query)
        conn.commit()
        print("✅ 'sources' table successfully seeded with job boards!")

if __name__ == '__main__':
    seed_sources()