# 📋 CONFIGURACIÓN RÁPIDA PARA SYNOLOGY DS1520+

## 🎯 **DATOS QUE DEBES MODIFICAR**

### **1. 🤖 TOKEN DEL BOT (OBLIGATORIO)**

**Archivo:** `.env`
```bash
# Cambiar esta línea:
BOT_TOKEN=your_telegram_bot_token_here

# Por tu token real de @BotFather:
BOT_TOKEN=1234567890:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### **2. 🗄️ CONFIGURACIÓN POSTGRESQL (OBLIGATORIO)**

**Archivo:** `.env`
```bash
# Cambiar estos valores por seguridad:
POSTGRES_DB=bot_telegram_db          # ← Puedes dejarlo así
POSTGRES_USER=bot_admin              # ← Puedes dejarlo así  
POSTGRES_PASSWORD=MiPassword123!Seguro  # ← ¡CAMBIA ESTO!

# Por ejemplo:
POSTGRES_PASSWORD=TuPasswordMuySeguro2024!
```

### **3. 👤 TU ID DE TELEGRAM (OBLIGATORIO)**

**Archivo:** `.env`
```bash
# Cambiar estos valores:
ADMIN_USER_ID=195947658              # ← Tu ID real
NOTIFICATION_CHAT_ID=195947658       # ← Tu ID real
AUTHORIZED_USERS=195947658,123456789 # ← IDs autorizados
```

**¿Cómo obtener tu ID?**
1. Envía un mensaje a `@userinfobot` en Telegram
2. O usa `@RawDataBot`
3. Copia el número y reemplázalo

### **4. 📁 RUTAS EN SYNOLOGY (IMPORTANTE)**

**Archivo:** `docker-compose.yml`

Las rutas están configuradas para:
```yaml
volumes:
  - /volume1/docker/bot_telegram/postgres_data:/var/lib/postgresql/data
  - /volume1/docker/bot_telegram/data:/app/data
  - /volume1/docker/bot_telegram/logs:/app/logs
```

**Si tu volumen es diferente**, cambiar `/volume1/` por tu volumen real:
- `/volume2/docker/bot_telegram/...`
- `/volumeUSB1/docker/bot_telegram/...`

## 🛠️ **PASOS DE INSTALACIÓN**

### **Paso 1: Crear directorios en Synology**
```bash
# SSH como admin
ssh admin@tu_synology_ip

# Crear estructura
sudo mkdir -p /volume1/docker/bot_telegram/{data,postgres_data,logs,backups}
sudo mkdir -p /volume1/docker/bot_telegram/data/{photos,reports,backups}

# Permisos
sudo chown -R 1000:1000 /volume1/docker/bot_telegram/
sudo chmod -R 755 /volume1/docker/bot_telegram/
```

### **Paso 2: Subir archivos**
1. **Via FileStation:** Subir todos los archivos del proyecto a `/volume1/docker/bot_telegram/`
2. **Via SCP:** 
   ```bash
   scp -r * admin@tu_synology_ip:/volume1/docker/bot_telegram/
   ```

### **Paso 3: Configurar en Container Manager**
1. Abrir **Container Manager** en DSM
2. Ir a **"Proyecto"** → **"Crear"**
3. **Nombre:** `bot_telegram`
4. **Ruta:** `/volume1/docker/bot_telegram`
5. **Ejecutar**

### **Paso 4: Verificar funcionamiento**
```bash
# Ver logs
sudo docker-compose logs -f telegram-bot

# Estado de contenedores
sudo docker-compose ps

# Test de base de datos
sudo docker-compose exec db psql -U bot_admin -d bot_telegram_db -c "\dt"
```

## ⚙️ **CONFIGURACIONES OPCIONALES**

### **Zona Horaria**
```bash
# En .env cambiar:
TZ=Europe/Madrid     # ← Tu zona horaria
```

### **Notificaciones de errores**
```bash
# En .env:
NOTIFICATION_CHAT_ID=tu_id_aqui  # Para recibir errores
```

### **Usuarios autorizados**
```bash
# En .env, agregar IDs separados por coma:
AUTHORIZED_USERS=195947658,987654321,123456789
```

## 🔧 **COMANDOS ÚTILES**

### **Gestión del contenedor**
```bash
# Reiniciar bot
sudo docker-compose restart telegram-bot

# Parar todo
sudo docker-compose down

# Iniciar con rebuild
sudo docker-compose up -d --build

# Ver logs en tiempo real
sudo docker-compose logs -f
```

### **Backup de base de datos**
```bash
# Backup manual
sudo docker-compose exec db pg_dump -U bot_admin bot_telegram_db > backup.sql

# Restaurar backup
sudo docker-compose exec -T db psql -U bot_admin bot_telegram_db < backup.sql
```

### **Monitoreo**
```bash
# Uso de recursos
sudo docker stats

# Espacio en disco
sudo docker system df

# Logs del sistema
sudo docker-compose logs db
sudo docker-compose logs telegram-bot
```

## 🆘 **SOLUCIÓN DE PROBLEMAS**

### **Error: Bot no responde**
```bash
# Verificar token
sudo docker-compose logs telegram-bot | grep -i "token"

# Verificar conectividad
sudo docker-compose exec telegram-bot ping telegram.org
```

### **Error: Base de datos no conecta**
```bash
# Verificar PostgreSQL
sudo docker-compose logs db

# Test de conexión
sudo docker-compose exec telegram-bot python -c "from db_adapter import get_connection; print('OK' if get_connection() else 'ERROR')"
```

### **Error: Permisos**
```bash
# Reestablecer permisos
sudo chown -R 1000:1000 /volume1/docker/bot_telegram/
sudo chmod -R 755 /volume1/docker/bot_telegram/
```

### **Error: Puerto ocupado**
```bash
# Ver qué usa el puerto 5432
sudo netstat -tulpn | grep 5432

# Si es necesario, cambiar puerto en docker-compose.yml:
ports:
  - "5433:5432"  # Puerto externo 5433
```

## ✅ **VERIFICACIÓN FINAL**

### **Checklist:**
- [ ] ✅ **BOT_TOKEN** configurado con token real
- [ ] ✅ **POSTGRES_PASSWORD** cambiado por uno seguro
- [ ] ✅ **ADMIN_USER_ID** configurado con tu ID real
- [ ] ✅ **Directorios creados** en `/volume1/docker/bot_telegram/`
- [ ] ✅ **Archivos subidos** a Synology
- [ ] ✅ **Container Manager** proyecto creado y ejecutando
- [ ] ✅ **Bot responde** en Telegram
- [ ] ✅ **Base de datos** conecta correctamente

### **Test final:**
1. Enviar `/start` al bot en Telegram
2. Verificar que responde con el menú principal
3. Probar función de avances
4. Verificar en Container Manager que ambos contenedores están "running"

---

🎉 **¡Tu bot estará funcionando perfectamente en Synology DS1520+!**

Para soporte adicional, revisar los logs en:
- Container Manager → Contenedor → Logs
- `/volume1/docker/bot_telegram/logs/`
