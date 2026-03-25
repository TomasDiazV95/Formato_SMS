import io

import pandas as pd
from flask import Blueprint, jsonify, render_template, request, send_file

from services import db_repos
from services.constants import MANDANTE_CHOICES
from utils.excel_export import df_to_xlsx_bytesio

reports_bp = Blueprint('reports', __name__)

@reports_bp.get('/reportes/costos')
def report_costos():
    mandante = request.args.get('mandante')
    data = db_repos.get_cost_summary(mandante_nombre=mandante)
    return jsonify(data)

@reports_bp.get('/reports')
def reports_page():
    mandantes = db_repos.fetch_all_mandantes()
    nombres = [m.nombre for m in mandantes]
    return render_template('reports.html', mandantes=nombres)

@reports_bp.get('/reports/costos/totales')
def download_costos_totales():
    data = db_repos.get_cost_summary()
    df = pd.DataFrame(data['resumen_por_proceso'])
    if df.empty:
        df = pd.DataFrame(columns=['proceso', 'descripcion', 'total_registros', 'costo_total'])
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
        df = pd.DataFrame(columns=['proceso', 'descripcion', 'total_registros', 'costo_total'])
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
