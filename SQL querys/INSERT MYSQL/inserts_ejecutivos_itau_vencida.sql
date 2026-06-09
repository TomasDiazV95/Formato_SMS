-- Ejecutivos Itau Vencida (upsert)
INSERT INTO ejecutivos_phoenix (mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador)
VALUES
    ('Itau Vencida', 'analitt_karina_olivar_riveros', 'Analitt Karina Olivar Riveros', 'aolivar@phoenixservice.cl', '979382039', 'aolivar@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'cesar_escobar_gonzalez', 'Cesar Escobar Gonzalez', 'Cescobar@phoenixservice.cl', '949925366', 'cescobar@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'duchka_uribe_martinez', 'Duchka Uribe Martinez', 'duribe@phoenixservice.cl', '956719890', 'duribe@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'jessica_carolina_diaz_mata', 'Jessica Carolina Diaz Mata', 'jdiaz@phoenixservice.cl', '981804485', 'jdiaz@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'katterine_parraguez_riquelme', 'Katterine Parraguez Riquelme', 'kparraguez@phoenixservice.cl', '959629301', 'kparraguez@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'monica_alejandra_colarte_carrasco', 'Monica Alejandra Colarte Carrasco', 'mcolarte@phoenixservice.cl', '972150239', 'mcolarte@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'pilar_javiera_aracena_ceron', 'Pilar Javiera Aracena  Ceron', 'paracena@phoenixservice.cl', '946980356', 'paracena@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'veronica_margarita_vega_bustos', 'Veronica Margarita Vega Bustos', 'vvega@phoenixservice.cl', '993884467', 'vvega@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'yasna_uribe_martinez', 'Yasna Uribe Martinez', 'yuribe@phoenixservice.cl', '944710186', 'yuribe@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'nicolle_milla', 'Nicolle Milla', 'nmilla@phoenixservice.cl', '961286439', 'kavendano@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'carmina_urrutia_urrutia', 'Carmina Urrutia Urrutia', 'Currutia@phoenixservice.cl', '922027692', 'Currutia@info.phoenixserviceinfo.cl'),
    ('Itau Vencida', 'karen_avendano_calderon', 'Karen Avendano Calderon', 'kavendano@phoenixservice.cl', '938731034', 'kavendano@info.phoenixserviceinfo.cl')
ON DUPLICATE KEY UPDATE
    nombre_mostrar = VALUES(nombre_mostrar),
    correo = VALUES(correo),
    telefono = VALUES(telefono),
    reenviador = VALUES(reenviador),
    activo = 1;

-- Alias recomendados para match de CARTERIZADO
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Analitt Karina Olivar Riveros' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'analitt_karina_olivar_riveros';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'analitt karina olivar riveros' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'analitt_karina_olivar_riveros';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'ANALITT KARINA OLIVAR RIVEROS' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'analitt_karina_olivar_riveros';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Cesar Orlando Escobar González' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'cesar orlando escobar gonzález' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CESAR ORLANDO ESCOBAR GONZÁLEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Cesar Escobar Gonzalez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'cesar escobar gonzalez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CESAR ESCOBAR GONZALEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Cesar Orlando Escobar Gonzalez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'cesar orlando escobar gonzalez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CESAR ORLANDO ESCOBAR GONZALEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'cesar_escobar_gonzalez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Duchka Estefanny Uribe Martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'duchka_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'duchka estefanny uribe martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'duchka_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'DUCHKA ESTEFANNY URIBE MARTINEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'duchka_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Duchka Uribe Martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'duchka_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'duchka uribe martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'duchka_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'DUCHKA URIBE MARTINEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'duchka_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Jessica Carolina Díaz Mata' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'jessica_carolina_diaz_mata';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'jessica carolina díaz mata' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'jessica_carolina_diaz_mata';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'JESSICA CAROLINA DÍAZ MATA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'jessica_carolina_diaz_mata';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Jessica Carolina Diaz Mata' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'jessica_carolina_diaz_mata';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'jessica carolina diaz mata' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'jessica_carolina_diaz_mata';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'JESSICA CAROLINA DIAZ MATA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'jessica_carolina_diaz_mata';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Katterine Fernanda Parraguez Riquelme' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'katterine_parraguez_riquelme';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'katterine fernanda parraguez riquelme' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'katterine_parraguez_riquelme';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'KATTERINE FERNANDA PARRAGUEZ RIQUELME' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'katterine_parraguez_riquelme';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Katterine Parraguez Riquelme' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'katterine_parraguez_riquelme';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'katterine parraguez riquelme' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'katterine_parraguez_riquelme';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'KATTERINE PARRAGUEZ RIQUELME' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'katterine_parraguez_riquelme';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Monica Alejandra Colarte Carrasco' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'monica_alejandra_colarte_carrasco';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'monica alejandra colarte carrasco' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'monica_alejandra_colarte_carrasco';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'MONICA ALEJANDRA COLARTE CARRASCO' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'monica_alejandra_colarte_carrasco';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Pilar Javiera Aracena Ceron' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'pilar_javiera_aracena_ceron';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'pilar javiera aracena ceron' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'pilar_javiera_aracena_ceron';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'PILAR JAVIERA ARACENA CERON' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'pilar_javiera_aracena_ceron';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Pilar Javiera Aracena  Ceron' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'pilar_javiera_aracena_ceron';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'pilar javiera aracena  ceron' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'pilar_javiera_aracena_ceron';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'PILAR JAVIERA ARACENA  CERON' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'pilar_javiera_aracena_ceron';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Veronica Margarita Vega Bustos' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'veronica_margarita_vega_bustos';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'veronica margarita vega bustos' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'veronica_margarita_vega_bustos';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'VERONICA MARGARITA VEGA BUSTOS' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'veronica_margarita_vega_bustos';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Yasna Isabel Uribe Martínez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'yasna isabel uribe martínez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'YASNA ISABEL URIBE MARTÍNEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Yasna Uribe Martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'yasna uribe martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'YASNA URIBE MARTINEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Yasna Isabel Uribe Martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'yasna isabel uribe martinez' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'YASNA ISABEL URIBE MARTINEZ' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'yasna_uribe_martinez';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Nicole Alejandra Milla Miranda' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'nicolle_milla';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'nicole alejandra milla miranda' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'nicolle_milla';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'NICOLE ALEJANDRA MILLA MIRANDA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'nicolle_milla';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Nicolle Milla' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'nicolle_milla';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'nicolle milla' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'nicolle_milla';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'NICOLLE MILLA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'nicolle_milla';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Carmiña Daniela Urrutia Urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'carmiña daniela urrutia urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CARMIÑA DANIELA URRUTIA URRUTIA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Carmiña Urrutia Urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'carmiña urrutia urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CARMIÑA URRUTIA URRUTIA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Carmina Daniela Urrutia Urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'carmina daniela urrutia urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CARMINA DANIELA URRUTIA URRUTIA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Carmina Urrutia Urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'carmina urrutia urrutia' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'CARMINA URRUTIA URRUTIA' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'carmina_urrutia_urrutia';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Karen Andrea Avendaño Calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'karen andrea avendaño calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'KAREN ANDREA AVENDAÑO CALDERON' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Karen Avendaño Calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'karen avendaño calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'KAREN AVENDAÑO CALDERON' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Karen Andrea Avendano Calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'karen andrea avendano calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'KAREN ANDREA AVENDANO CALDERON' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'Karen Avendano Calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'karen avendano calderon' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) SELECT id, 'KAREN AVENDANO CALDERON' FROM ejecutivos_phoenix WHERE mandante = 'Itau Vencida' AND nombre_clave = 'karen_avendano_calderon';
