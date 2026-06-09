import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file
import re
import unicodedata

from services.mail_templates import MAIL_TEMPLATE_OPTIONS, build_mail_template, sample_mail_template
from services.mandante_rules import apply_mandante_rules
from utils.excel_export import df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

mail_bp = Blueprint('mail', __name__)


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
        nombre = _template_output_name(template_code, mandante_nombre)
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
