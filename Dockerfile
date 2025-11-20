# Usar imagen Python slim como base
FROM python:3.12-slim AS builder

# Configurar directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir --user -r requirements.txt

# Imagen final
FROM python:3.12-slim

# Configurar directorio de trabajo
WORKDIR /app

# Copiar dependencias instaladas desde builder
COPY --from=builder /root/.local /root/.local

# Copiar código de la aplicación
COPY . .

# Asegurar que los scripts de Python usen el path correcto
ENV PATH=/root/.local/bin:$PATH

# Exponer puerto
EXPOSE 8000

# Variable de entorno por defecto
ENV ENVIRONMENT=production
ENV DEVICE=cpu

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
