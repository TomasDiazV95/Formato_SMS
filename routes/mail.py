import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file

from services.mail_service import build_mail_crm_output, sample_mail_crm_output
from services.mail_templates import MAIL_TEMPLATE_OPTIONS, build_mail_template, sample_mail_template
from services.mandante_rules import apply_mandante_rules
from services.constants import MANDANTE_CHOICES
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

mail_bp = Blueprint('mail', __name__)


def _mail_error(message: str, status: int = 400):
    return api_error_response(message, 'mail.mail_page', status=status)


def _build_mail_detalle(df: pd.DataFrame, template_code: str) -> list[dict[str, str | None]]:
    if df is None or df.empty:
        return []
    detalles = []
    for _, row in df.iterrows():
        rut = (
            str(row.get("RUT+DV", "")).strip()
            or str(row.get("RUT", "")).strip()
        ) or None
        operacion = (
            str(row.get("NRO_OPERACION", "")).strip()
            or str(row.get("OPERACION", "")).strip()
            or str(row.get("NUM_OP", "")).strip()
        ) or None
        detalles.append({
            "rut": rut,
            "operacion": operacion,
            "mail": str(row.get("dest_email", "")).strip() or None,
            "plantilla": template_code,
            "mensaje": None,
            "extra": {
                "nombre_agente": str(row.get("NOMBRE_AGENTE", "")).strip() or None,
                "mail_agente": str(row.get("MAIL_AGENTE", "")).strip() or None,
            }
        })
    return detalles

@mail_bp.get('/mail')
def mail_page():
    return serve_react_app()


@mail_bp.post('/mail/template')
def mail_template_process():
    file = request.files.get('file')
    mandante_nombre = (request.form.get('mandante_template') or '').strip()
    template_code = (request.form.get('template_code') or '').strip()

    if not file or file.filename == '':
        return _mail_error('Debes subir un archivo Excel.')
    if not mandante_nombre:
        return _mail_error('Debes seleccionar un Mandante.')
    if not template_code:
        return _mail_error('Debes seleccionar una plantilla.')

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        salida = build_mail_template(df, template_code, mandante_nombre)
        nombre = f'plantilla_{template_code}.xlsx'
        buf = df_to_xlsx_bytesio(salida, sheet_name='PlantillaMail')

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        proceso = db_repos.fetch_proceso_by_codigo('MAIL_CRM') if mandante else None
        if mandante and proceso:
            masividad_id = db_repos.log_masividad(
                mandante_id=mandante.id,
                proceso_id=proceso.id,
                total_registros=len(salida),
                costo_unitario=proceso.costo_unitario,
                usuario_app='mail',
                archivo_generado=nombre,
                observacion=f'Plantilla {template_code}',
                metadata={'template': template_code},
            )
            detalles = _build_mail_detalle(salida, template_code)
            if masividad_id and detalles:
                db_repos.bulk_insert_masividad_detalle(
                    masividad_log_id=masividad_id,
                    proceso_codigo=proceso.codigo,
                    mandante_nombre=mandante.nombre,
                    registros=detalles,
                )

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except ValueError as e:
        return _mail_error(str(e))
    except Exception as e:
        return _mail_error(f'Ocurrió un error procesando el archivo: {e}', status=500)

@mail_bp.post('/mail/crm')
def mail_crm_process():
    file = request.files.get('file')
    usuario = (request.form.get('usuario') or '').strip()
    observacion = (request.form.get('observacion') or '').strip()
    fecha_str = (request.form.get('fecha') or '').strip()
    hora_inicio = (request.form.get('hora_inicio') or '').strip()
    hora_fin = (request.form.get('hora_fin') or '').strip()
    intervalo_str = (request.form.get('intervalo') or '').strip()

    intervalo = None
    if intervalo_str:
        try:
            intervalo_val = int(intervalo_str)
            if intervalo_val <= 0:
                raise ValueError
            intervalo = intervalo_val
        except ValueError:
            return _mail_error('El intervalo debe ser un entero positivo en segundos.')

    if not file or file.filename == '':
        return _mail_error('Debes subir un archivo Excel.')
    if not usuario:
        return _mail_error('Debes ingresar un Usuario.')
    if not fecha_str or not hora_inicio or not hora_fin:
        return _mail_error('Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.')

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        return _mail_error('Formato de fecha inválido (usa AAAA-MM-DD).')

    try:
        df = pd.read_excel(file, dtype=str)
        salida = build_mail_crm_output(
            df=df,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            usuario_value=usuario,
            observacion_value=observacion,
            intervalo_segundos=intervalo,
        )
        fecha_salida = fecha.strftime('%d-%m')
        buf = df_to_xlsx_bytesio(salida, sheet_name='cargaMailCRM')
        nombre = f'carga_MAIL_CRM_{fecha_salida}.xlsx'

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
    except ValueError as e:
        return _mail_error(str(e))
    except Exception as e:
        return _mail_error(f'Ocurrió un error procesando el archivo: {e}', status=500)


@mail_bp.get('/mail/sample/template')
def mail_template_sample():
    template_code = (request.args.get('template_code') or '').strip() or MAIL_TEMPLATE_OPTIONS[0].code
    try:
        salida = sample_mail_template(template_code)
    except ValueError as exc:
        return _mail_error(str(exc))
    nombre = f'ejemplo_MAIL_TEMPLATE_{template_code}.xlsx'
    buf = df_to_xlsx_bytesio(salida, sheet_name='PlantillaMail')
    return send_file(
        buf,
        as_attachment=True,
        download_name=nombre,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@mail_bp.get('/mail/sample/crm')
def mail_crm_sample():
    salida = sample_mail_crm_output()
    nombre = 'ejemplo_MAIL_CRM.xlsx'
    buf = df_to_xlsx_bytesio(salida, sheet_name='cargaMailCRM')
    return send_file(
        buf,
        as_attachment=True,
        download_name=nombre,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
