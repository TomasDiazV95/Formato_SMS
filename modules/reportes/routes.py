from __future__ import annotations

import io
import json
from datetime import datetime, timedelta
from typing import Any, cast

import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio
from frontend import serve_react_app

reports_bp = Blueprint('reports', __name__)

PROCESS_APP_MAP = {
    'sms': 'sms',
    'ivr': 'ivr',
    'mail': 'mail',
}


def _parse_period_filters() -> tuple[datetime | None, datetime | None, dict[str, Any] | None, str | None]:
    anio_raw = (request.args.get('anio') or '').strip()
    mes_raw = (request.args.get('mes') or '').strip()
    desde_raw = (request.args.get('desde') or '').strip()
    hasta_raw = (request.args.get('hasta') or '').strip()

    if (anio_raw or mes_raw) and (desde_raw or hasta_raw):
        return None, None, None, "No puedes combinar filtros por mes con filtro desde/hasta."

    if anio_raw or mes_raw:
        if not anio_raw or not mes_raw:
            return None, None, None, "Debes indicar anio y mes juntos."
        try:
            anio = int(anio_raw)
            mes = int(mes_raw)
            fecha_inicio = datetime(anio, mes, 1)
            if mes == 12:
                fecha_fin = datetime(anio + 1, 1, 1) - timedelta(seconds=1)
            else:
                fecha_fin = datetime(anio, mes + 1, 1) - timedelta(seconds=1)
        except ValueError:
            return None, None, None, 'Mes o año inválido.'
        return fecha_inicio, fecha_fin, {'tipo': 'mes', 'anio': anio, 'mes': mes}, None

    if desde_raw or hasta_raw:
        if not desde_raw or not hasta_raw:
            return None, None, None, 'Debes indicar desde y hasta para filtro por rango.'
        try:
            fecha_inicio = datetime.strptime(desde_raw, '%Y-%m-%d')
            fecha_fin = datetime.strptime(hasta_raw, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
        except ValueError:
            return None, None, None, 'Formato de fecha inválido (usa AAAA-MM-DD).'
        return fecha_inicio, fecha_fin, {'tipo': 'rango', 'desde': desde_raw, 'hasta': hasta_raw}, None

    return None, None, {'tipo': 'historico'}, None


def _calc_variation(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round(((current - previous) / previous) * 100, 2)

@reports_bp.get('/reportes/costos')
def report_costos():
    mandante = (request.args.get('mandante') or '').strip() or None
    proceso = (request.args.get('proceso') or '').strip() or None
    fecha_inicio, fecha_fin, period_meta, period_err = _parse_period_filters()
    if period_err:
        return jsonify({'error': period_err}), 400

    data = db_repos.get_cost_summary(
        mandante_nombre=mandante,
        proceso_codigo=proceso,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    comparativo = None
    if fecha_inicio and fecha_fin:
        delta = fecha_fin - fecha_inicio
        prev_fin = fecha_inicio - timedelta(seconds=1)
        prev_ini = prev_fin - delta
        prev_data = db_repos.get_cost_summary(
            mandante_nombre=mandante,
            proceso_codigo=proceso,
            fecha_inicio=prev_ini,
            fecha_fin=prev_fin,
        )
        current_regs = int(data['totales']['total_registros'] or 0)
        prev_regs = int(prev_data['totales']['total_registros'] or 0)
        current_cost = float(data['totales']['costo_total'] or 0)
        prev_cost = float(prev_data['totales']['costo_total'] or 0)
        ticket_current = round((current_cost / current_regs), 2) if current_regs else 0
        ticket_prev = round((prev_cost / prev_regs), 2) if prev_regs else 0
        comparativo = {
            'periodo_anterior': {
                'desde': prev_ini.strftime('%Y-%m-%d'),
                'hasta': prev_fin.strftime('%Y-%m-%d'),
            },
            'totales': {
                'total_registros': prev_regs,
                'costo_total': prev_cost,
                'ticket_promedio': ticket_prev,
            },
            'variacion': {
                'total_registros_pct': _calc_variation(current_regs, prev_regs),
                'costo_total_pct': _calc_variation(current_cost, prev_cost),
                'ticket_promedio_pct': _calc_variation(ticket_current, ticket_prev),
            },
        }

    data['periodo'] = {
        **(period_meta or {'tipo': 'historico'}),
        'desde': fecha_inicio.strftime('%Y-%m-%d') if fecha_inicio else None,
        'hasta': fecha_fin.strftime('%Y-%m-%d') if fecha_fin else None,
    }
    total_regs = int(data['totales']['total_registros'] or 0)
    total_cost = float(data['totales']['costo_total'] or 0)
    data['kpis'] = {
        'total_registros': total_regs,
        'costo_total': total_cost,
        'ticket_promedio': round(total_cost / total_regs, 2) if total_regs else 0,
    }
    data['comparativo'] = comparativo
    return jsonify(data)


@reports_bp.get('/reportes/costos/tendencia')
def report_costos_tendencia():
    mandante = (request.args.get('mandante') or '').strip() or None
    proceso = (request.args.get('proceso') or '').strip() or None
    months_raw = (request.args.get('meses') or '').strip()
    anio_raw = (request.args.get('anio') or '').strip()
    mes_raw = (request.args.get('mes') or '').strip()

    months = 12
    if months_raw:
        try:
            months = int(months_raw)
        except ValueError:
            return jsonify({'error': "Parámetro 'meses' inválido."}), 400

    end_year = None
    end_month = None
    if anio_raw or mes_raw:
        if not anio_raw or not mes_raw:
            return jsonify({'error': 'Debes indicar anio y mes juntos para el cierre de tendencia.'}), 400
        try:
            end_year = int(anio_raw)
            end_month = int(mes_raw)
            datetime(end_year, end_month, 1)
        except ValueError:
            return jsonify({'error': 'Mes o año inválido.'}), 400

    items = db_repos.get_monthly_cost_trend(
        months=months,
        mandante_nombre=mandante,
        proceso_codigo=proceso,
        end_year=end_year,
        end_month=end_month,
    )
    return jsonify({'items': items})


@reports_bp.get('/reportes/costos/ranking-mandantes')
def report_costos_ranking_mandantes():
    proceso = (request.args.get('proceso') or '').strip() or None
    limit_raw = (request.args.get('limit') or '').strip()
    limit = 10
    if limit_raw:
        try:
            limit = int(limit_raw)
        except ValueError:
            return jsonify({'error': "Parámetro 'limit' inválido."}), 400

    fecha_inicio, fecha_fin, period_meta, period_err = _parse_period_filters()
    if period_err:
        return jsonify({'error': period_err}), 400
    if not fecha_inicio or not fecha_fin:
        now = datetime.now()
        fecha_inicio = datetime(now.year, now.month, 1)
        if now.month == 12:
            fecha_fin = datetime(now.year + 1, 1, 1) - timedelta(seconds=1)
        else:
            fecha_fin = datetime(now.year, now.month + 1, 1) - timedelta(seconds=1)
        period_meta = {'tipo': 'mes', 'anio': now.year, 'mes': now.month}

    items = db_repos.get_mandante_ranking(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        proceso_codigo=proceso,
        limit=limit,
    )
    return jsonify(
        {
            'periodo': {
                **(period_meta or {'tipo': 'mes'}),
                'desde': fecha_inicio.strftime('%Y-%m-%d'),
                'hasta': fecha_fin.strftime('%Y-%m-%d'),
            },
            'items': items,
        }
    )


@reports_bp.get('/reportes/costos/proceso-vs-mes')
def report_costos_proceso_vs_mes():
    mandante = (request.args.get('mandante') or '').strip() or None
    months_raw = (request.args.get('meses') or '').strip()
    anio_raw = (request.args.get('anio') or '').strip()
    mes_raw = (request.args.get('mes') or '').strip()

    months = 6
    if months_raw:
        try:
            months = int(months_raw)
        except ValueError:
            return jsonify({'error': "Parámetro 'meses' inválido."}), 400

    end_year = None
    end_month = None
    if anio_raw or mes_raw:
        if not anio_raw or not mes_raw:
            return jsonify({'error': 'Debes indicar anio y mes juntos para el cierre.'}), 400
        try:
            end_year = int(anio_raw)
            end_month = int(mes_raw)
            datetime(end_year, end_month, 1)
        except ValueError:
            return jsonify({'error': 'Mes o año inválido.'}), 400

    months_axis = db_repos.get_monthly_cost_trend(
        months=months,
        mandante_nombre=mandante,
        end_year=end_year,
        end_month=end_month,
    )
    matrix = db_repos.get_process_month_matrix(
        months=months,
        mandante_nombre=mandante,
        end_year=end_year,
        end_month=end_month,
    )
    return jsonify({'periodos': [item['periodo'] for item in months_axis], 'items': matrix})


@reports_bp.get('/reportes/historial')
def report_process_history():
    proceso = (request.args.get('proceso') or '').strip().lower()
    if proceso not in PROCESS_APP_MAP:
        return jsonify({'error': "Parámetro 'proceso' inválido. Usa sms, ivr o mail."}), 400

    limit_raw = (request.args.get('limit') or '').strip()
    limit = 20
    if limit_raw:
        try:
            limit = int(limit_raw)
        except ValueError:
            return jsonify({'error': "Parámetro 'limit' inválido. Debe ser un número entero."}), 400

    rows = db_repos.fetch_process_history(usuario_app=PROCESS_APP_MAP[proceso], limit=limit)
    history = [
        {
            'id': row.get('id'),
            'proceso': row.get('proceso_codigo'),
            'descripcion': row.get('proceso_descripcion'),
            'mandante': row.get('mandante_nombre'),
            'registros': int(row.get('total_registros') or 0),
            'fecha_creacion': row.get('fecha_ejecucion'),
            'archivo': row.get('archivo_generado') or '',
        }
        for row in rows
    ]
    return jsonify({'proceso': proceso, 'items': history})

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
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.reindex(columns=columns)
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


@reports_bp.get('/reports/costos/mensual')
def download_costos_mensual():
    mandante = (request.args.get('mandante') or '').strip() or None
    proceso = (request.args.get('proceso') or '').strip() or None
    months_raw = (request.args.get('meses') or '').strip()
    months = 12
    if months_raw:
        try:
            months = int(months_raw)
        except ValueError:
            return jsonify({'error': "Parámetro 'meses' inválido."}), 400

    fecha_inicio, fecha_fin, period_meta, period_err = _parse_period_filters()
    if period_err:
        return jsonify({'error': period_err}), 400
    if not fecha_inicio or not fecha_fin:
        return jsonify({'error': 'Para exporte mensual debes seleccionar anio y mes o rango desde/hasta.'}), 400

    summary = db_repos.get_cost_summary(
        mandante_nombre=mandante,
        proceso_codigo=proceso,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    trend = db_repos.get_monthly_cost_trend(
        months=months,
        mandante_nombre=mandante,
        proceso_codigo=proceso,
        end_year=fecha_fin.year,
        end_month=fecha_fin.month,
    )
    ranking = db_repos.get_mandante_ranking(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        proceso_codigo=proceso,
        limit=15,
    )
    detalle = db_repos.fetch_masividades_detalle(
        mandante_nombre=mandante,
        proceso_codigo=proceso,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        limit=50000,
    )

    resumen_df = pd.DataFrame(summary['resumen_por_proceso'])
    if resumen_df.empty:
        resumen_df = pd.DataFrame({'proceso': [], 'descripcion': [], 'total_registros': [], 'costo_total': []})
    kpis_df = pd.DataFrame(
        [
            {
                'periodo_tipo': (period_meta or {}).get('tipo', 'mes'),
                'desde': fecha_inicio.strftime('%Y-%m-%d'),
                'hasta': fecha_fin.strftime('%Y-%m-%d'),
                'mandante': mandante or 'Todos',
                'proceso': proceso or 'Todos',
                'total_registros': int(summary['totales']['total_registros'] or 0),
                'costo_total': float(summary['totales']['costo_total'] or 0),
            }
        ]
    )
    tendencia_df = pd.DataFrame(trend)
    ranking_df = pd.DataFrame(ranking)
    if ranking_df.empty:
        ranking_df = pd.DataFrame({'mandante': [], 'total_registros': [], 'costo_total': []})

    detalle_rows: list[dict[str, Any]] = []
    for item in detalle:
        extra = item.get('extra_json')
        if isinstance(extra, (dict, list)):
            extra_str = json.dumps(extra, ensure_ascii=False)
        else:
            extra_str = extra or ''
        detalle_rows.append(
            {
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
            }
        )
    detalle_df = pd.DataFrame(detalle_rows)
    if detalle_df.empty:
        detalle_df = pd.DataFrame(
            {
                'Fecha ejecución': [],
                'Mandante': [],
                'Proceso': [],
                'Usuario': [],
                'Archivo generado': [],
                'RUT': [],
                'Teléfono': [],
                'Operación': [],
                'Mail': [],
                'Plantilla': [],
                'Mensaje': [],
                'Extra': [],
            }
        )

    buf = io.BytesIO()
    with pd.ExcelWriter(cast(Any, buf), engine='openpyxl') as writer:
        kpis_df.to_excel(writer, sheet_name='Resumen', index=False)
        resumen_df.to_excel(writer, sheet_name='PorProceso', index=False)
        tendencia_df.to_excel(writer, sheet_name='Tendencia', index=False)
        ranking_df.to_excel(writer, sheet_name='RankingMandantes', index=False)
        detalle_df.to_excel(writer, sheet_name='Detalle', index=False)
    buf.seek(0)

    suffix = ''
    if period_meta and period_meta.get('tipo') == 'mes':
        anio_meta = int(period_meta.get('anio') or fecha_inicio.year)
        mes_meta = int(period_meta.get('mes') or fecha_inicio.month)
        suffix = f"_{anio_meta}_{mes_meta:02d}"
    else:
        suffix = f"_{fecha_inicio.strftime('%Y%m%d')}_{fecha_fin.strftime('%Y%m%d')}"
    filename = f"reporte_costos_mensual{suffix}.xlsx"

    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
