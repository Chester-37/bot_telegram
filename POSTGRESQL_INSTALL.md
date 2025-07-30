# 🐘 GUÍA RÁPIDA: INSTALAR POSTGRESQL

## ⚡ Instalación Express (Windows)

### 1. Descargar PostgreSQL
```
https://www.postgresql.org/download/windows/
```
**Recomendado:** PostgreSQL 15 o superior

### 2. Durante la instalación:
- **Usuario:** postgres
- **Contraseña:** Anotar bien (ej: postgres123)
- **Puerto:** 5432
- **Locale:** Spanish, Spain

### 3. Después de instalar:
**Abrir pgAdmin** (incluido con PostgreSQL)

### 4. Crear base de datos:
```sql
-- En pgAdmin, ejecutar:
CREATE USER bot_user WITH PASSWORD 'bot_password123';
CREATE DATABASE bot_telegram_db OWNER bot_user;
GRANT ALL PRIVILEGES ON DATABASE bot_telegram_db TO bot_user;
```

### 5. Configurar proyecto:
```bash
# Actualizar .env con tu contraseña real:
USE_SQLITE=false
POSTGRES_PASSWORD=tu_contraseña_real_aqui
```

### 6. Crear schema:
```bash
python setup_database.py
```

### 7. Migrar datos desde SQLite:
```bash
python import_sqlite_to_postgres.py
```

### 8. Verificar migración:
```bash
python test_migration.py
```

### 9. ¡Listo! Usar el bot:
```bash
python main.py
```

---

## 🚀 MIENTRAS TANTO: PROBAR CON SQLITE

El sistema ya funciona completamente con SQLite.
Puedes probar todas las nuevas funciones de Admin:

1. **Configurar BOT_TOKEN en .env**
2. **Ejecutar: python main.py**
3. **Ir a Admin > Administrar Base de Datos**

---

## 💡 BENEFICIOS DE POSTGRESQL:

- ✅ **Mejor rendimiento** para múltiples usuarios
- ✅ **Transacciones ACID** más robustas  
- ✅ **Backup automático** y herramientas avanzadas
- ✅ **Escalabilidad** para crecimiento futuro
- ✅ **Seguridad enterprise** con control granular
