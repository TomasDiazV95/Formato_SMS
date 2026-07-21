import io
import zipfile
import pandas as pd
from datetime import date, datetime
from flask import Blueprint, request, send_file
import re
import unicodedata

from services.mail_templates import MAIL_TEMPLATE_OPTIONS, build_mail_template, sample_mail_template
from services.mail_service import build_mail_crm_output
from services.mandante_rules import apply_mandante_rules
from utils.excel_export import df_to_xlsx_bytes, df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

mail_bp = Blueprint('mail', __name__)

MAIL_CRM_RULES = {
    'itau vencida': ('VDAD', 'ENVIO SIN RESPUESTA'),
    'itau castigo': ('VDAD', 'ENVIO SIN RESPUESTA'),
    'banco internacional': ('VDAD', ''),
    'la araucana': ('VDAD', ''),
    'tanner': ('VDAD', ''),
    'santander consumer judicial': ('jriveros', ''),
    'general motors': ('jriveros', 'ENVIO MAIL'),
}


def _mail_error(message: str, status: int = 400):
    return api_error_response(message, 'mail.mail_page', status=status)


def _filename_safe(value: str) -> str:
    text = unicodedata.normalize('NFKD', value or '').encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^A-Za-z0-9]+', '_', text).strip('_')
    return text or 'MAIL_TEMPLATE'


def _template_output_name(template_code: str, mandante_nombre: str) -> str:
    template = next((item for item in MAIL_TEMPLATE_OPTIONS if item.code == template_code), None)
    template_id = str(template.message_id) if template else '00000'
    template_name = _filename_safe(template.label if template else template_code)
    mandante_name = _filename_safe(mandante_nombre)
    fecha_salida = datetime.now().strftime('%d-%m-%Y')
    return f'{template_id}_{template_name}_{mandante_name}_{fecha_salida}.xlsx'


def _crm_rule_for_mail(mandante: str) -> tuple[str, str] | None:
    return MAIL_CRM_RULES.get((mandante or '').strip().lower())


def _zip_mail_outputs(files: list[tuple[str, bytes]]) -> io.BytesIO:
    zip_bio = io.BytesIO()
    with zipfile.ZipFile(zip_bio, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for filename, payload in files:
            zf.writestr(filename, payload)
    zip_bio.seek(0)
    return zip_bio


def _filter_mail_crm_seed_rows(df: pd.DataFrame) -> pd.DataFrame:
    rut_col = next((col for col in df.columns if str(col).strip().lower() in {'rut', 'rut ', 'rut+dv', 'rutdv'}), None)
    if not rut_col:
        return df
    seed_values = {'prb', '1', '2', '3', '4', '1-1', '1-2'}
    rut = df[rut_col].fillna('').astype(str).str.strip().str.lower()
    return df.loc[~rut.isin(seed_values)].copy()


@mail_bp.get('/mail')
def mail_page():
    return serve_react_app()


@mail_bp.post('/mail/template')
def mail_template_process():
    file = request.files.get('file')
    mandante_nombre = (request.form.get('mandante_template') or '').strip()
    template_code = (request.form.get('template_code') or '').strip()
    include_crm = request.form.get('include_crm') == 'on'
    template_fecha_raw = (request.form.get('template_fecha') or '').strip()
    crm_fecha_raw = (request.form.get('crm_fecha') or '').strip()
    crm_hora_inicio = (request.form.get('crm_hora_inicio') or '').strip()
    crm_hora_fin = (request.form.get('crm_hora_fin') or '').strip()

    if not file or file.filename == '':
        return _mail_error('Debes subir un archivo Excel.')
    if not mandante_nombre:
        return _mail_error('Debes seleccionar un Mandante.')
    if not template_code:
        return _mail_error('Debes seleccionar una plantilla.')
    if template_code == 'ARAUCANA_ALTERNATIVAS_PAGO_86256':
        if not template_fecha_raw:
            return _mail_error('Debes indicar FECHA_VCTO para La Araucana Alternativas de Pago.')
        try:
            template_fecha = date.fromisoformat(template_fecha_raw)
        except ValueError:
            return _mail_error('La fecha FECHA_VCTO no es valida.')
    else:
        template_fecha = None
    if include_crm:
        crm_rule = _crm_rule_for_mail(mandante_nombre)
        if not crm_rule:
            return _mail_error('Este mandante no sube CRM desde el modulo Mail.')
        if not crm_fecha_raw or not crm_hora_inicio or not crm_hora_fin:
            return _mail_error('Debes indicar fecha, hora inicio y hora fin para generar CRM.')
        try:
            crm_fecha = date.fromisoformat(crm_fecha_raw)
        except ValueError:
            return _mail_error('La fecha de gestion CRM no es valida.')
    else:
        crm_rule = None
        crm_fecha = None

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        salida = build_mail_template(df, template_code, mandante_nombre, template_date=template_fecha)
        nombre = _template_output_name(template_code, mandante_nombre)

        if include_crm and crm_rule and crm_fecha:
            usuario, observacion = crm_rule
            crm_source = _filter_mail_crm_seed_rows(salida)
            crm_df = build_mail_crm_output(
                crm_source,
                fecha=crm_fecha,
                hora_inicio=crm_hora_inicio,
                hora_fin=crm_hora_fin,
                usuario_value=usuario,
                observacion_value=observacion,
                require_operacion=False,
            )
            fecha_salida = datetime.now().strftime('%d-%m-%Y')
            mandante_token = _filename_safe(mandante_nombre)
            template_token = _filename_safe(template_code)
            crm_base = f'cargaCRM_MAIL_{mandante_token}_{template_token}_{fecha_salida}'
            files = [
                (nombre, df_to_xlsx_bytes(salida, sheet_name='PlantillaMail')),
                (f'{crm_base}.xlsx', df_to_xlsx_bytes(crm_df, sheet_name='cargaMailCRM')),
                (f'{crm_base}.csv', crm_df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')),
            ]
            zip_name = f'MAIL_{mandante_token}_{template_token}_{fecha_salida}.zip'
            return send_file(_zip_mail_outputs(files), as_attachment=True, download_name=zip_name, mimetype='application/zip')

        buf = df_to_xlsx_bytesio(salida, sheet_name='PlantillaMail')

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
