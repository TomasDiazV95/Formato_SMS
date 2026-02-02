# services/sant_hipotecario_masividad_service.py
import os
from datetime import datetime

import numpy as np
import pandas as pd


def generar_masividad(df: pd.DataFrame, output_dir: str) -> dict:
    """Genera Excel Masividad desde df base."""
    os.makedirs(output_dir, exist_ok=True)

    columnas_masividad = [
        'INSTITUCIÓN','SEGMENTOINSTITUCIÓN','message_id','PLANTILLA','RUT',
        'NRO_OPERACION','CLIENTE','dest_email','name_from','mail_from','CORREO',
        'EJECUTIVO2','CELULAR','DIA','MES','ANHO'
    ]

    df_mas = pd.DataFrame(columns=columnas_masividad)

    df_mas['RUT'] = df['rut']
    df_mas['CLIENTE'] = df['nombre_cliente']
    df_mas['NRO_OPERACION'] = df['numero_operacion'].astype(str).str.zfill(12)

    # Limpieza mail
    df_mas['dest_email'] = df['mail'].astype(str).str.strip()
    df_mas.loc[df_mas['dest_email'].str.lower() == 'nan', 'dest_email'] = None
    df_mas = df_mas.dropna(subset=['dest_email'])
    df_mas = df_mas[df_mas['dest_email'].str.strip() != '']

    # Dedupe por RUT
    df_mas = df_mas.drop_duplicates(subset=['RUT'], keep='first')

    now = datetime.now()
    df_mas['DIA'] = now.strftime('%d')
    df_mas['MES'] = now.strftime('%B').capitalize()
    df_mas['ANHO'] = now.strftime('%Y')

    df_mas = df_mas.assign(
        INSTITUCIÓN='BANCO SANTANDER',
        SEGMENTOINSTITUCIÓN='BANCO SANTANDER',
        message_id=91785,
        PLANTILLA='HIPOTECARIO',
        name_from='Atencion Cliente Banco Santander',
        CELULAR=225830435
    ).fillna('')

    nombres_ejecutivos = [
        'Olga Arenas','Ana Leal','Melanie Ortiz','Francisca Huerta','Claudia Apablaza',
        'Maria Gomez','Maria Cristina Chavarria','Lorena Fuentes','Pablo Rivas',
        'Claudia Paola Hasbun Estolaza','Claudia Alejandra Aravena Quinteros',
        'Jesús Manuel Olivares Peña','Andrea Lorena Perez Brito', 'Marcela Roca', 'Pilar Gonzales'
    ]

    correos_ejecutivos = [
        'oarenas@phoenixservice.cl','aleal@phoenixservice.cl','mmondiglio@phoenixservice.cl',
        'fhuerta@phoenixservice.cl','capablaza@phoenixservice.cl','mgomez@phoenixservice.cl',
        'mchavarria@phoenixservice.cl','lofuentes@phoenixservice.cl','privas@phoenixservice.cl',
        'chasbun@phoenixservice.cl','caravena@phoenixservice.cl','jolivares@phoenixservice.cl',
        'aperez@phoenixservice.cl','mroca@phoenixservice.cl','pgonzales@phoenixservice.cl'
    ]

    correos_masivos = [
        'oarenas@info.phoenixserviceinfo.cl','aleal@info.phoenixserviceinfo.cl','mmondiglio@info.phoenixserviceinfo.cl',
        'ghuerta@estandar.phoenixserviceinfo.cl','capablaza@estandar.phoenixserviceinfo.cl','mgomez@info.phoenixserviceinfo.cl',
        'mchavarria@info.phoenixserviceinfo.cl','lfuentes@info.phoenixserviceinfo.cl','privas@info.phoenixserviceinfo.cl',
        'chasbun@info.phoenixserviceinfo.cl','caravena@info.phoenixserviceinfo.cl','jolivares@info.phoenixserviceinfo.cl',
        'aperez@info.phoenixserviceinfo.cl','mroca@info.phoenixserviceinfo.cl','pgonzales@info.phoenixserviceinfo.cl'
    ]

    df_mas['EJECUTIVO2'] = np.resize(nombres_ejecutivos, len(df_mas))
    df_mas['CORREO'] = np.resize(correos_ejecutivos, len(df_mas))
    df_mas['mail_from'] = np.resize(correos_masivos, len(df_mas))

    fecha_actual = now.strftime("%d-%m")
    masiv_name = f"Masividad Hipotecario {fecha_actual}.xlsx"
    masiv_path = os.path.join(output_dir, masiv_name)

    df_mas.to_excel(masiv_path, index=False)

    return {"masiv_path": masiv_path, "masiv_name": masiv_name}
