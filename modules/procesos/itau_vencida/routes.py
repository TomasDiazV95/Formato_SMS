from __future__ import annotations

from datetime import date, datetime
import io
import re
import unicodedata
import zipfile

import pandas as pd
from flask import Blueprint, request, send_file

from frontend import serve_react_app
from modules.procesos.mail.routes import _filter_mail_crm_seed_rows
from services.itau_vencida_service import build_itau_vencida_outputs
from services.mail_service import build_mail_crm_output
from services.mail_templates import get_template
from services.sms_service import build_crm_output as build_sms_crm_output
from utils import api_error_response
from utils.excel_export import df_to_xlsx_bytes


itau_vencida_bp = Blueprint("itau_vencida", __name__)


MAIL_OUTPUT_TOKENS = {
    "ITAU_VENCIDA_MAIL": "ITAU_VENCIDA_COBRANZA",
    "ITAU_VENCIDA_MAIL_100998": "EMAIL_CAMPANA_ITAU_VIGENTE",
}


def _itau_vencida_error(message: str, status: int = 400):
    return api_error_response(message, "itau_vencida.itau_vencida_page", status=status)


def _filename_token(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "ITAU_VENCIDA"


def _zip_outputs(files: list[tuple[str, bytes]]) -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, payload in files:
            archive.writestr(filename, payload)
    buffer.seek(0)
    return buffer


def _parse_date(raw: str, label: str) -> date:
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"La fecha de {label} no es valida.") from exc


def _append_crm_files(
    files: list[tuple[str, bytes]],
    base_name: str,
    crm_df: pd.DataFrame,
    sheet_name: str,
) -> None:
    files.append((f"{base_name}.xlsx", df_to_xlsx_bytes(crm_df, sheet_name=sheet_name)))
    files.append(
        (
            f"{base_name}.csv",
            crm_df.to_csv(index=False, sep=";", encoding="utf-8-sig").encode("utf-8-sig"),
        )
    )


@itau_vencida_bp.get("/itau-vencida")
def itau_vencida_page():
    return serve_react_app()


@itau_vencida_bp.post("/itau-vencida/generar")
def itau_vencida_process():
    file = request.files.get("file")
    tipo_salida = (request.form.get("tipo_salida") or "").strip().upper()
    include_crm_sms = request.form.get("include_crm_sms") == "on"
    include_crm_mail = request.form.get("include_crm_mail") == "on"

    if not file or file.filename == "":
        return _itau_vencida_error("Debes subir un archivo Excel de origen.")
    if tipo_salida not in {"AXIA", "ATHENAS"}:
        return _itau_vencida_error("Debes seleccionar el formato SMS AXIA o ATHENAS.")

    crm_sms_fecha_raw = (request.form.get("crm_sms_fecha") or "").strip()
    crm_sms_hora_inicio = (request.form.get("crm_sms_hora_inicio") or "").strip()
    crm_sms_hora_fin = (request.form.get("crm_sms_hora_fin") or "").strip()
    crm_mail_fecha_raw = (request.form.get("crm_mail_fecha") or "").strip()
    crm_mail_hora_inicio = (request.form.get("crm_mail_hora_inicio") or "").strip()
    crm_mail_hora_fin = (request.form.get("crm_mail_hora_fin") or "").strip()

    try:
        crm_sms_fecha = None
        crm_mail_fecha = None
        if include_crm_sms:
            if not crm_sms_fecha_raw or not crm_sms_hora_inicio or not crm_sms_hora_fin:
                raise ValueError("Debes indicar fecha, hora inicio y hora fin para CRM SMS.")
            crm_sms_fecha = _parse_date(crm_sms_fecha_raw, "CRM SMS")
        if include_crm_mail:
            if not crm_mail_fecha_raw or not crm_mail_hora_inicio or not crm_mail_hora_fin:
                raise ValueError("Debes indicar fecha, hora inicio y hora fin para CRM Mail.")
            crm_mail_fecha = _parse_date(crm_mail_fecha_raw, "CRM Mail")

        outputs = build_itau_vencida_outputs(file, tipo_salida)
        fecha_salida = datetime.now().strftime("%d-%m-%Y")
        files: list[tuple[str, bytes]] = []

        if outputs.sms_output is not None:
            if tipo_salida == "AXIA":
                sms_name = f"carga_AXIA_SMS_ITAU_VENCIDA_{fecha_salida}.xlsx"
                files.append((sms_name, df_to_xlsx_bytes(outputs.sms_output, sheet_name="Hoja1", header=False)))
                files.append(
                    (
                        sms_name.replace(".xlsx", ".csv"),
                        outputs.sms_output.to_csv(
                            index=False,
                            header=False,
                            sep=";",
                            encoding="utf-8-sig",
                        ).encode("utf-8-sig"),
                    )
                )
            else:
                sms_name = f"cargaAthenas_SMS_ITAU_VENCIDA_{fecha_salida}.xlsx"
                files.append((sms_name, df_to_xlsx_bytes(outputs.sms_output, sheet_name="cargaAthenas")))
        elif include_crm_sms:
            raise ValueError("La base no contiene ninguna de las cuatro masividades SMS de Itaú.")

        for template_code, output in outputs.mail_outputs.items():
            template = get_template(template_code)
            if not template:
                raise ValueError(f"No se encontro la plantilla Mail Itaú: {template_code}.")
            token = MAIL_OUTPUT_TOKENS.get(template_code, _filename_token(template_code))
            name = f"{template.message_id}_{token}_{fecha_salida}.xlsx"
            files.append((name, df_to_xlsx_bytes(output, sheet_name="PlantillaMail")))

        if include_crm_sms and crm_sms_fecha:
            crm_sms = build_sms_crm_output(
                outputs.sms_crm_source,
                usuario="VDAD",
                fecha=crm_sms_fecha,
                hora_inicio=crm_sms_hora_inicio,
                hora_fin=crm_sms_hora_fin,
                observacion="ENVIO SIN RESPUESTA",
            )
            _append_crm_files(
                files,
                f"carga_CRM_SMS_ITAU_VENCIDA_{fecha_salida}",
                crm_sms,
                "cargaCRM",
            )

        if include_crm_mail and crm_mail_fecha:
            if not outputs.mail_outputs:
                raise ValueError("La base no contiene ninguna de las dos masividades Mail de Itaú.")
            mail_source = pd.concat(list(outputs.mail_outputs.values()), ignore_index=True)
            mail_source = _filter_mail_crm_seed_rows(mail_source)
            if mail_source.empty:
                raise ValueError("No quedaron filas Mail validas para generar CRM Mail.")
            crm_mail = build_mail_crm_output(
                mail_source,
                fecha=crm_mail_fecha,
                hora_inicio=crm_mail_hora_inicio,
                hora_fin=crm_mail_hora_fin,
                usuario_value="VDAD",
                observacion_value="ENVIO SIN RESPUESTA",
                require_operacion=False,
            )
            _append_crm_files(
                files,
                f"carga_CRM_MAIL_ITAU_VENCIDA_{fecha_salida}",
                crm_mail,
                "cargaMailCRM",
            )

        if not files:
            raise ValueError("La base no genero ningun archivo de salida.")

        return send_file(
            _zip_outputs(files),
            as_attachment=True,
            download_name=f"ITAU_VENCIDA_{fecha_salida}.zip",
            mimetype="application/zip",
        )
    except ValueError as exc:
        return _itau_vencida_error(str(exc))
    except Exception as exc:
        return _itau_vencida_error(
            f"Ocurrio un error procesando ITAU VENCIDA: {exc}",
            status=500,
        )
