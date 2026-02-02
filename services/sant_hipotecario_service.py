# services/sant_hipotecario_service.py
import os
import io
from datetime import datetime

import pandas as pd
import chardet


def _detect_encoding(file_bytes: bytes) -> str:
    result = chardet.detect(file_bytes)
    return result.get("encoding") or "utf-8"


def leer_csv_sant_hipotecario(file_storage) -> pd.DataFrame:
    """Lee CSV separado por ';' desde Flask FileStorage y retorna df base."""
    file_bytes = file_storage.read()
    encoding = _detect_encoding(file_bytes)
    stream = io.BytesIO(file_bytes)
    df = pd.read_csv(stream, encoding=encoding, sep=";", on_bad_lines="skip")
    return df


def generar_crm(df: pd.DataFrame, output_dir: str) -> dict:
    """Genera Excel CRM desde df base."""
    os.makedirs(output_dir, exist_ok=True)

    columnas_CRM = [
        'Nro_Documento', 'RUT - DV', 'NOMBRE', 'AD1', 'NombreProducto', 'AD2', 'AD3',
        'AD4', 'AD5', 'AD6', 'AD7', 'DEUDA TOTAL', 'AD11', 'AD8', 'AD9', 'AD10',
        'DIRECCION', 'COMUNA', 'CIUDAD', 'REGION', 'DIRECCION_COMERCIAL',
        'COMUNA_COMERCIAL', 'CIUDAD_COMERCIAL', 'REGION_COMERCIAL', 'EMAIL1',
        'AD13', 'FONO1', 'FONO2', 'FONO3', 'FONO4', 'FONO5', 'FONO6', 'AD14',
        'AD15', 'TIPO_DEUDOR', 'TIPO_PRODUCTO 1', 'AFINIDAD_1', 'NRO_PRODUCTO 1',
        'FECHA_VEN_1', 'COD_SEG_1', 'ID_BANCO_1', 'TIPO_PRODUCTO_2', 'AFINIDAD_2',
        'NRO_PRODUCTO_2', 'FECHA_VEN_2', 'COD_SEG_2', 'ID_BANCO_2',
        'TIPO_PRODUCTO_3', 'AFINIDAD_3', 'NRO_PRODUCTO_3', 'FECHA_VEN_3',
        'COD_SEG_3', 'ID_BANCO_3', 'TIPO_PRODUCTO_4', 'AFINIDAD_4',
        'NRO_PRODUCTO_4', 'FECHA_VEN_4', 'COD_SEG_4', 'ID_BANCO_4',
        'TIPO_PRODUCTO_5', 'AFINIDAD_5', 'NRO_PRODUCTO_5', 'FECHA_VEN_5',
        'COD_SEG_5', 'ID_BANCO_5', 'PRIMER_NOMBRE', 'SEGUNDO_NOMBRE',
        'APE_PATERNO', 'APE_MATERNO', 'EDAD', 'SEXO', 'FECHA_NAC', 'NUMERO',
        'DEPARTAMENTO', 'POBLACION'
    ]

    df_crm = pd.DataFrame(columns=columnas_CRM)

    # --- CRM ---
    df_crm['Nro_Documento'] = df['numero_operacion'].astype(str).str.zfill(12)
    df_crm['RUT - DV'] = df['rut'].astype(str) + '-' + df['dv_cliente'].astype(str)
    df_crm['NOMBRE'] = df['nombre_cliente']
    df_crm['NombreProducto'] = df['nombre_producto']
    df_crm['AD2'] = df['perfil_riesgo']
    df_crm['AD1'] = df['ciclo']
    df_crm['AD3'] = df['dias_atraso']
    df_crm['FONO1'] = df.get('telefono_1', '')
    df_crm['FONO2'] = df.get('telefono_2', '')
    df_crm['FONO3'] = df.get('telefono_3', '')
    df_crm['FONO4'] = df.get('telefono_4', '')
    df_crm['FONO5'] = df.get('telefono_5', '')
    df_crm['DIRECCION'] = df.get('direccion', '')
    df_crm['AD5'] = df.get('estrategia_1', '')
    df_crm['AD11'] = df.get('nro_cuotas_pagadas', '')
    df_crm['AD8'] = df.get('total_cuotas', '')
    df_crm['AD9'] = df.get('nro_cuotas_en_mora', '')

    df_crm['AD7'] = pd.to_datetime(
        df.get('fecha_vcto_cuota', ''),
        format='%Y%m%d',
        errors='coerce'
    ).dt.strftime('%d-%m-%Y')

    df_crm['AD6'] = pd.to_numeric(df.get('monto_cuota', ''), errors='coerce').fillna(0).astype(int)
    df_crm['AD10'] = df.get('tipo_campana', '')
    df_crm['DEUDA TOTAL'] = pd.to_numeric(df.get('total_arrastre', ''), errors='coerce').fillna(0).astype(int)
    df_crm['EMAIL1'] = df.get('mail', '')

    df_crm = df_crm.fillna('')

    now = datetime.now()
    fecha_actual = now.strftime("%d-%m")
    crm_name = f"ARCHIVO DE CARGA ASIGNACION HIPOTECARIO {fecha_actual}.xlsx"
    crm_path = os.path.join(output_dir, crm_name)

    df_crm.to_excel(crm_path, index=False)

    return {"crm_path": crm_path, "crm_name": crm_name}
