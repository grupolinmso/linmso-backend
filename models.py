# models.py
from pydantic import BaseModel, EmailStr, field_validator
from pydantic_core import PydanticCustomError
from typing import Optional
import re

class ContactCreate(BaseModel):
    nombre: str
    empresa: Optional[str] = None
    telefono: str
    email: str
    servicio: str
    mensaje: Optional[str] = None

    @field_validator('nombre')
    def nombre_no_vacio(cls, v):
        if not v.strip():
            raise ValueError('El nombre es requerido')
        return v.strip()

    @field_validator('telefono')
    def telefono_mexicano(cls, v):
        v_limpio = re.sub(r'\D', '', v)
        if len(v_limpio) != 10:
            raise ValueError('El teléfono debe contener 10 dígitos.')
        return v_limpio
    
    @field_validator('email')
    def email_valido(cls, v):
        try:
            EmailStr._validate(v) 
        except PydanticCustomError:
            raise ValueError('El correo electrónico no es válido (ej: nombre@dominio.com).')
        
        # Si pasa, devolvemos el valor original
        return v

    @field_validator('servicio')
    def servicio_valido(cls, v):
        servicios_validos = [
            'personal-limpieza', 'limpieza-profunda', 'pulido-encerado',
            'fumigacion-sanitizacion', 'jardineria', 'venta-productos'
        ]
        if v not in servicios_validos:
            raise ValueError('Servicio no válido')
        return v