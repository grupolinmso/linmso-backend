# models.py
from pydantic import BaseModel, EmailStr, field_validator, ValidationError, TypeAdapter
from pydantic_core import PydanticCustomError # <--- ESTA LÍNEA SE VA
from typing import Optional
import re

# Forma oficial de Pydantic v2 de validar un tipo, (adaptador reutilizable)
email_type_adapter = TypeAdapter(EmailStr)

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
            # Uso  del adaptador oficial para validar
            email_type_adapter.validate_python(v)
        except ValidationError:
            raise ValueError('El correo electrónico no es válido (ej: nombre@dominio.com).')
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