import pandas as pd
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file

from services.mail_service import build_mail_crm_output
from services.mail_templates import MAIL_TEMPLATE_OPTIONS, build_mail_template
from services.constants import MANDANTE_CHOICES
from services import db_repos
from utils.excel_export import df_to_xlsx_bytesio

mail_bp = Blueprint('mail', __name__)

@mail_bp.get('/mail')
def mail_page():
    return render_template('mail.html', mandantes=MANDANTE_CHOICES, mail_templates=MAIL_TEMPLATE_OPTIONS)


@mail_bp.post('/mail/template')
def mail_template_process():
    file = request.files.get('file')
    mandante_nombre = (request.form.get('mandante_template') or '').strip()
    template_code = (request.form.get('template_code') or '').strip()

    if not file or file.filename == '':
        flash('Debes subir un archivo Excel.', 'danger')
        return redirect(url_for('mail.mail_page'))
    if not mandante_nombre:
        flash('Debes seleccionar un Mandante.', 'danger')
        return redirect(url_for('mail.mail_page'))
    if not template_code:
        flash('Debes seleccionar una plantilla.', 'danger')
        return redirect(url_for('mail.mail_page'))

    try:
        df = pd.read_excel(file, dtype=str)
        salida = build_mail_template(df, template_code)
        nombre = f'plantilla_{template_code}.xlsx'
        buf = df_to_xlsx_bytesio(salida, sheet_name='PlantillaMail')

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        proceso = db_repos.fetch_proceso_by_codigo('MAIL_CRM') if mandante else None
        if mandante and proceso:
            db_repos.log_masividad(
                mandante_id=mandante.id,
                proceso_id=proceso.id,
                total_registros=len(salida),
                costo_unitario=proceso.costo_unitario,
                usuario_app='mail',
                archivo_generado=nombre,
                observacion=f'Plantilla {template_code}',
                metadata={'template': template_code},
            )

        return send_file(
            buf,
            as_attachment=True,
            download_name=nombre,
            mimetype='application/vnd.openxmlformats-officedocument-spreadsheetml.sheet',
        )
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('mail.mail_page'))
    except Exception as e:
        flash(f'Ocurrió un error procesando el archivo: {e}', 'danger')
        return redirect(url_for('mail.mail_page'))

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
            flash('El intervalo debe ser un entero positivo en segundos.', 'danger')
            return redirect(url_for('mail.mail_page'))

    if not file or file.filename == '':
        flash('Debes subir un archivo Excel.', 'danger')
        return redirect(url_for('mail.mail_page'))
    if not usuario:
        flash('Debes ingresar un Usuario.', 'danger')
        return redirect(url_for('mail.mail_page'))
    if not fecha_str or not hora_inicio or not hora_fin:
        flash('Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.', 'danger')
        return redirect(url_for('mail.mail_page'))

    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
    except ValueError:
        flash('Formato de fecha inválido (usa AAAA-MM-DD).', 'danger')
        return redirect(url_for('mail.mail_page'))

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
        flash(str(e), 'danger')
        return redirect(url_for('mail.mail_page'))
    except Exception as e:
        flash(f'Ocurrió un error procesando el archivo: {e}', 'danger')
        return redirect(url_for('mail.mail_page'))
