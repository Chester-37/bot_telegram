# 🏠 CONFIGURACIÓN PARA SYNOLOGY DS1520+ / DSM 7.2

## 📋 **REQUISITOS PREVIOS**

### 1. **Hardware verificado:**
- ✅ **Synology DS1520+** (Intel Celeron J4125, 8GB RAM recomendado)
- ✅ **DSM 7.2** o superior
- ✅ **Container Manager** instalado desde Package Center

### 2. **Preparación del sistema:**
```bash
# Conectar por SSH a tu Synology (como admin)
ssh admin@192.168.1.XXX

# Verificar Docker
sudo docker --version
sudo docker-compose --version
```

## 🛠️ **CONFIGURACIÓN PASO A PASO**

### **PASO 1: Crear estructura de directorios**

```bash
# Conectar por SSH como administrador
ssh admin@tu_synology_ip

# Crear directorios principales
sudo mkdir -p /volume1/docker/bot_telegram/{data,postgres_data,logs,backups}

# Asignar permisos correctos
sudo chown -R 1000:1000 /volume1/docker/bot_telegram/
sudo chmod -R 755 /volume1/docker/bot_telegram/
```

### **PASO 2: Configurar variables importantes**

**📝 Editar archivo `.env`:**

```bash
# 🤖 OBLIGATORIO: Tu token de @BotFather
BOT_TOKEN=1234567890:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 🗄️ OBLIGATORIO: Configurar PostgreSQL
POSTGRES_DB=bot_telegram_db
POSTGRES_USER=bot_admin  
POSTGRES_PASSWORD=TuPasswordSeguro123!

# 👤 OBLIGATORIO: Tu ID de usuario de Telegram
ADMIN_USER_ID=tu_user_id_aqui
NOTIFICATION_CHAT_ID=tu_user_id_aqui
AUTHORIZED_USERS=tu_user_id_aqui,otros_ids

# 🌍 OPCIONAL: Ajustar zona horaria
TZ=Europe/Madrid
```

### **PASO 3: Configuración en Container Manager**

#### **Método A: Usando Container Manager GUI**

1. **Abrir Container Manager** en DSM
2. **Ir a "Proyecto"** → **"Crear"**
3. **Configurar proyecto:**
   - **Nombre:** `bot_telegram`
   - **Ruta:** `/volume1/docker/bot_telegram`
4. **Subir archivos:**
   - `docker-compose.yml`
   - `.env`
   - Todo el código del bot
5. **Ejecutar proyecto**

#### **Método B: Usando línea de comandos**

```bash
# Navegar al directorio
cd /volume1/docker/bot_telegram

# Copiar archivos del proyecto aquí
# (usar FileStation o SCP)

# Construir y ejecutar
sudo docker-compose up -d --build

# Verificar que funciona
sudo docker-compose ps
sudo docker-compose logs -f telegram-bot
```

## 🔧 **CONFIGURACIÓN ESPECÍFICA SYNOLOGY**

### **Rutas importantes modificadas:**

```yaml
# En docker-compose.yml estas rutas están configuradas para Synology:
volumes:
  - /volume1/docker/bot_telegram/postgres_data:/var/lib/postgresql/data
  - /volume1/docker/bot_telegram/data:/app/data
  - /volume1/docker/bot_telegram/logs:/app/logs
```

### **Puertos configurados:**
- **PostgreSQL:** `5432` (interno)
- **Bot:** No necesita puertos externos

### **Optimizaciones para DS1520+:**
- Imagen `postgres:15-alpine` (más ligera)
- `restart: unless-stopped` (mejor para DSM)
- Healthchecks configurados
- Usuario no-root por seguridad

## 🚀 **DESPLIEGUE**

### **1. Primera ejecución:**

```bash
# Construir imágenes
sudo docker-compose build

# Iniciar servicios
sudo docker-compose up -d

# Verificar estado
sudo docker-compose ps
```

### **2. Verificar funcionamiento:**

```bash
# Ver logs del bot
sudo docker-compose logs -f telegram-bot

# Ver logs de PostgreSQL
sudo docker-compose logs -f db

# Verificar base de datos
sudo docker-compose exec db psql -U bot_admin -d bot_telegram_db -c "\dt"
```

### **3. Configurar autostart:**

En **Container Manager** → **Proyecto** → **bot_telegram** → **Configuración**:
- ✅ **Habilitar inicio automático**
- ✅ **Reiniciar contenedores automáticamente**

## 📊 **MONITOREO Y MANTENIMIENTO**

### **Comandos útiles:**

```bash
# Ver estado de contenedores
sudo docker-compose ps

# Reiniciar bot
sudo docker-compose restart telegram-bot

# Ver uso de recursos
sudo docker stats

# Backup de base de datos
sudo docker-compose exec db pg_dump -U bot_admin bot_telegram_db > backup.sql

# Actualizar código
sudo docker-compose down
# (copiar archivos nuevos)
sudo docker-compose up -d --build
```

### **Ubicación de logs:**
- **Sistema:** `/volume1/docker/bot_telegram/logs/`
- **Docker:** Container Manager → Contenedor → Logs
- **PostgreSQL:** `/volume1/docker/bot_telegram/postgres_data/log/`

## 🔐 **SEGURIDAD**

### **Recomendaciones:**
1. **Cambiar passwords por defecto** en `.env`
2. **Usar usuarios no-root** (ya configurado)
3. **Configurar firewall** en DSM si es necesario
4. **Backups regulares** de `/volume1/docker/bot_telegram/`
5. **Actualizar imágenes** regularmente

### **Backup automático:**
```bash
# Crear script de backup
sudo crontab -e

# Agregar línea para backup diario a las 2 AM
0 2 * * * cd /volume1/docker/bot_telegram && docker-compose exec -T db pg_dump -U bot_admin bot_telegram_db > /volume1/docker/bot_telegram/backups/backup_$(date +\%Y\%m\%d).sql
```

## 🆘 **SOLUCIÓN DE PROBLEMAS**

### **Problemas comunes:**

**1. Error de permisos:**
```bash
sudo chown -R 1000:1000 /volume1/docker/bot_telegram/
```

**2. Puerto ocupado:**
```bash
sudo netstat -tulpn | grep 5432
# Cambiar puerto en docker-compose.yml si es necesario
```

**3. Bot no responde:**
```bash
# Verificar token
sudo docker-compose logs telegram-bot | grep -i token

# Verificar conexión a PostgreSQL
sudo docker-compose exec telegram-bot python -c "from db_adapter import get_connection; print(get_connection())"
```

**4. Base de datos no inicia:**
```bash
# Verificar logs
sudo docker-compose logs db

# Recrear volumen si es necesario
sudo docker-compose down -v
sudo docker-compose up -d
```

## 📞 **SOPORTE**

Para obtener tu **user_id de Telegram**:
1. Enviar mensaje a `@userinfobot`
2. O usar: `@RawDataBot`
3. Copiar el número y agregarlo en `.env`

Para obtener el **token del bot**:
1. Hablar con `@BotFather` en Telegram
2. Crear nuevo bot: `/newbot`
3. Copiar token y agregarlo en `.env`

---

✅ **¡Tu bot estará funcionando en Synology DS1520+ con todas las funcionalidades avanzadas!**
