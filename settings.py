# settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Email configuration
    MAILGUN_API_KEY: str
    MAILGUN_DOMAIN: str

    # Email Addresses
    FROM_EMAIL: str # "Formulario LINMSO <mailgun@linmso.com>"
    TO_EMAIL: str   # "ventas@linmso.com"

    # CORS
    FRONTEND_URL: str # "https://www.linmso.com"

    class Config:
        env_file = ".env" # Carga las variables desde el archivo .env

# Exportar la instancia para usarla en la aplicación

settings = Settings()