# settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Email configuración
    MAILGUN_API_KEY: str
    MAILGUN_DOMAIN: str

    # Email direcciones
    FROM_EMAIL: str 
    TO_EMAIL: str   

    # CORS
    FRONTEND_URL: str # "https://www.linmso.com"

    class Config:
        env_file = ".env" # Carga las variables desde el archivo .env

# Exportar la instancia para usarla en la aplicación

settings = Settings()