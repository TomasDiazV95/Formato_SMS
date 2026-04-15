from __future__ import annotations

import io
import json
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio
from frontend import serve_react_app

reports_bp = Blueprint('reports', __name__)

@reports_bp.get('/reportes/costos')
def report_costos():
    mandante = request.args.get('mandante')
    data = db_repos.get_cost_summary(mandante_nombre=mandante)
    return jsonify(data)

@reports_bp.get('/reports')
def reports_page():
    return serve_react_app()

@reports_bp.get('/reports/costos/totales')
def download_costos_totales():
    data = db_repos.get_cost_summary()
    df = pd.DataFrame(data['resumen_por_proceso'])
    if df.empty:
        base_cols = ['proceso', 'descripcion', 'total_registros', 'costo_total']
        df = pd.DataFrame({col: [] for col in base_cols})
    totals = pd.DataFrame([{
        'proceso': 'TOTAL',
        'descripcion': '',
        'total_registros': data['totales']['total_registros'] or 0,
        'costo_total': data['totales']['costo_total'] or 0,
    }])
    df = pd.concat([df, totals], ignore_index=True)
    buf = df_to_xlsx_bytesio(df, sheet_name='CostosTotales')
    return send_file(
        buf,
        as_attachment=True,
        download_name='reporte_costos_totales.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@reports_bp.get('/reports/costos/mandante')
def download_costos_mandante():
    mandante = request.args.get('mandante')
    if not mandante:
        return jsonify({'error': 'Debe especificar un mandante'}), 400
    data = db_repos.get_cost_summary(mandante_nombre=mandante)
    df = pd.DataFrame(data['resumen_por_proceso'])
    if df.empty:
        base_cols = ['proceso', 'descripcion', 'total_registros', 'costo_total']
        df = pd.DataFrame({col: [] for col in base_cols})
    totals = pd.DataFrame([{
        'proceso': mandante,
        'descripcion': '',
        'total_registros': data['totales']['total_registros'] or 0,
        'costo_total': data['totales']['costo_total'] or 0,
    }])
    df = pd.concat([df, totals], ignore_index=True)
    buf = df_to_xlsx_bytesio(df, sheet_name='CostosMandante')
    filename = f'reporte_costos_{mandante.replace(" ", "_")}.xlsx'
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@reports_bp.get('/reports/detalle')
def download_detalle_masividades():
    mandante = (request.args.get('mandante') or '').strip()
    proceso = (request.args.get('proceso') or '').strip()
    fecha_desde = (request.args.get('desde') or '').strip()
    fecha_hasta = (request.args.get('hasta') or '').strip()

    if not fecha_desde or not fecha_hasta:
        return jsonify({'error': 'Debes indicar fecha desde y hasta (AAAA-MM-DD).'}), 400
    try:
        fecha_inicio = datetime.strptime(fecha_desde, '%Y-%m-%d')
        fecha_fin = datetime.strptime(fecha_hasta, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    except ValueError:
        return jsonify({'error': 'Formato de fecha inválido (usa AAAA-MM-DD).'}), 400

    registros = db_repos.fetch_masividades_detalle(
        mandante_nombre=mandante or None,
        proceso_codigo=proceso or None,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    rows: list[dict[str, Any]] = []
    for item in registros:
        extra = item.get('extra_json')
        if isinstance(extra, (dict, list)):
            extra_str = json.dumps(extra, ensure_ascii=False)
        else:
            extra_str = extra or ''
        rows.append({
            'Fecha ejecución': item.get('fecha_ejecucion'),
            'Mandante': item.get('mandante_nombre'),
            'Proceso': item.get('proceso_codigo'),
            'Usuario': item.get('usuario_app'),
            'Archivo generado': item.get('archivo_generado'),
            'RUT': item.get('rut'),
            'Teléfono': item.get('telefono'),
            'Operación': item.get('operacion'),
            'Mail': item.get('mail'),
            'Plantilla': item.get('plantilla'),
            'Mensaje': item.get('mensaje'),
            'Extra': extra_str,
        })

    columns = ['Fecha ejecución', 'Mandante', 'Proceso', 'Usuario', 'Archivo generado', 'RUT', 'Teléfono', 'Operación', 'Mail', 'Plantilla', 'Mensaje', 'Extra']
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        df = pd.DataFrame({col: [] for col in columns})

    buf = df_to_xlsx_bytesio(df, sheet_name='DetalleMasividades')
    mandante_slug = mandante.replace(' ', '_') if mandante else 'todos'
    filename = f'detalle_masividades_{mandante_slug}_{fecha_desde}_{fecha_hasta}.xlsx'
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
