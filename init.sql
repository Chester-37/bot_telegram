DROP TABLE IF EXISTS solicitud_personal_notas;
DROP TABLE IF EXISTS pedido_items;
DROP TABLE IF EXISTS pedidos;
DROP TABLE IF EXISTS incidencia_comentarios;
DROP TABLE IF EXISTS incidencias;
DROP TABLE IF EXISTS prevencion_incidencia_comentarios;
DROP TABLE IF EXISTS prevencion_incidencias;
DROP TABLE IF EXISTS averias;
DROP TABLE IF EXISTS avances;
DROP TABLE IF EXISTS registros_personal;

DROP TABLE IF EXISTS almacen_items CASCADE;
DROP TABLE IF EXISTS ubicaciones_config CASCADE;
DROP TABLE IF EXISTS solicitudes_personal CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;


-- -----------------------------------------------------------------------------
-- Tabla: usuarios
-- Almacena la información de los usuarios y sus roles.
-- -----------------------------------------------------------------------------
CREATE TABLE usuarios (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    first_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    CONSTRAINT check_role CHECK (role IN ('Encargado', 'Tecnico', 'Gerente', 'Almacen', 'RRHH', 'Prevencion', 'Admin'))
);

-- -----------------------------------------------------------------------------
-- Tabla: almacen_items
-- Inventario de herramientas, EPIS y fungibles.
-- -----------------------------------------------------------------------------
CREATE TABLE almacen_items (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) UNIQUE NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 0,
    descripcion TEXT,
    tipo VARCHAR(50) NOT NULL,
    CONSTRAINT check_item_type CHECK (tipo IN ('Herramienta', 'EPI', 'Fungible'))
);

-- -----------------------------------------------------------------------------
-- Tabla: ubicaciones_config
-- Almacena las opciones de ubicación configurables por el administrador.
-- -----------------------------------------------------------------------------
CREATE TABLE ubicaciones_config (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(50) NOT NULL, -- 'Edificio', 'Planta', 'Zona', 'Trabajo'
    nombre VARCHAR(255) NOT NULL,
    UNIQUE (tipo, nombre)
);

-- -----------------------------------------------------------------------------
-- Tabla: tipos_trabajo
-- Almacena los tipos de trabajo configurables por técnicos.
-- -----------------------------------------------------------------------------
CREATE TABLE tipos_trabajo (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL UNIQUE,
    emoji VARCHAR(10) DEFAULT '🔧',
    activo BOOLEAN DEFAULT TRUE,
    orden INTEGER DEFAULT 0,
    creado_por BIGINT REFERENCES usuarios(user_id),
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Tabla: avances
-- Registra los avances de obra con jerarquía dinámica.
-- -----------------------------------------------------------------------------
CREATE TABLE avances (
    id SERIAL PRIMARY KEY,
    encargado_id BIGINT REFERENCES usuarios(user_id),
    
    -- Ubicación desglosada para búsquedas jerárquicas
    ubicacion_edificio VARCHAR(255),
    ubicacion_zona VARCHAR(255),
    ubicacion_planta VARCHAR(255),
    ubicacion_nucleo VARCHAR(255),

    ubicacion_completa VARCHAR(1024) NOT NULL, 
    
    trabajo VARCHAR(255) NOT NULL,
    tipo_trabajo_id INTEGER REFERENCES tipos_trabajo(id),
    observaciones TEXT,
    foto_path VARCHAR(255),
    estado VARCHAR(50),
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_trabajo DATE
);

-- -----------------------------------------------------------------------------
-- Tabla: incidencias
-- Registra incidencias, ya sea de un avance de obra o de una herramienta.
-- -----------------------------------------------------------------------------
CREATE TABLE incidencias (
    id SERIAL PRIMARY KEY,
    reporta_id BIGINT REFERENCES usuarios(user_id) NOT NULL,
    avance_id INTEGER REFERENCES avances(id) ON DELETE SET NULL,
    item_id INTEGER REFERENCES almacen_items(id) ON DELETE SET NULL,
    descripcion TEXT NOT NULL,
    foto_path VARCHAR(255),
    estado VARCHAR(50),
    fecha_reporte TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_resolucion TIMESTAMP WITH TIME ZONE,
    tecnico_resolutor_id BIGINT REFERENCES usuarios(user_id),
    resolucion_desc TEXT,
    CONSTRAINT chk_incidencia_type CHECK (
        (avance_id IS NOT NULL AND item_id IS NULL) OR
        (avance_id IS NULL AND item_id IS NOT NULL)
    )
);

-- -----------------------------------------------------------------------------
-- Tabla: incidencia_comentarios
-- Historial de comentarios en una incidencia.
-- -----------------------------------------------------------------------------
CREATE TABLE incidencia_comentarios (
    id SERIAL PRIMARY KEY,
    incidencia_id INTEGER REFERENCES incidencias(id) ON DELETE CASCADE,
    usuario_id BIGINT REFERENCES usuarios(user_id),
    comentario TEXT,
    fecha_comentario TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- -----------------------------------------------------------------------------
-- Tabla: pedidos
-- Registra las solicitudes de material.
-- -----------------------------------------------------------------------------
CREATE TABLE pedidos (
    id SERIAL PRIMARY KEY,
    solicitante_id BIGINT REFERENCES usuarios(user_id) NOT NULL,
    aprobador_id BIGINT REFERENCES usuarios(user_id),
    almacen_id BIGINT REFERENCES usuarios(user_id),
    estado VARCHAR(50) NOT NULL,
    notas_solicitud TEXT,
    notas_decision TEXT,
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_decision TIMESTAMP WITH TIME ZONE,
    fecha_preparado TIMESTAMP WITH TIME ZONE,
    fecha_entregado TIMESTAMP WITH TIME ZONE
);

-- -----------------------------------------------------------------------------
-- Tabla: pedido_items
-- Detalle de los artículos solicitados en cada pedido.
-- -----------------------------------------------------------------------------
CREATE TABLE pedido_items (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
    item_id INTEGER REFERENCES almacen_items(id),
    cantidad_solicitada INTEGER NOT NULL,
    cantidad_aprobada INTEGER,
    nombre_item VARCHAR(255) NOT NULL
);

-- -----------------------------------------------------------------------------
-- Tabla: averias
-- Registra las averías de maquinaria reportadas.
-- -----------------------------------------------------------------------------
CREATE TABLE averias (
    id SERIAL PRIMARY KEY,
    reporta_id BIGINT REFERENCES usuarios(user_id) NOT NULL,
    tecnico_id BIGINT REFERENCES usuarios(user_id),
    maquina VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    foto_path VARCHAR(255),
    estado VARCHAR(50) NOT NULL,
    notas_tecnico TEXT,
    fecha_reporte TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_decision TIMESTAMP WITH TIME ZONE
);

-- -----------------------------------------------------------------------------
-- Tabla: solicitudes_personal
-- Almacena el ciclo de vida de una solicitud de personal.
-- -----------------------------------------------------------------------------
CREATE TABLE solicitudes_personal (
    id SERIAL PRIMARY KEY,
    solicitante_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    tecnico_id BIGINT REFERENCES usuarios(user_id),
    gerente_id BIGINT REFERENCES usuarios(user_id),
    -- puesto VARCHAR(255) NOT NULL, -- ELIMINADO
    -- cantidad_solicitada INTEGER NOT NULL, -- ELIMINADO
    fecha_incorporacion DATE NOT NULL,
    estado VARCHAR(50) NOT NULL,
    notas_solicitud TEXT,
    notas_decision TEXT,
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_decision TIMESTAMP WITH TIME ZONE
);

CREATE TABLE solicitud_personal_items (
    id SERIAL PRIMARY KEY,
    solicitud_id INTEGER NOT NULL REFERENCES solicitudes_personal(id) ON DELETE CASCADE,
    puesto VARCHAR(255) NOT NULL,
    cantidad INTEGER NOT NULL
);

-- -----------------------------------------------------------------------------
-- Tabla: solicitud_personal_notas
-- Almacena el historial de anotaciones de RRHH para una solicitud.
-- -----------------------------------------------------------------------------
CREATE TABLE solicitud_personal_notas (
    id SERIAL PRIMARY KEY,
    solicitud_id INTEGER NOT NULL REFERENCES solicitudes_personal(id) ON DELETE CASCADE,
    rrhh_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    nota TEXT NOT NULL,
    fecha_nota TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE prevencion_incidencias (
    id SERIAL PRIMARY KEY,
    reporta_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    ubicacion VARCHAR(255) NOT NULL,
    descripcion TEXT NOT NULL,
    foto_path VARCHAR(255),
    estado VARCHAR(50) NOT NULL,
    fecha_reporte TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    fecha_cierre TIMESTAMP WITH TIME ZONE,
    cerrado_por_id BIGINT REFERENCES usuarios(user_id)
);
-- -----------------------------------------------------------------------------
-- Tabla: prevencion_incidencia_comentarios
-- Historial de comentarios en una incidencia de prevención.
-- -----------------------------------------------------------------------------
CREATE TABLE prevencion_incidencia_comentarios (
    id SERIAL PRIMARY KEY,
    incidencia_id INTEGER NOT NULL REFERENCES prevencion_incidencias(id) ON DELETE CASCADE,
    usuario_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    comentario TEXT NOT NULL,
    fecha_comentario TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- -----------------------------------------------------------------------------
-- Tabla: registros_personal
-- Almacena el recuento diario del personal en obra.
-- -----------------------------------------------------------------------------
CREATE TABLE registros_personal (
    id SERIAL PRIMARY KEY,
    fecha DATE NOT NULL UNIQUE,
    en_obra INTEGER NOT NULL,
    faltas INTEGER NOT NULL,
    bajas INTEGER NOT NULL,
    registrado_por_id BIGINT REFERENCES usuarios(user_id),
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ordenes_trabajo (
    id SERIAL PRIMARY KEY,
    creador_id BIGINT NOT NULL REFERENCES usuarios(user_id),
    descripcion TEXT NOT NULL,
    foto_path VARCHAR(255),
    estado VARCHAR(50) NOT NULL DEFAULT 'Pendiente',
    fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolutor_id BIGINT REFERENCES usuarios(user_id),
    fecha_resolucion TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_orden_estado CHECK (estado IN ('Pendiente', 'Realizada'))
);

-- Insertar datos iniciales para tipos_trabajo
INSERT INTO tipos_trabajo (nombre, emoji, orden) VALUES 
('Albañilería', '🧱', 1),
('Electricidad', '⚡', 2),
('Fontanería', '🔧', 3),
('Pintura', '🎨', 4),
('Carpintería', '🪚', 5),
('Limpieza', '🧹', 6),
('Inspección', '🔍', 7),
('Otro', '📝', 8);

INSERT INTO ubicaciones_config (tipo, nombre) VALUES
('Edificio', 'Edificio 1'),
('Edificio', 'Edificio 2'),
('Edificio', 'Edificio 3'),
('Planta', 'Planta 0'),
('Planta', 'Planta 1'),
('Planta', 'Planta 2'),
('Planta', 'Planta 3'),
('Zona', 'Zona 1'),
('Zona', 'Zona 2'),
('Zona', 'Zona 3'),
('Zona', 'Zona 4'),
('Trabajo', 'Trabajo 1'),
('Trabajo', 'Trabajo 2'),
('Trabajo', 'Trabajo 3');


-- -----------------------------------------------------------------------------
-- INSERCIÓN DE DATOS DE EJEMPLO
-- -----------------------------------------------------------------------------
INSERT INTO usuarios (user_id, username, first_name, role) VALUES
(1108686086, 'tecnico_chemi', 'Chemi', 'Admin'),
--(123456789, 'tecnico_nico', 'TecnicoPrueba', 'Encargado');
(195947658, 'nico_', 'Nico', 'Admin');
-- (111222333, 'almacen_test', 'AlmacenPrueba', 'Almacen'),
-- (444555666, 'rrhh_test', 'RecursosH', 'RRHH');
