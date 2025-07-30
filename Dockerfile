# =============================================================================
# Dockerfile optimizado para Synology DS1520+ / DSM 7.2
# =============================================================================

# Usar imagen base ligera de Python 3.11 (compatible con ARM64 de Synology)
FROM python:3.11-slim

# Metadatos del contenedor
LABEL maintainer="Bot Telegram Avances"
LABEL description="Bot de Telegram para gestión de avances - Synology DS1520+"
LABEL version="2.0"

# Variables de entorno para optimización
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Instalar dependencias del sistema necesarias para PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad (recomendado para Synology)
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Establecer directorio de trabajo
WORKDIR /app

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorios necesarios con permisos correctos
RUN mkdir -p /app/data /app/logs /app/data/photos /app/data/reports /app/data/backups \
    && chown -R botuser:botuser /app

# Copiar código de la aplicación
COPY --chown=botuser:botuser . .

# Cambiar a usuario no-root
USER botuser

# Exponer puerto para healthcheck (opcional)
EXPOSE 8080

# Healthcheck para Container Manager
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import psutil; exit(0 if any('python' in p.name() for p in psutil.process_iter()) else 1)" || exit 1

# Comando por defecto
CMD ["python", "main.py"]

