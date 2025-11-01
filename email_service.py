# email_service.py
import httpx 
from models import ContactCreate
from settings import settings

# Se actualiza el build_email_body para que sea más limpio
def _build_email_body(
        contact: ContactCreate,
        ip_address: str,
        user_agent: str,
        server_timestamp_utc: str,
        server_timestamp_cst: str,
        client_timezone: str,
        client_language: str,
        client_timestamp_full: str
        ) -> str:

    servicio_legible = contact.servicio.replace('-', ' ').title()

    # Formato más limpio, con saltos de línea y encabezados en español
    return f"""
Nuevo mensaje desde el formulario de contacto de LINMSO:

--- INFORMACIÓN DEL CLIENTE ---
- Nombre: {contact.nombre}
- Empresa: {contact.empresa or 'No especificada'}
- Teléfono: {contact.telefono}
- Email: {contact.email}

--- DETALLES DE LA SOLICITUD ---
- Servicio Solicitado: {servicio_legible}
- Mensaje:
{contact.mensaje or 'El cliente no dejó un mensaje adicional.'}

--- INFORMACIÓN TÉCNICA ---
- IP de Origen: {ip_address} 
- Agente (Navegador/SO): {user_agent} 
- Idioma del Navegador: {client_language}
- Zona Horaria del Dispositivo: {client_timezone}
- Hora del Servidor (UTC): {server_timestamp_utc}
- Hora del Servidor (CST): {server_timestamp_cst}
- Hora del Cliente (Local): {client_timestamp_full}
---
Enviado desde el sitio web LINMSO.
    """

# Envía notificación por correo usando la API Mailgun
async def send_contact_notification(
        contact: ContactCreate,
        ip_address: str,
        user_agent: str, 
        server_timestamp_utc: str,
        server_timestamp_cst: str,
        client_timezone: str,
        client_language: str,
        client_timestamp_full: str
        ) -> bool:
    
    api_key = settings.MAILGUN_API_KEY
    domain = settings.MAILGUN_DOMAIN
    
    if not api_key or not domain:
        print("ERROR: Faltan las variables de entorno de Mailgun (API_KEY, DOMAIN).")
        return False

    api_url = f"https://api.mailgun.net/v3/{domain}/messages"

    email_body = _build_email_body(
        contact, 
        ip_address, 
        user_agent, 
        server_timestamp_utc,
        server_timestamp_cst,
        client_timezone,
        client_language,
        client_timestamp_full
    )

    email_data = {
        "from": settings.FROM_EMAIL,
        "to": settings.TO_EMAIL,
        "subject": f"Nuevo Contacto Web: {contact.nombre}",
        "text": email_body
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, auth=("api", api_key), data=email_data)
            response.raise_for_status() 
            print("Correo enviado exitosamente a través de Mailgun.")
            return True
        except httpx.HTTPStatusError as e:
            print(f"Error al enviar el correo con Mailgun: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            print(f"Un error inesperado ocurrió: {e}")
            return False