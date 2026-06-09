CREATE TABLE IF NOT EXISTS masividades_detalle (
    id INT AUTO_INCREMENT PRIMARY KEY,
masividad_log_id BIGINT NOT NULL,
    proceso_codigo VARCHAR(50) NOT NULL,
    mandante_nombre VARCHAR(100) NOT NULL,
    rut VARCHAR(50),
    telefono VARCHAR(50),
    mail VARCHAR(150),
    operacion VARCHAR(100),
    plantilla VARCHAR(100),
    mensaje TEXT,
    extra_json JSON,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (masividad_log_id) REFERENCES masividades_log(id)
);
