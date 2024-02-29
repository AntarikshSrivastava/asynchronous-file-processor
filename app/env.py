from dotenv import load_dotenv
import os

load_dotenv()

db_host = os.getenv('DB_HOST')
db_user = os.getenv('DB_USER')
db_pass = os.getenv('DB_PASS')
db_port = os.getenv('DB_PORT')

redis_host = os.getenv('REDIS_HOST')
redis_port = os.getenv('REDIS_PORT')