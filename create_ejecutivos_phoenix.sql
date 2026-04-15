CREATE TABLE IF NOT EXISTS ejecutivos_phoenix (
    id INT AUTO_INCREMENT PRIMARY KEY,
    mandante VARCHAR(150) NOT NULL,
    nombre_clave VARCHAR(150) NOT NULL,
    nombre_mostrar VARCHAR(150) NULL,
    correo VARCHAR(200) NULL,
    telefono VARCHAR(80) NULL,
    reenviador VARCHAR(200) NULL,
    metadata_json JSON NULL,
    activo TINYINT(1) NOT NULL DEFAULT 1,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_mandante_nombre (mandante, nombre_clave)
);

CREATE TABLE IF NOT EXISTS ejecutivos_alias (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ejecutivo_id INT NOT NULL,
    alias VARCHAR(150) NOT NULL,
    creado_en TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uniq_ejecutivo_alias (ejecutivo_id, alias),
    CONSTRAINT fk_alias_ejecutivo FOREIGN KEY (ejecutivo_id)
        REFERENCES ejecutivos_phoenix(id) ON DELETE CASCADE
);
