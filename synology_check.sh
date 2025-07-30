#!/bin/bash

# =============================================================================
# Script de verificación para Synology DS1520+ / DSM 7.2
# =============================================================================

echo "🔍 VERIFICANDO CONFIGURACIÓN PARA SYNOLOGY DS1520+"
echo "=================================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para checks
check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✅ $1 está instalado${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 NO está instalado${NC}"
        return 1
    fi
}

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✅ Archivo encontrado: $1${NC}"
        return 0
    else
        echo -e "${RED}❌ Archivo NO encontrado: $1${NC}"
        return 1
    fi
}

check_directory() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✅ Directorio encontrado: $1${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  Directorio NO encontrado: $1${NC}"
        echo -e "${BLUE}   Créalo con: sudo mkdir -p $1${NC}"
        return 1
    fi
}

echo -e "\n${BLUE}1. VERIFICANDO SISTEMA SYNOLOGY${NC}"
echo "--------------------------------"

# Verificar DSM
if [ -f "/etc.defaults/VERSION" ]; then
    DSM_VERSION=$(grep buildnumber /etc.defaults/VERSION | cut -d'"' -f4)
    echo -e "${GREEN}✅ DSM detectado - Build: $DSM_VERSION${NC}"
else
    echo -e "${YELLOW}⚠️  No se detectó DSM o no es Synology${NC}"
fi

# Verificar modelo
if [ -f "/proc/sys/kernel/syno_hw_version" ]; then
    MODEL=$(cat /proc/sys/kernel/syno_hw_version)
    echo -e "${GREEN}✅ Modelo detectado: $MODEL${NC}"
    if [[ "$MODEL" == *"1520+"* ]]; then
        echo -e "${GREEN}✅ DS1520+ confirmado${NC}"
    else
        echo -e "${YELLOW}⚠️  Modelo diferente a DS1520+, pero debería funcionar${NC}"
    fi
fi

echo -e "\n${BLUE}2. VERIFICANDO DOCKER${NC}"
echo "---------------------"

check_command docker
check_command docker-compose

if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo -e "${BLUE}   Versión: $DOCKER_VERSION${NC}"
    
    # Verificar que Docker esté corriendo
    if docker info &> /dev/null; then
        echo -e "${GREEN}✅ Docker daemon está corriendo${NC}"
    else
        echo -e "${RED}❌ Docker daemon NO está corriendo${NC}"
        echo -e "${BLUE}   Inicia Docker desde Container Manager${NC}"
    fi
fi

echo -e "\n${BLUE}3. VERIFICANDO ESTRUCTURA DE DIRECTORIOS${NC}"
echo "----------------------------------------"

# Directorios principales para Synology
VOLUME_PATH="/volume1/docker/bot_telegram"
DATA_PATH="$VOLUME_PATH/data"
POSTGRES_PATH="$VOLUME_PATH/postgres_data"
LOGS_PATH="$VOLUME_PATH/logs"
BACKUPS_PATH="$VOLUME_PATH/backups"

check_directory "/volume1"
check_directory "/volume1/docker"
check_directory "$VOLUME_PATH"
check_directory "$DATA_PATH"
check_directory "$POSTGRES_PATH"
check_directory "$LOGS_PATH"
check_directory "$BACKUPS_PATH"

echo -e "\n${BLUE}4. VERIFICANDO ARCHIVOS DE CONFIGURACIÓN${NC}"
echo "----------------------------------------"

check_file "docker-compose.yml"
check_file ".env"
check_file "Dockerfile"
check_file "requirements.txt"
check_file "main.py"
check_file "db_adapter.py"

echo -e "\n${BLUE}5. VERIFICANDO CONFIGURACIÓN .ENV${NC}"
echo "-----------------------------------"

if [ -f ".env" ]; then
    # Verificar variables críticas
    if grep -q "BOT_TOKEN=your_telegram_bot_token_here" .env; then
        echo -e "${RED}❌ BOT_TOKEN no configurado${NC}"
        echo -e "${BLUE}   Edita .env y agrega tu token de @BotFather${NC}"
    else
        echo -e "${GREEN}✅ BOT_TOKEN configurado${NC}"
    fi
    
    if grep -q "USE_SQLITE=false" .env; then
        echo -e "${GREEN}✅ Configurado para usar PostgreSQL${NC}"
    else
        echo -e "${YELLOW}⚠️  Configurado para SQLite (cambia a PostgreSQL para Synology)${NC}"
    fi
    
    if grep -q "POSTGRES_PASSWORD=MiPassword123!Seguro" .env; then
        echo -e "${YELLOW}⚠️  Usando password por defecto - ¡CÁMBIALO!${NC}"
        echo -e "${BLUE}   Edita POSTGRES_PASSWORD en .env${NC}"
    else
        echo -e "${GREEN}✅ Password de PostgreSQL personalizado${NC}"
    fi
fi

echo -e "\n${BLUE}6. VERIFICANDO PUERTOS${NC}"
echo "----------------------"

# Verificar puerto 5432 (PostgreSQL)
if netstat -tuln 2>/dev/null | grep -q ":5432 "; then
    echo -e "${YELLOW}⚠️  Puerto 5432 ya está en uso${NC}"
    echo -e "${BLUE}   Puede que sea otra instancia de PostgreSQL${NC}"
else
    echo -e "${GREEN}✅ Puerto 5432 disponible${NC}"
fi

echo -e "\n${BLUE}7. COMANDOS PARA CREAR DIRECTORIOS FALTANTES${NC}"
echo "============================================"

cat << 'EOF'
# Ejecutar en SSH como admin:
sudo mkdir -p /volume1/docker/bot_telegram/{data,postgres_data,logs,backups}
sudo mkdir -p /volume1/docker/bot_telegram/data/{photos,reports,backups}
sudo chown -R 1000:1000 /volume1/docker/bot_telegram/
sudo chmod -R 755 /volume1/docker/bot_telegram/

# Verificar permisos:
ls -la /volume1/docker/bot_telegram/
EOF

echo -e "\n${BLUE}8. PRÓXIMOS PASOS${NC}"
echo "=================="

echo -e "${BLUE}1. Editar .env con tus datos reales:${NC}"
echo -e "   - BOT_TOKEN (de @BotFather)"
echo -e "   - POSTGRES_PASSWORD (seguro)"
echo -e "   - ADMIN_USER_ID (tu ID de Telegram)"

echo -e "\n${BLUE}2. Crear directorios si no existen:${NC}"
echo -e "   sudo mkdir -p /volume1/docker/bot_telegram/{data,postgres_data,logs,backups}"

echo -e "\n${BLUE}3. Copiar archivos a Synology:${NC}"
echo -e "   Usar FileStation o SCP para subir todo a /volume1/docker/bot_telegram/"

echo -e "\n${BLUE}4. Ejecutar desde Container Manager:${NC}"
echo -e "   Crear proyecto → bot_telegram → Ejecutar"

echo -e "\n${BLUE}5. O ejecutar desde SSH:${NC}"
echo -e "   cd /volume1/docker/bot_telegram"
echo -e "   sudo docker-compose up -d --build"

echo -e "\n${GREEN}¡VERIFICACIÓN COMPLETADA!${NC}"
echo "========================"
