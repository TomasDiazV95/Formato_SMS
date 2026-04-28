# routes/sms.py
import pandas as pd
from datetime import datetime
from flask import Blueprint, request, send_file, abort
from typing import Any
import re
import unicodedata
from pathlib import Path
from difflib import SequenceMatcher

from services.sms_service import (
    build_athenas_output,
    build_axia_output,
    sample_athenas_df,
    sample_axia_df,
)
from services.constants import MANDANTE_CHOICES, COLUMN_MAP
from services.mandante_rules import apply_mandante_rules
from services import db_repos, ejecutivos_repo
from utils.excel_export import df_to_xlsx_bytesio
from utils import api_error_response
from frontend import serve_react_app

sms_bp = Blueprint("sms", __name__)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ITAU_SMS_DIR = PROJECT_ROOT / "SMS_ITAU_VENCIDA"


def _sms_error(message: str, status: int = 400):
    return api_error_response(message, "sms.sms_page", status=status)


def _normalize_key(value: str) -> str:
    return (
        (value or "")
        .strip()
        .lower()
        .replace(" ", "")
        .replace("_", "")
        .replace("-", "")
    )


def _find_column(df: pd.DataFrame, logical: str) -> str | None:
    logical = (logical or "").lower()
    normalized = {_normalize_key(col): col for col in df.columns}
    candidates = {logical}
    if logical in COLUMN_MAP:
        candidates |= {_normalize_key(name) for name in COLUMN_MAP[logical]}
    for candidate in candidates:
        key = _normalize_key(candidate)
        if key in normalized:
            return normalized[key]
    return None


def _build_sms_detalle(df: pd.DataFrame, mensaje: str, tipo_salida: str, mensajes_series: pd.Series | None = None) -> list[dict[str, str | None]]:
    if df is None or df.empty:
        return []
    rut_col = _find_column(df, "rut")
    telefono_col = _find_column(df, "telefono")
    op_col = _find_column(df, "operacion")
    mensajes = None
    if mensajes_series is not None:
        mensajes = (
            mensajes_series.reindex(df.index)
            .fillna("")
            .astype(str)
            .str.strip()
        )
        mensajes = mensajes.where(mensajes != "", mensaje)
    detalles = []
    for idx, row in df.iterrows():
        mensaje_row = mensajes.get(idx, mensaje) if mensajes is not None else mensaje
        detalles.append({
            "rut": str(row.get(rut_col, "")).strip() if rut_col else None,
            "telefono": str(row.get(telefono_col, "")).strip() if telefono_col else None,
            "operacion": str(row.get(op_col, "")).strip() if op_col else None,
            "mensaje": mensaje_row,
            "extra": {"salida": tipo_salida},
        })
    return detalles


ITAU_SMS_TEMPLATE_FILES = {
    "MOROSIDAD": "SMS NORMAL-MOROSIDAD.txt",
    "COMPROMISO_PAGO": "SMS VIGENTE-COMPROMISO DE PAGO.txt",
    "COMPROMISO_ROTO": "SMS VENCIDO-COMPROMISO ROTO.txt",
}

ITAU_SEED_FILE = "SEMILLA ITAU VENCIDA.txt"

ITAU_MASIVIDAD_TO_TEMPLATE = {
    "SMS MOROSIDAD": "MOROSIDAD",
    "SMS COMPROMISO DE PAGO": "COMPROMISO_PAGO",
    "SMS COMPROMISO ROTO": "COMPROMISO_ROTO",
}


def _normalize_spaces(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _ascii_fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    return text.encode("ascii", "ignore").decode("ascii")


def _filename_token(value: str) -> str:
    text = _ascii_fold(_normalize_spaces(value))
    text = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")
    return text or "MANDANTE"


def _find_first_column(df: pd.DataFrame, aliases: set[str]) -> str | None:
    normalized = {_normalize_key(col): col for col in df.columns}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in normalized:
            return normalized[key]
    return None


def _normalize_contact_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if not digits:
        return ""
    if digits.startswith("56"):
        return f"+{digits}"
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return f"+56{digits}"


def _load_itau_sms_template(tipo_sms: str) -> str:
    filename = ITAU_SMS_TEMPLATE_FILES.get((tipo_sms or "").strip().upper())
    if not filename:
        raise ValueError("Tipo de SMS Itaú no soportado.")
    file_path = ITAU_SMS_DIR / filename
    if not file_path.exists():
        raise ValueError(f"No se encontró la plantilla Itaú: {filename}")
    text = file_path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"La plantilla Itaú está vacía: {filename}")
    return text


def _strip_trailing_phone(template_text: str) -> str:
    without_phone = re.sub(r"(?:\+?\d[\d\s\-()]{6,})\s*$", "", template_text or "").strip()
    return without_phone or (template_text or "").strip()


def _resolve_itau_phone(mandante: str, carterizado_name: str) -> str:
    raw = _normalize_spaces(carterizado_name)
    if not raw:
        return ""

    candidates = [
        raw,
        raw.lower(),
        raw.upper(),
        _ascii_fold(raw),
        _ascii_fold(raw).lower(),
        _ascii_fold(raw).upper(),
    ]
    seen: set[str] = set()
    unique_candidates: list[str] = []
    for item in candidates:
        item = _normalize_spaces(item)
        if item and item not in seen:
            seen.add(item)
            unique_candidates.append(item)

    for candidate in unique_candidates:
        ejecutivo = ejecutivos_repo.fetch_by_mandante_and_nombre(mandante, candidate)
        if ejecutivo and ejecutivo.telefono:
            phone = _normalize_contact_phone(ejecutivo.telefono)
            if phone:
                return phone

    target = _ascii_fold(raw).lower().strip()
    if target:
        try:
            best_score = 0.0
            best_phone = ""
            for ejecutivo in ejecutivos_repo.list_ejecutivos(mandante=mandante, activos=True):
                options = [
                    _ascii_fold(ejecutivo.nombre_mostrar or "").lower().strip(),
                    (ejecutivo.nombre_clave or "").replace("_", " ").lower().strip(),
                ]
                for option in options:
                    if not option:
                        continue
                    score = SequenceMatcher(None, target, option).ratio()
                    if score > best_score and ejecutivo.telefono:
                        best_score = score
                        best_phone = _normalize_contact_phone(ejecutivo.telefono)
            if best_score >= 0.92 and best_phone:
                return best_phone
        except Exception:
            pass
    return ""


def _build_itau_carterizado_messages(df: pd.DataFrame, mandante: str) -> pd.Series:
    carterizado_col = _find_first_column(
        df,
        {"carterizado", "carterizado<", "agente", "ejecutivo", "nombre_agente", "nombre agente", "carterizado abril"},
    )
    if not carterizado_col:
        raise ValueError("No se encontró la columna CARTERIZADO/AGENTE en el Excel.")

    masividad_col = _find_first_column(df, {"masividad", "tipo_sms", "tipo sms", "gestion", "gestion"})
    if not masividad_col:
        raise ValueError("No se encontró la columna MASIVIDAD en el Excel de Itaú.")

    template_cache: dict[str, str] = {}

    def _normalize_masividad(value: str) -> str:
        text = _ascii_fold(_normalize_spaces(value)).upper()
        text = re.sub(r"\s+", " ", text)
        return text

    def _template_text_from_masividad(value: str) -> str:
        key = ITAU_MASIVIDAD_TO_TEMPLATE.get(_normalize_masividad(value))
        if not key:
            return ""
        if key not in template_cache:
            template_cache[key] = _strip_trailing_phone(_load_itau_sms_template(key))
        return template_cache[key]

    phones: list[str] = []
    templates: list[str] = []
    missing: list[str] = []
    invalid_masividades: list[str] = []

    raw_carterizados = df[carterizado_col].fillna("").astype(str).tolist()
    raw_masividades = df[masividad_col].fillna("").astype(str).tolist()
    for raw_name, raw_masividad in zip(raw_carterizados, raw_masividades):
        template_text = _template_text_from_masividad(raw_masividad)
        templates.append(template_text)
        if not template_text:
            invalid_masividades.append(_normalize_spaces(raw_masividad) or "(vacío)")
            phones.append("")
            continue

        carterizado = _normalize_spaces(raw_name)
        phone = _resolve_itau_phone(mandante, carterizado)
        phones.append(phone)
        if not phone:
            missing.append(carterizado or "(vacío)")

    if invalid_masividades:
        uniq_invalid = []
        for item in invalid_masividades:
            if item not in uniq_invalid:
                uniq_invalid.append(item)
        only_invalid = all(not t for t in templates)
        if only_invalid:
            raise ValueError(
                "No se encontraron valores de MASIVIDAD válidos para SMS Itaú. "
                f"Valores detectados: {', '.join(uniq_invalid[:8])}"
            )

    if missing:
        # No se bloquea todo el proceso: filas sin match quedan vacías y se filtran en el flujo.
        # Si todas las filas quedan sin teléfono, se informa error.
        pass

    messages = [f"{tpl} {phone}".strip() if tpl and phone else "" for tpl, phone in zip(templates, phones)]
    if not any(messages):
        uniq = []
        for name in missing:
            if name not in uniq:
                uniq.append(name)
        preview = ", ".join(uniq[:8])
        extra = "" if len(uniq) <= 8 else f" ... (+{len(uniq) - 8} más)"
        raise ValueError(
            "No se encontró teléfono de ejecutivo para los carterizados del archivo. "
            f"Ejemplos: {preview}{extra}. Revisa ejecutivos_phoenix/alias para Itau Vencida."
        )
    return pd.Series(messages, index=df.index)


def _seed_type_from_message(message: str) -> str | None:
    text = _ascii_fold(_normalize_spaces(message)).upper()
    if not text:
        return None
    if "MORA" in text:
        return "MOROSIDAD"
    if "PROXIMO" in text and "VENC" in text:
        return "COMPROMISO_PAGO"
    if "PENDIENTE" in text:
        return "COMPROMISO_ROTO"
    return None


def _load_itau_seed_rows() -> list[dict[str, str]]:
    seed_path = ITAU_SMS_DIR / ITAU_SEED_FILE
    if not seed_path.exists():
        return []

    rows: list[dict[str, str]] = []
    for raw_line in seed_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if "\t" in line:
            phone_raw, msg_raw = line.split("\t", 1)
        else:
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                continue
            phone_raw, msg_raw = parts[0], parts[1]
        digits = re.sub(r"\D", "", phone_raw or "")
        if not digits:
            continue
        seed_type = _seed_type_from_message(msg_raw)
        if not seed_type:
            continue
        rows.append({
            "seed_type": seed_type,
            "phone_local": digits,
            "message": _normalize_spaces(msg_raw),
        })
    return rows


def _prepend_itau_seed_rows(
    carga: pd.DataFrame,
    tipo_salida: str,
    mensaje_series: pd.Series,
) -> tuple[pd.DataFrame, int]:
    seeds = _load_itau_seed_rows()
    if not seeds:
        return carga, 0

    target_types = {
        seed_type
        for seed_type in mensaje_series.fillna("").astype(str).map(_seed_type_from_message).tolist()
        if seed_type
    }
    if not target_types:
        return carga, 0

    selected = [row for row in seeds if row["seed_type"] in target_types]
    if not selected:
        return carga, 0

    base = carga.copy()
    # En modo Itaú se ignoran semillas hardcodeadas del sistema.
    if tipo_salida == "AXIA":
        if not base.empty and str(base.iloc[0].get("FONO", "")).strip() == "976900353":
            base = base.iloc[1:].copy()
        seed_df = pd.DataFrame(
            [{"FONO": row["phone_local"], "MENSAJE": row["message"]} for row in selected]
        )
        final_df = pd.concat([seed_df, base], ignore_index=True)
        return final_df, len(seed_df)

    if "ID_CLIENTE (RUT)" in base.columns:
        if not base.empty and str(base.iloc[0].get("ID_CLIENTE (RUT)", "")).strip().upper() == "PRB":
            base = base.iloc[1:].copy()
    seed_df = pd.DataFrame(
        [
            {
                "TELEFONO": f"56{row['phone_local']}",
                "MENSAJE": row["message"],
                "ID_CLIENTE (RUT)": "PRB",
                "OPCIONAL": " ",
                "CAMPO1": " ",
                "CAMPO2": " ",
                "CAMPO3": " ",
            }
            for row in selected
        ]
    )
    final_df = pd.concat([seed_df, base], ignore_index=True)
    return final_df, len(seed_df)


@sms_bp.get("/")
def main():
    return serve_react_app()


@sms_bp.get("/procesos")
def procesos_menu():
    return serve_react_app()


@sms_bp.get("/cargas")
def cargas_menu():
    return serve_react_app()

@sms_bp.get("/sms")
def sms_page():
    return serve_react_app()

@sms_bp.get("/sms/sample/<tipo>")
def sms_sample(tipo: str):
    tipo = (tipo or "").upper()
    if tipo == "ATHENAS":
        df = sample_athenas_df()
        sheet = "cargaAthenas"
        name = "ejemplo_SMS_ATHENAS.xlsx"
        header = True
    elif tipo == "AXIA":
        df = sample_axia_df()
        sheet = "Hoja1"
        name = "ejemplo_SMS_AXIA.xlsx"
        header = False
    else:
        abort(404)

    buf = df_to_xlsx_bytesio(df, sheet_name=sheet, header=header)
    return send_file(
        buf,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

@sms_bp.post("/sms/athenas")
def sms_athenas_process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    tipo_salida = (request.form.get("tipo_salida") or "").strip().upper()
    mandante_nombre = (request.form.get("mandante") or "").strip()
    mensajes_personalizados = request.form.get("mensajes_personalizados") == "on"
    modo_carterizado_itau = request.form.get("modo_carterizado_itau") == "on"

    if not file or file.filename == "":
        return _sms_error("Debes subir un archivo Excel.")
    if not mensaje and not mensajes_personalizados and not modo_carterizado_itau:
        return _sms_error("Debes ingresar un Mensaje.")
    if not tipo_salida:
        return _sms_error("Debes escoger un formato de salida.")
    if not mandante_nombre:
        return _sms_error("Debes seleccionar un Mandante.")
    if modo_carterizado_itau and mandante_nombre.lower() != "itau vencida":
        return _sms_error("El modo carterizado Itaú solo está habilitado para mandante Itau Vencida.")

    try:
        df = pd.read_excel(file, dtype=str)
        df = apply_mandante_rules(df, mandante_nombre)
        mensaje_series = None
        descartadas = 0
        seed_count = 0
        if modo_carterizado_itau:
            mensaje_series = _build_itau_carterizado_messages(df, mandante_nombre)
            valid_mask = mensaje_series.fillna("").astype(str).str.strip() != ""
            descartadas = int((~valid_mask).sum())
            if not valid_mask.any():
                return _sms_error("No hay filas SMS válidas para generar salida Itaú (revisa MASIVIDAD).")
            df = df.loc[valid_mask].copy()
            mensaje_series = mensaje_series.loc[valid_mask].copy()
            mensaje = "SMS ITAU CARTERIZADO"
            mensajes_personalizados = True
        elif mensajes_personalizados:
            mensaje_col = _find_column(df, "mensaje")
            if not mensaje_col:
                return _sms_error("Activaste múltiples mensajes pero no existe una columna 'Mensaje' en el archivo.")
            mensaje_series = df[mensaje_col].fillna("").astype(str).str.strip()
            if mensaje_series.eq("").all() and not mensaje:
                return _sms_error("La columna 'Mensaje' está vacía y no ingresaste un mensaje base.")
            if not mensaje:
                primera = mensaje_series[mensaje_series != ""]
                if primera.empty:
                    return _sms_error("No hay mensajes válidos en la columna 'Mensaje'.")
                mensaje = primera.iloc[0]
            mensaje_series = mensaje_series.where(mensaje_series != "", mensaje)

        fecha_actual = datetime.now().strftime("%d-%m")

        mandante = db_repos.fetch_mandante_by_nombre(mandante_nombre)
        if not mandante:
            return _sms_error("Mandante no encontrado en catálogo.")

        mandante_token = _filename_token(mandante.nombre)

        if tipo_salida == "AXIA":
            carga = build_axia_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            if modo_carterizado_itau and mensaje_series is not None:
                carga, seed_count = _prepend_itau_seed_rows(carga, tipo_salida, mensaje_series)
            proceso_codigo = "SMS_AXIA"
            buf = df_to_xlsx_bytesio(carga, sheet_name="Hoja1", header=False)
            nombre = f"carga_AXIA_SMS_{mandante_token}_{fecha_actual}.xlsx"
        else:
            carga = build_athenas_output(df, mensaje=mensaje, mensajes_series=mensaje_series if mensajes_personalizados else None)
            if modo_carterizado_itau and mensaje_series is not None:
                carga, seed_count = _prepend_itau_seed_rows(carga, tipo_salida, mensaje_series)
            proceso_codigo = "SMS_ATHENAS"
            buf = df_to_xlsx_bytesio(carga, sheet_name="cargaAthenas")
            nombre = f"cargaAthenas_SMS_{mandante_token}_{fecha_actual}.xlsx"

        proceso = db_repos.fetch_proceso_by_codigo(proceso_codigo)
        if not proceso:
            return _sms_error("No se logró identificar el proceso para registrar costos.", status=500)

        total_registros = max(len(carga) - 1, 0)
        metadata: dict[str, Any] = {"formato": tipo_salida}
        if mensajes_personalizados:
            metadata["mensajes_personalizados"] = True
        if modo_carterizado_itau:
            metadata["modo_carterizado_itau"] = True
            metadata["origen_tipo_sms"] = "MASIVIDAD"
            if descartadas > 0:
                metadata["filas_descartadas"] = descartadas
            if seed_count > 0:
                metadata["seed_rows"] = seed_count
        masividad_id = db_repos.log_masividad(
            mandante_id=mandante.id,
            proceso_id=proceso.id,
            total_registros=total_registros,
            costo_unitario=proceso.costo_unitario,
            usuario_app="sms",
            archivo_generado=nombre,
            observacion=mensaje,
            metadata=metadata,
        )

        detalles = _build_sms_detalle(
            df,
            mensaje,
            tipo_salida,
            mensaje_series if mensajes_personalizados else None,
        )
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
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    except Exception as e:
        return _sms_error(f"Ocurrió un error procesando el archivo: {e}", status=500)
