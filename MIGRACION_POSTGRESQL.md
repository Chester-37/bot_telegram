# 🐘 GUÍA COMPLETA DE MIGRACIÓN A POSTGRESQL

## 📥 Paso 1: Instalar PostgreSQL

### Opción A: PostgreSQL nativo (Recomendado)
1. **Descargar PostgreSQL 15 o superior:**
   - Ir a: https://www.postgresql.org/download/windows/
   - Descargar el instalador oficial
   - **Usuario:** postgres
   - **Contraseña:** Elegir una contraseña segura (anotar bien)
   - **Puerto:** 5432 (por defecto)

2. **Verificar instalación:**
   ```bash
   psql --version
   ```

### Opción B: Docker (Alternativa)
1. **Instalar Docker Desktop:**
   - Descargar de: https://www.docker.com/products/docker-desktop/
   - Reiniciar después de instalar

2. **Usar docker-compose existente:**
   ```bash
   docker-compose up -d db
   ```

## ⚙️ Paso 2: Configurar la base de datos

### Si usas PostgreSQL nativo:
1. **Abrir pgAdmin** (incluido con PostgreSQL)
2. **Conectar al servidor local**
3. **Crear base de datos:** `bot_telegram_db`
4. **Crear usuario:** `bot_user` con contraseña

### Comandos SQL para crear usuario:
```sql
CREATE USER bot_user WITH PASSWORD 'bot_password123';
CREATE DATABASE bot_telegram_db OWNER bot_user;
GRANT ALL PRIVILEGES ON DATABASE bot_telegram_db TO bot_user;
```

## 🔄 Paso 3: Actualizar configuración

### Modificar archivo .env:
```bash
# Cambiar a PostgreSQL
USE_SQLITE=false
POSTGRES_DB=bot_telegram_db
POSTGRES_USER=bot_user
POSTGRES_PASSWORD=tu_contraseña_real_aqui
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## 📊 Paso 4: Ejecutar migración

### Ejecutar scripts en orden:
```bash
# 1. Crear schema en PostgreSQL
python setup_database.py

# 2. Importar datos de SQLite
python import_sqlite_to_postgres.py

# 3. Verificar migración
python test_migration.py
```

## ✅ Paso 5: Verificar sistema

### Probar bot con PostgreSQL:
```bash
python main.py
```

## 🔒 Paso 6: Backup automático (Opcional)

### Configurar backups regulares:
```bash
# Crear script de backup diario
pg_dump -h localhost -U bot_user bot_telegram_db > backup_$(date +%Y%m%d).sql
```

---

## 🚨 PUNTOS IMPORTANTES:

1. **Los datos están seguros** - Ya tienes backup completo de SQLite
2. **Mantén SQLite** - Como respaldo hasta confirmar que PostgreSQL funciona
3. **Prueba antes de eliminar** - Verifica que todo funciona antes de limpiar
4. **Anota contraseñas** - Guarda las credenciales de PostgreSQL

## 🔧 Solución de problemas comunes:

### Error "connection refused":
- Verificar que PostgreSQL esté ejecutándose
- Comprobar puerto 5432 disponible
- Verificar firewall

### Error de permisos:
- Verificar usuario/contraseña
- Comprobar permisos de base de datos

### Error de encoding:
- Usar UTF-8 en PostgreSQL
- Verificar configuración regional
