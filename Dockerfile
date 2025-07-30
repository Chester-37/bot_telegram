# Dockerfile

# 1. Usar una imagen base oficial de Python.
# 'slim' es una versión ligera, ideal para producción.
FROM python:3.11-slim

# 2. Establecer el directorio de trabajo dentro del contenedor.
WORKDIR /app

# 3. Copiar solo el fichero de requisitos primero.
# Esto aprovecha el cache de Docker. Si requirements.txt no cambia,
# no se volverán a instalar las dependencias en cada build.
COPY requirements.txt .

# 4. Instalar las dependencias.
# --no-cache-dir reduce el tamaño de la imagen.
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copiar el resto del código de tu aplicación al contenedor.
COPY . .

# 6. Comando que se ejecutará cuando el contenedor se inicie.
CMD ["python", "main.py"]

