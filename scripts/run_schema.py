from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get DB URL
DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine
engine = create_engine(DATABASE_URL)

# Read schema.sql
with open("sql/schema.sql", "r") as file:
    schema_sql = file.read()

# Execute schema
with engine.connect() as conn:
    conn.execute(text(schema_sql))
    conn.commit()

print("✅ Schema created successfully!")