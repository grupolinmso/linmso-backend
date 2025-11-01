# main.py
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Form, Request 
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from models import ContactCreate
from email_service import send_contact_notification
from settings import settings

app = FastAPI(title="LINMSO Contact API", version="1.0.0")

# Rate limiter: 3 requests cada 10 minutos por IP
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# Diccionarios en memoria para tracking (en producción se puede usar Redis)
success_tracking = {}  
error_tracking = {}    

# Handler personalizado para rate limit
@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Manejador que detecta si es comportamiento de bot o límite normal
    ip = request.client.host if request.client else "unknown"
    
    # Verificar si hay envíos exitosos recientes muy rápidos
    if ip in success_tracking:
        timestamps = success_tracking[ip]
        if len(timestamps) >= 3:
            # Calcular tiempo entre primer y último envío
            time_diff = (timestamps[-1] - timestamps[0]).total_seconds()
            
            if time_diff < 30:  # 3 envíos en menos de 30 segundos = BOT
                error_html = '<div id="form-response" class="error permanent"><strong>Demasiados intentos.</strong> Por favor, espera 10 minutos o contáctanos por <strong>WhatsApp</strong> o <strong>Correo Electrónico</strong>.</div>'
            else:
                # Usuario normal que alcanzó el límite
                error_html = '<div id="form-response" class="info permanent"><strong>Tus mensajes han sido enviados.</strong> Por favor, espera respuesta o contáctanos por <strong>WhatsApp</strong> o <strong>Correo Electrónico</strong>.</div>'
        else:
            error_html = '<div id="form-response" class="error permanent"><strong>Demasiados intentos.</strong> Por favor, espera 10 minutos o contáctanos por <strong>WhatsApp</strong> o <strong>Correo Electrónico</strong>.</div>'
    else:
        error_html = '<div id="form-response" class="error permanent"><strong>Demasiados intentos.</strong> Por favor, espera 10 minutos o contáctanos por <strong>WhatsApp</strong> o <strong>Correo Electrónico</strong>.</div>'
    
    return HTMLResponse(content=error_html, status_code=429)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["POST"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/api/v1/contact", response_class=HTMLResponse)
@limiter.limit("10/10minutes")
async def create_contact(
    request: Request,
    nombre: str = Form(...),
    empresa: str = Form(None),
    telefono: str = Form(...),
    email: str = Form(...),
    servicio: str = Form(...),
    mensaje: str = Form(None),
    website_url: str = Form(None), 
    client_timezone: str = Form("No disponible"),
    client_language: str = Form("No disponible"),
    client_timestamp_full: str = Form("No disponible")
):
    ip = request.client.host if request.client else "unknown"
    
    # Honeypot check
    if website_url:
        print(f"Honeypot triggered from IP: {ip}")
        success_headers = {"HX-Trigger": "form-sent-successfully"}
        success_html = '<div id="form-response" class="success"><strong>¡Mensaje enviado!</strong> Te contactaremos pronto.</div>'
        return HTMLResponse(content=success_html, headers=success_headers)

    try:
        contact_data = ContactCreate(
            nombre=nombre, empresa=empresa, telefono=telefono,
            email=email, servicio=servicio, mensaje=mensaje
        )

        user_agent = request.headers.get("user-agent", "No disponible")
        
        # Timestamps
        FMT_FECHA_HORA = '%d-%m-%Y %H:%M:%S %Z' 
        server_timestamp_utc = datetime.now(timezone.utc)
        mexico_tz = timezone(timedelta(hours=-6))
        server_timestamp_cst = server_timestamp_utc.astimezone(mexico_tz)
        server_utc_str = server_timestamp_utc.strftime(FMT_FECHA_HORA)
        server_cst_str = server_timestamp_cst.strftime(FMT_FECHA_HORA)
        
        # Intentar enviar el email
        success = await send_contact_notification(
            contact=contact_data,
            ip_address=ip,
            user_agent=user_agent,
            server_timestamp_utc=server_utc_str, 
            server_timestamp_cst=server_cst_str, 
            client_timezone=client_timezone,
            client_language=client_language,
            client_timestamp_full=client_timestamp_full
        )
        
        if success:
            # ÉXITO: Registrar el timestamp para detección de bots
            if ip not in success_tracking:
                success_tracking[ip] = []
            success_tracking[ip].append(datetime.now())
            
            # Limpiar timestamps antiguos (más de 10 minutos)
            success_tracking[ip] = [
                ts for ts in success_tracking[ip] 
                if (datetime.now() - ts).total_seconds() < 600
            ]
            
            # Resetear contador de errores en éxito
            if ip in error_tracking:
                error_tracking[ip] = 0
            
            print(f"Envío exitoso desde {ip}. Total de envíos recientes: {len(success_tracking[ip])}")
            
            success_headers = {"HX-Trigger": "form-sent-successfully"}
            success_html = '<div id="form-response" class="success"><strong>¡Mensaje enviado!</strong> Te contactaremos pronto.</div>'
            return HTMLResponse(content=success_html, headers=success_headers)
        else:
            # ERROR DEL SERVIDOR: Incrementar contador
            if ip not in error_tracking:
                error_tracking[ip] = 0
            error_tracking[ip] += 1
            
            error_count = error_tracking[ip]
            print(f"Error del servidor para {ip}. Intento {error_count}/3")
            
            if error_count >= 3:
                error_html = '<div id="form-response" class="error permanent"><strong>No fue posible enviar tu información.</strong> Por favor, contáctanos por <strong>WhatsApp</strong> o por <strong>Correo Electrónico</strong>.</div>'
            else:
                error_html = f'<div id="form-response" class="warning"><strong>Error temporal en el servidor.</strong> Intenta nuevamente. (Intento {error_count}/3)</div>'
            
            return HTMLResponse(content=error_html, status_code=500)

    except ValidationError as e:
        # ERROR DE VALIDACIÓN
        try:
            raw_msg = e.errors()[0]['msg']
            error_msg = raw_msg.replace("Value error, ", "").capitalize()
        except (IndexError, KeyError):
            error_msg = "Datos inválidos en el formulario."
        
        error_html = f'<div id="form-response" class="warning"><strong>Error de validación:</strong> {error_msg}</div>'
        return HTMLResponse(content=error_html, status_code=400)
    
    except Exception as e:
        # ERROR INESPERADO
        print(f"Error inesperado en el endpoint: {e}")
        error_html = '<div id="form-response" class="error"><strong>Error en el sistema.</strong> No fue posible enviar tu información. Por favor, contáctanos por WhatsApp o por correo electrónico.</div>'
        return HTMLResponse(content=error_html, status_code=500)