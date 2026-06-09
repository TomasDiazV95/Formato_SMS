-- archivo: create_phoenix_masividades.sql
-- Ejecuta con: mysql -h 127.0.0.1 -P 3307 -u root < create_phoenix_masividades.sql

DROP DATABASE IF EXISTS phoenix_masividades;
CREATE DATABASE phoenix_masividades CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE phoenix_masividades;

CREATE TABLE mandantes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(64) NOT NULL UNIQUE,
    nombre VARCHAR(255) NOT NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO mandantes (codigo, nombre) VALUES
    ('ITAUV', 'Itau Vencida'),
    ('ITAUCAST', 'Itau Castigo'),
    ('CAJA18', 'CAJA18'),
    ('BINTER', 'Banco Internacional'),
    ('SANT_HIPO', 'Santander Hipotecario'),
    ('SANT_CONS_T', 'Santander Consumer Terreno'),
    ('SANT_CONS_F', 'Santander Consumer Telefonía'),
    ('GM', 'General Motors'),
    ('ARAUCANA', 'La Araucana');

CREATE TABLE procesos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(64) NOT NULL UNIQUE,
    descripcion VARCHAR(255) NOT NULL,
    tipo ENUM('SMS','IVR','MAIL') NOT NULL,
    costo_unitario DECIMAL(12,2) NOT NULL,
    moneda CHAR(3) NOT NULL DEFAULT 'CLP',
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO procesos (codigo, descripcion, tipo, costo_unitario) VALUES
    ('SMS_ATHENAS', 'Proceso SMS Layout Athenas', 'SMS', 14.00),
    ('SMS_AXIA', 'Proceso SMS Layout AXIA', 'SMS', 7.00),
    ('IVR_ATHENAS', 'Proceso IVR Athenas', 'IVR', 7.00),
    ('IVR_CRM', 'Proceso IVR CRM', 'IVR', 7.00),
    ('MAIL_CRM', 'Proceso Mail CRM', 'MAIL', 1.00);

CREATE TABLE masividades_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    mandante_id INT NOT NULL,
    proceso_id INT NOT NULL,
    total_registros INT NOT NULL,
    costo_unitario DECIMAL(12,2) NOT NULL,
    costo_total DECIMAL(14,2) NOT NULL,
    usuario_app VARCHAR(128) NOT NULL,
    archivo_generado VARCHAR(255) NULL,
    observacion VARCHAR(255) NULL,
    metadata_json JSON NULL,
    fecha_ejecucion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mandante_id) REFERENCES mandantes(id),
    FOREIGN KEY (proceso_id) REFERENCES procesos(id),
    INDEX idx_log_fecha (fecha_ejecucion),
    INDEX idx_log_mandante (mandante_id),
    INDEX idx_log_proceso (proceso_id)
);
