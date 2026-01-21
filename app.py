
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
from datetime import datetime, date, time, timedelta
import io
import zipfile
import tempfile
import os
import re
import numpy as np
from itertools import cycle


app = Flask(__name__)
app.secret_key = "123456"

REQUIRED_COLUMNS = {"RUT", "OP", "FONO"}

def build_outputs(df: pd.DataFrame, mensaje: str, usuario: str):
    # Normaliza columnas esperadas
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en el Excel: {', '.join(sorted(missing))}")

    # Copia para no mutar el original
    df = df.copy()

    # Inputs -> columnas
    df["MENSAJE"] = mensaje
    df["USERNAME"] = usuario

    # FONO_2: "56" + FONO como string (asegurando sin .0 si venía como número)
    df["FONO"] = df["FONO"].astype(str).str.replace(r"\.0$", "", regex=True)
    df["FONO_2"] = "56" + df["FONO"]

    # ---------------------------
    # Carga CRM
    # ---------------------------
    cargaCRM_df = pd.DataFrame(columns=[
        "RUT", "NRO_DOCUMENTO", "FECHA_GESTION", "TELEFONO",
        "OBSERVACION", "USUARIO", "CORREO"
    ])

    df1 = df[["RUT", "OP", "FONO", "USERNAME"]].rename(columns={
        "OP": "NRO_DOCUMENTO",
        "FONO": "TELEFONO",
        "USERNAME": "USUARIO"
    })

    cargaCRM_df = pd.concat([cargaCRM_df, df1], ignore_index=True)
    cargaCRM_df["OBSERVACION"] = "ACCIONES COMERCIALES"

    # Fecha de gestión: hoy a las 10:00:00
    fecha_gestion = datetime.combine(date.today(), time(10, 0, 0))
    cargaCRM_df["FECHA_GESTION"] = fecha_gestion

    # Asegurar NRO_DOCUMENTO como texto
    cargaCRM_df["NRO_DOCUMENTO"] = cargaCRM_df["NRO_DOCUMENTO"].astype(str)

    cargaCRM_df["CORREO"] = " "

    # ---------------------------
    # Carga Athenas
    # ---------------------------
    cargaAthenas_df = pd.DataFrame(columns=[
        "TELEFONO", "MENSAJE", "ID_CLIENTE (RUT)", "OPCIONAL",
        "CAMPO1", "CAMPO2", "CAMPO3"
    ])

    df2 = df[["RUT", "FONO_2", "MENSAJE"]].rename(columns={
        "FONO_2": "TELEFONO",
        "RUT": "ID_CLIENTE (RUT)"
    })

    cargaAthenas_df = pd.concat([cargaAthenas_df, df2], ignore_index=True)
    cargaAthenas_df["OPCIONAL"] = " "
    cargaAthenas_df["CAMPO1"] = " "
    cargaAthenas_df["CAMPO2"] = " "
    cargaAthenas_df["CAMPO3"] = " "

    return cargaCRM_df, cargaAthenas_df

def reemplazarComa(nombreColumna, dataFrame):
    for i in range(len(dataFrame)):
        if "," in dataFrame.loc[i, nombreColumna]:
            dataFrame.loc[i, nombreColumna] = dataFrame.loc[i, nombreColumna].replace(',', '.')

CAMP_COLS = ["campana_1", "campana_2", "campana_3", "campana_4", "campana_5"]

def asegurar_columnas_campana(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in CAMP_COLS:
        if col not in df.columns:
            df[col] = ""
    return df

def copiar_campanas_por_operacion(
    df_nuevo: pd.DataFrame,
    df_antiguo: pd.DataFrame,
    col_operacion: str = "Agreement Number "
) -> pd.DataFrame:
    """
    Copia campana_1..campana_5 desde df_antiguo a df_nuevo usando match por col_operacion.
    - Prioriza campañas del antiguo si hay match.
    - Mantiene filas y orden del df_nuevo.
    """
    df_nuevo = df_nuevo.copy()
    df_nuevo = asegurar_columnas_campana(df_nuevo)
    df_antiguo = asegurar_columnas_campana(df_antiguo)

    if col_operacion not in df_nuevo.columns:
        raise ValueError(f"El archivo nuevo no contiene la columna de operación: {col_operacion}")
    if col_operacion not in df_antiguo.columns:
        raise ValueError(f"El archivo antiguo no contiene la columna de operación: {col_operacion}")

    # Normaliza operación a string para evitar mismatch por números vs texto
    df_nuevo[col_operacion] = df_nuevo[col_operacion].astype(str).str.strip()
    df_antiguo[col_operacion] = df_antiguo[col_operacion].astype(str).str.strip()

    # Lookup desde antiguo (operación + campañas), sin duplicados por operación
    lookup = df_antiguo[[col_operacion] + CAMP_COLS].copy()
    lookup = lookup.drop_duplicates(subset=[col_operacion], keep="first")
    lookup = lookup.rename(columns={c: f"{c}_old" for c in CAMP_COLS})

    # Merge para traer campañas del antiguo como *_old
    merged = df_nuevo.merge(lookup, on=col_operacion, how="left")

    # Copia campañas: si hay valor en *_old, úsalo; si no, conserva el del nuevo
    for c in CAMP_COLS:
        merged[c] = merged[f"{c}_old"].combine_first(merged[c])
        merged.drop(columns=[f"{c}_old"], inplace=True)

    return merged

MASIVIDAD_COLUMNS = [
    'INSTITUCIÓN','SEGMENTOINSTITUCIÓN','message_id','NOMBRE','RUT','OPERACION',
    'FECHA_VENCIMIENTO_CUOTA','MONTO_CUOTA','FECHA_ARCHIVO','FONO_EJECUTIVA',
    'FECHA_ENTREGA','dest_email','name_from','mail_from','CORREO_EJECUTIVA'
]

EJECUTIVOS = [
    {"name_from": "Daniela Cañicul", "CORREO_EJECUTIVA": "dcanicul@phoenixservice.cl", "mail_from": "dcanicul@info.phoenixserviceinfo.cl"},
    {"name_from": "Paula Alarcon",   "CORREO_EJECUTIVA": "palarcon@phoenixservice.cl", "mail_from": "palarcon@info.phoenixserviceinfo.cl"},
    {"name_from": "Claudia Sandoval","CORREO_EJECUTIVA": "csandoval@phoenixservice.cl","mail_from": "csandoval@info.phoenixserviceinfo.cl"},
    {"name_from": "Erika Alderete",  "CORREO_EJECUTIVA": "Ealderete@phoenixservice.cl","mail_from": "Ealderete@info.phoenixserviceinfo.cl"},
    {"name_from": "Yessenia Salinas","CORREO_EJECUTIVA": "ysalinas@phoenixservice.cl", "mail_from": "ysalinas@info.phoenixserviceinfo.cl"},
    {"name_from": "Paulina Ortiz",   "CORREO_EJECUTIVA": "portiz@phoenixservice.cl",  "mail_from": "portiz@estandar.phoenixserviceinfo.cl"},
    {"name_from": "Pamela Alamos",   "CORREO_EJECUTIVA": "palamos@phoenixservice.cl", "mail_from": "palamos@info.phoenixserviceinfo.cl"},
    {"name_from": "Luis Toledo",     "CORREO_EJECUTIVA": "ltoledo@phoenixservice.cl", "mail_from": "ltoledo@info.phoenixserviceinfo.cl"},
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Quita espacios extremos y normaliza múltiples espacios
    df = df.copy()
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df

def _rut_only_numbers(series: pd.Series) -> pd.Series:
    # Acepta "12345678-9" o "12.345.678-9" o "12345678"
    s = series.astype(str).str.strip()
    s = s.str.replace(".", "", regex=False)
    s = s.str.split("-").str[0]
    s = s.str.replace(r"\D+", "", regex=True)
    return s

def construir_df_masividad(df_nuevo: pd.DataFrame) -> pd.DataFrame:
    # OJO: NO normalizamos columnas, porque el Excel viene con espacios al final
    required_map = {
        "National Id ": "RUT",
        "Customer Name ": "NOMBRE",
        "Agreement Number ": "OPERACION",
        "Due Date": "FECHA_VENCIMIENTO_CUOTA",
        "EMI": "MONTO_CUOTA",
        "Email ": "dest_email",
    }

    missing = [c for c in required_map.keys() if c not in df_nuevo.columns]
    if missing:
        raise ValueError(
            "Faltan columnas para masividades en el archivo: "
            + ", ".join(missing)
            + ". (Ojo: este layout viene con espacios al final en las cabeceras)."
        )

    df_m = pd.DataFrame(index=df_nuevo.index, columns=MASIVIDAD_COLUMNS)

    df_m["RUT"] = _rut_only_numbers(df_nuevo["National Id "])
    df_m["NOMBRE"] = df_nuevo["Customer Name "].astype(str).str.strip()
    df_m["OPERACION"] = df_nuevo["Agreement Number "].astype(str).str.strip()
    df_m["FECHA_VENCIMIENTO_CUOTA"] = df_nuevo["Due Date"]
    df_m["MONTO_CUOTA"] = df_nuevo["EMI"]
    df_m["dest_email"] = df_nuevo["Email "].astype(str).str.strip()

    hoy = datetime.now().strftime("%d-%m-%Y")
    df_m["FECHA_ENTREGA"] = hoy
    df_m["FECHA_ARCHIVO"] = hoy
    df_m["FECHA_VENCIMIENTO_CUOTA"] = pd.to_datetime(df_m["FECHA_VENCIMIENTO_CUOTA"], errors='coerce').dt.strftime("%d-%m-%Y")
    # Limpiezas básicas
    df_m = df_m.dropna(subset=["dest_email"])
    df_m = df_m[df_m["dest_email"].astype(str).str.strip() != ""]
    df_m = df_m[df_m["dest_email"].astype(str).str.match(EMAIL_RE, na=False)]

    df_m = df_m[df_m["RUT"].astype(str).str.len() >= 7]
    df_m = df_m.drop_duplicates(subset=["RUT"], keep="first")

    # Fijos
    df_m = df_m.assign(
        **{
            "INSTITUCIÓN": "GENERAL MOTORS",
            "SEGMENTOINSTITUCIÓN": "GENERAL MOTORS",
            "message_id": 84995,
            "FONO_EJECUTIVA": 228400433,
        }
    )

    # Asignación ejecutivos
    cyc = cycle(EJECUTIVOS)
    asignados = [next(cyc) for _ in range(len(df_m))]
    df_m["name_from"] = [a["name_from"] for a in asignados]
    df_m["CORREO_EJECUTIVA"] = [a["CORREO_EJECUTIVA"] for a in asignados]
    df_m["mail_from"] = [a["mail_from"] for a in asignados]

    return df_m[MASIVIDAD_COLUMNS]

    columnasMasividad = [
        'INSTITUCIÓN','SEGMENTOINSTITUCIÓN','message_id','NOMBRE','RUT','OPERACION',
        'FECHA_VENCIMIENTO_CUOTA','MONTO_CUOTA','FECHA_ARCHIVO','FONO_EJECUTIVA',
        'FECHA_ENTREGA','dest_email','name_from','mail_from','CORREO_EJECUTIVA'
    ]

    # Crea DF con columnas
    df_masividad = pd.DataFrame(columns=columnasMasividad)

    # Validaciones mínimas (para que falle con mensaje claro si falta algo)
    """ required = ['RUT - DV', 'NOMBRE', 'Nro_Documento', 'AD9', 'AD6', 'EMAIL1']
    missing = [c for c in required if c not in nuevo_df.columns]
    if missing:
        raise ValueError(f"Faltan columnas para masividades en el archivo nuevo: {', '.join(missing)}")
 """
    # Mapeos
    df_masividad['RUT'] = nuevo_df['National Id '].astype(str).str.split('-').str[0]
    df_masividad['NOMBRE'] = nuevo_df['Customer Name ']
    df_masividad['OPERACION'] = nuevo_df['Agreement Number']
    df_masividad['FECHA_VENCIMIENTO_CUOTA'] = nuevo_df['Due Date']
    df_masividad['MONTO_CUOTA'] = nuevo_df['EMI']
    df_masividad['dest_email'] = nuevo_df['Email ']

    hoy = datetime.now().strftime('%d-%m-%Y')
    df_masividad['FECHA_ENTREGA'] = hoy
    df_masividad['FECHA_ARCHIVO'] = hoy

    # Eliminar filas vacías o NaN en dest_email
    df_masividad = df_masividad.dropna(subset=['dest_email'])
    df_masividad = df_masividad[df_masividad['dest_email'].astype(str).str.strip() != '']

    # Eliminar duplicados por RUT
    df_masividad = df_masividad.drop_duplicates(subset=['RUT'], keep='first')

    # Asignaciones fijas
    df_masividad = df_masividad.assign(
        INSTITUCIÓN='GENERAL MOTORS',
        SEGMENTOINSTITUCIÓN='GENERAL MOTORS',
        message_id=84995,
        FONO_EJECUTIVA=228400433
    )

    # Listas de ejecutivos
    nombres_ejecutivos = [
        'Daniela Cañicul', 'Paula Alarcon', 'Claudia Sandoval', 'Erika Alderete',
        'Yessenia Salinas', 'Paulina Ortiz', 'Pamela Alamos', 'Luis Toledo'
    ]

    correos_ejecutivos = [
        'dcanicul@phoenixservice.cl', 'palarcon@phoenixservice.cl', 'csandoval@phoenixservice.cl', 'Ealderete@phoenixservice.cl',
        'ysalinas@phoenixservice.cl', 'portiz@phoenixservice.cl', 'palamos@phoenixservice.cl', 'ltoledo@phoenixservice.cl'
    ]

    correos_masivos = [
        'dcanicul@info.phoenixserviceinfo.cl', 'palarcon@info.phoenixserviceinfo.cl', 'csandoval@info.phoenixserviceinfo.cl', 'Ealderete@info.phoenixserviceinfo.cl',
        'ysalinas@info.phoenixserviceinfo.cl', 'portiz@estandar.phoenixserviceinfo.cl', 'palamos@info.phoenixserviceinfo.cl', 'ltoledo@info.phoenixserviceinfo.cl'
    ]

    # Asignación cíclica
    df_masividad['name_from'] = np.resize(nombres_ejecutivos, len(df_masividad))
    df_masividad['CORREO_EJECUTIVA'] = np.resize(correos_ejecutivos, len(df_masividad))
    df_masividad['mail_from'] = np.resize(correos_masivos, len(df_masividad))

    return df_masividad

@app.route("/", methods=["GET"])
def index():
    return render_template("main.html")

@app.route("/sms", methods=["GET"])
def sms_page():
    # Tu página actual (index.html)
    return render_template("index.html")

@app.route("/sms/process", methods=["POST"])
def process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    usuario = (request.form.get("usuario") or "").strip()

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("sms_page"))

    if not mensaje:
        flash("Debes ingresar un Mensaje.", "danger")
        return redirect(url_for("sms_page"))

    if not usuario:
        flash("Debes ingresar un Usuario.", "danger")
        return redirect(url_for("sms_page"))

    try:
        # Lee Excel
        df = pd.read_excel(file)

        # Construye salidas
        cargaCRM_df, cargaAthenas_df = build_outputs(df, mensaje, usuario)

        # Nombres de archivos
        fecha_actual = datetime.now().strftime("%d-%m")
        name1 = f"cargaCRM_{fecha_actual}_.xlsx"
        name2 = f"cargaAthenas_{fecha_actual}_.xlsx"

        # Escribe ambos a memoria y empaqueta ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            buf1 = io.BytesIO()
            with pd.ExcelWriter(buf1, engine="openpyxl") as writer:
                cargaCRM_df.to_excel(writer, index=False, sheet_name="cargaCRM")
            z.writestr(name1, buf1.getvalue())

            buf2 = io.BytesIO()
            with pd.ExcelWriter(buf2, engine="openpyxl") as writer:
                cargaAthenas_df.to_excel(writer, index=False, sheet_name="cargaAthenas")
            z.writestr(name2, buf2.getvalue())

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=f"salidas_{fecha_actual}.zip",
            mimetype="application/zip"
        )

    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("sms_page"))
    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("sms_page"))

@app.route("/cargaGM", methods=["GET", "POST"])
def gm_page():
    if request.method == "POST":
        try:
            # Switches
            comparar = request.form.get("habilitar_comparacion") == "on"
            masividades = request.form.get("habilitar_masividades") == "on"

            # -----------------------------
            # Archivo NUEVO (obligatorio)
            # -----------------------------
            archivo = request.files.get("archivo")
            if not archivo:
                flash("Debes subir el archivo Collection (Nuevo).", "danger")
                return render_template("cargagm.html")

            nuevo_df = pd.read_excel(archivo)
            nuevo_df = asegurar_columnas_campana(nuevo_df)

            # -----------------------------
            # Si comparar: copiar campañas por operación (Nro_Documento)
            # -----------------------------
            if comparar:
                archivo_ant = request.files.get("archivo_anterior")
                if not archivo_ant:
                    flash("Activaste comparación, pero falta subir el archivo antiguo.", "danger")
                    return render_template("cargagm.html")

                df_antiguo = pd.read_excel(archivo_ant)
                nuevo_df = copiar_campanas_por_operacion(nuevo_df, df_antiguo, col_operacion="Agreement Number ")
                flash("Campañas copiadas desde el archivo antiguo usando operación (Agreement Number ).", "success")

            # -----------------------------
            # Tu lógica de formateo original
            # -----------------------------
            # (Si estas columnas a veces cambian, dímelo y lo hacemos robusto)
            nuevo_df['POS/Curr. Acc. Bal.* '] = nuevo_df['POS/Curr. Acc. Bal.* '].astype(str)
            nuevo_df['EMI'] = nuevo_df['EMI'].astype(str)

            nuevo_df['POS/Curr. Acc. Bal.* '] = nuevo_df['POS/Curr. Acc. Bal.* '].apply(
                lambda x: '{:,.0f}'.format(float(str(x).replace(',', '')))
            )
            nuevo_df['EMI'] = nuevo_df['EMI'].apply(
                lambda x: '{:,.0f}'.format(float(str(x).replace(',', '')))
            )

            reemplazarComa('EMI', nuevo_df)
            reemplazarComa('POS/Curr. Acc. Bal.* ', nuevo_df)

            fecha_actual = datetime.now().strftime("%d-%m")

            # -----------------------------
            # Excel principal (final)
            # -----------------------------
            archivo_excel = f"ARCHIVO COLLECTION {fecha_actual}.xlsx"
            nuevo_df.to_excel(archivo_excel, index=False)

            # -----------------------------
            # Masividades (opcional)
            # -----------------------------
            archivo_masividades = None
            if masividades:
                df_m = construir_df_masividad(nuevo_df)
                archivo_masividades = f"MASIVIDADES {fecha_actual}.xlsx"
                df_m.to_excel(archivo_masividades, index=False)

            # -----------------------------
            # ZIP final
            # -----------------------------
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
                with zipfile.ZipFile(temp_zip.name, "w") as zipf:
                    zipf.write(archivo_excel)
                    if archivo_masividades:
                        zipf.write(archivo_masividades)

                # Limpieza archivos sueltos
                for f in [archivo_excel, archivo_masividades]:
                    if f and os.path.exists(f):
                        try:
                            os.remove(f)
                        except:
                            pass

                return send_file(
                    temp_zip.name,
                    as_attachment=True,
                    download_name=f"Procesamiento_GM_{fecha_actual}.zip"
                )

        except Exception as e:
            flash(f"Error al procesar: {str(e)}", "danger")
            return render_template("cargagm.html")

    return render_template("cargagm.html")
    if request.method == "POST":
        try:
            # Switches
            comparar = request.form.get("habilitar_comparacion") == "on"
            masividades = request.form.get("habilitar_masividades") == "on"

            # -----------------------------
            # Archivo NUEVO (obligatorio)
            # -----------------------------
            archivo = request.files.get("archivo")
            if not archivo:
                flash("Debes subir el archivo Collection (Nuevo).", "danger")
                return render_template("cargagm.html")

            nuevo_df = pd.read_excel(archivo)

            # Asegura columnas de campañas
            nuevo_df = asegurar_columnas_campana(nuevo_df)

            # -----------------------------
            # Tu lógica de formateo original
            # -----------------------------
            nuevo_df['POS/Curr. Acc. Bal.* '] = nuevo_df['POS/Curr. Acc. Bal.* '].astype(str)
            nuevo_df['EMI'] = nuevo_df['EMI'].astype(str)

            nuevo_df['POS/Curr. Acc. Bal.* '] = nuevo_df['POS/Curr. Acc. Bal.* '].apply(
                lambda x: '{:,.0f}'.format(float(x.replace(',', '')))
            )
            nuevo_df['EMI'] = nuevo_df['EMI'].apply(
                lambda x: '{:,.0f}'.format(float(x.replace(',', '')))
            )

            reemplazarComa('EMI', nuevo_df)
            reemplazarComa('POS/Curr. Acc. Bal.* ', nuevo_df)

            fecha_actual = datetime.now().strftime("%d-%m")

            # -----------------------------
            # Excel principal
            # -----------------------------
            archivo_excel = f"ARCHIVO COLLECTION {fecha_actual}.xlsx"
            nuevo_df.to_excel(archivo_excel, index=False)

            # -----------------------------
            # Comparación (opcional)
            # -----------------------------
            archivo_campanas_nuevas = None
            if comparar:
                archivo_ant = request.files.get("archivo_anterior")
                if not archivo_ant:
                    flash("Activaste comparación, pero falta subir el archivo antiguo.", "danger")
                    return render_template("cargagm.html")

                df_antiguo = pd.read_excel(archivo_ant)
                df_antiguo = asegurar_columnas_campana(df_antiguo)

                camp_old = extraer_campanas(df_antiguo)
                camp_new = extraer_campanas(nuevo_df)

                nuevas = sorted(list(camp_new - camp_old))
                df_nuevas = pd.DataFrame({"campana_nueva": nuevas})

                archivo_campanas_nuevas = f"CAMPANAS_NUEVAS {fecha_actual}.xlsx"
                df_nuevas.to_excel(archivo_campanas_nuevas, index=False)

            # -----------------------------
            # Masividades (opcional)
            # -----------------------------
            archivo_masividades = None
            if masividades:
                df_m = construir_df_masividad(nuevo_df)
                archivo_masividades = f"MASIVIDADES {fecha_actual}.xlsx"
                df_m.to_excel(archivo_masividades, index=False)

            # -----------------------------
            # ZIP final
            # -----------------------------
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
                with zipfile.ZipFile(temp_zip.name, "w") as zipf:
                    zipf.write(archivo_excel)

                    if archivo_campanas_nuevas:
                        zipf.write(archivo_campanas_nuevas)

                    if archivo_masividades:
                        zipf.write(archivo_masividades)

                # Limpieza archivos sueltos
                for f in [archivo_excel, archivo_campanas_nuevas, archivo_masividades]:
                    if f and os.path.exists(f):
                        os.remove(f)

                return send_file(
                    temp_zip.name,
                    as_attachment=True,
                    download_name=f"Procesamiento_GM_{fecha_actual}.zip"
                )

        except Exception as e:
            flash(f"Error al procesar: {str(e)}", "danger")
            return render_template("cargagm.html")

    return render_template("cargagm.html")

@app.route("/gm_masividades", methods=["GET", "POST"])
def gm_masividades():
    try:
        if request.method == "GET":
            # Renderiza tu template donde tienes el input file
            return render_template("cargagm.html")

        # POST
        if "file" not in request.files:
            raise ValueError("No se recibió archivo (input name='file').")

        f = request.files["file"]
        if not f or f.filename.strip() == "":
            raise ValueError("Archivo vacío o sin nombre.")

        # Lee excel
        nuevo_df = pd.read_excel(f)

        # Construye masividad
        df_m = construir_df_masividad(nuevo_df)

        # Exporta a XLSX en memoria
        fecha_actual = datetime.now().strftime("%Y-%m-%d")
        xlsx_name = f"MASIVIDADES_GM_{fecha_actual}.xlsx"

        xlsx_bytes = io.BytesIO()
        with pd.ExcelWriter(xlsx_bytes, engine="openpyxl") as writer:
            df_m.to_excel(writer, index=False, sheet_name="MASIVIDAD")
        xlsx_bytes.seek(0)

        # Comprime a ZIP en memoria
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(xlsx_name, xlsx_bytes.getvalue())
        zip_bytes.seek(0)

        return send_file(
            zip_bytes,
            as_attachment=True,
            download_name=f"Masividades_GM_{fecha_actual}.zip",
            mimetype="application/zip",
        )

    except Exception as e:
        flash(f"No se pudo generar masividades: {str(e)}", "danger")
        return render_template("cargagm.html")

# =========================
# FUNCIONALIDADES IVR + CRM
# =========================

POSSIBLE_NAMES = {
    "TELEFONO": {"telefono", "teléfono", "fono", "celular", "movil", "móvil", "telefono1"},
    "RUT": {"rut", "id_cliente", "id cliente", "id_cliente (rut)", "id cliente (rut)"},
    "OP": {"op", "operacion", "operación", "nro_documento", "nro documento", "documento", "operacion1"},
    "NOMBRE": {"nombre", "name", "cliente", "contacto"}
}

def _pick_col(df: pd.DataFrame, logical_name: str) -> str | None:
    """Devuelve el nombre real de la columna que matchea el logical_name usando sinónimos."""
    targets = {s.lower().strip() for s in POSSIBLE_NAMES.get(logical_name, set())}
    for col in df.columns:
        key = str(col).lower().strip()
        if key in targets:
            return col
    return None

def _as_text(series: pd.Series) -> pd.Series:
    """Normaliza a texto, quita sufijo '.0' y espacios laterales."""
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.strip()

def _parse_hora(s: str) -> time:
    """Parsea hora HH:MM o HH:MM:SS."""
    s = (s or "").strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s, fmt).time()
        except ValueError:
            pass
    raise ValueError("Formato de hora inválido (usa HH:MM o HH:MM:SS).")

def _generate_schedule(n: int, fecha: date, hora_inicio: str, hora_fin: str, intervalo_segundos: int | None) -> list[str]:
    """
    Genera una lista de timestamps 'YYYY-MM-DD HH:MM:SS' para n registros,
    dentro del rango [inicio, fin]. Si intervalo es None, se auto-ajusta para que quepan todos.
    """
    t_ini = _parse_hora(hora_inicio)
    t_fin = _parse_hora(hora_fin)
    dt_ini = datetime.combine(fecha, t_ini)
    dt_fin = datetime.combine(fecha, t_fin)
    if dt_fin <= dt_ini:
        raise ValueError("La hora fin debe ser mayor a la hora inicio.")
    rango_seg = int((dt_fin - dt_ini).total_seconds())
    if n <= 0:
        return []
    if intervalo_segundos is not None and intervalo_segundos > 0:
        capacidad = rango_seg // intervalo_segundos + 1  # incluye el inicio
        if n > capacidad:
            raise ValueError(
                f"El rango {hora_inicio}–{hora_fin} no alcanza para {n} registros con intervalo de {intervalo_segundos}s "
                f"(capacidad: {capacidad}). Ajusta el intervalo o amplía el rango."
            )
        step = intervalo_segundos
    else:
        # Auto-ajuste: distribución homogénea para que entren todos
        step = 1 if n == 1 else max(1, rango_seg // (n - 1))
    schedule = [dt_ini + timedelta(seconds=i * step) for i in range(n)]
    schedule = [min(dt, dt_fin) for dt in schedule]  # no pasar la hora fin
    return [dt.strftime("%Y-%m-%d %H:%M:%S") for dt in schedule]


# ---------------------------
# Construcción archivo IVR (Athenas)
# ---------------------------
def build_ivr_output(df: pd.DataFrame, campo1_value: str) -> pd.DataFrame:
    base = df.copy()
    tel_col = _pick_col(base, "TELEFONO")
    rut_col = _pick_col(base, "RUT")
    op_col  = _pick_col(base, "OP")
    nom_col = _pick_col(base, "NOMBRE")
    if not tel_col:
        raise ValueError("Falta columna de TELEFONO (acepta: Telefono, Teléfono, Fono, Celular, Móvil).")

    telefono = _as_text(base[tel_col])
    rut      = _as_text(base[rut_col]) if rut_col else pd.Series([""] * len(base), index=base.index)
    oper     = _as_text(base[op_col])  if op_col  else pd.Series([""] * len(base), index=base.index)

    # ---- Cambio solicitado: MENSAJE = nombre si existe; si no existe o viene vacío por fila, usar RUT ----
    if nom_col:
        nombre = _as_text(base[nom_col])
        # Fallback por fila: si nombre queda vacío, usar RUT
        nombre = nombre.where(nombre.str.len() > 0, rut)
    else:
        # Si no existe columna de nombre, usar directamente el RUT
        nombre = rut

    final_cols = ["TELEFONO", "MENSAJE", "ID_CLIENTE", "", "OPCIONAL", "CAMPO1", "CAMPO2"]
    out = pd.DataFrame(columns=final_cols)
    out["TELEFONO"]   = "56" + telefono
    out["MENSAJE"]    = nombre
    out["ID_CLIENTE"] = rut
    out[""]           = ""
    out["OPCIONAL"]   = oper
    out["CAMPO1"]     = campo1_value
    out["CAMPO2"]     = ""
    return out


# ---------------------------
# Construcción archivo CRM (nuevo)
# ---------------------------
def build_crm_output(df: pd.DataFrame, fecha: date, hora_inicio: str, hora_fin: str, usuario_value: str, intervalo_segundos: int | None) -> pd.DataFrame:
    base = df.copy()
    tel_col = _pick_col(base, "TELEFONO")
    rut_col = _pick_col(base, "RUT")
    op_col  = _pick_col(base, "OP")  # NRO_DOCUMENTO
    faltantes = []
    if not rut_col: faltantes.append("RUT")
    if not op_col:  faltantes.append("NRO_DOCUMENTO/OP")
    if not tel_col: faltantes.append("TELEFONO")
    if faltantes:
        raise ValueError("Faltan columnas requeridas en el Excel base: " + ", ".join(faltantes))
    rut      = _as_text(base[rut_col])
    nro_doc  = _as_text(base[op_col])
    telefono = _as_text(base[tel_col])
    n = len(base)
    fechas = _generate_schedule(n, fecha, hora_inicio, hora_fin, intervalo_segundos)
    out_cols = ["RUT", "NRO_DOCUMENTO", "FECHA_GESTION", "TELEFONO", "OBSERVACION", "USUARIO", "CORREO"]
    out = pd.DataFrame(columns=out_cols, index=base.index)
    out["RUT"]            = rut
    out["NRO_DOCUMENTO"]  = nro_doc
    out["FECHA_GESTION"]  = fechas
    out["TELEFONO"]       = telefono       # tal cual origen (sin 56)
    out["OBSERVACION"]    = "IVR"
    out["USUARIO"]        = usuario_value
    out["CORREO"]         = " "            # espacio para no vacío
    return out


# ---------------------------
# ÚNICA página GET: envia opciones para ambos formularios (Athenas + CRM)
# ---------------------------

# ---- Cambio solicitado: mostrar nombres amigables pero enviar los códigos CAMPO1 reales ----
CAMPO1_CHOICES = [
    ("ITAÚ VENCIDA",         "PHOENIXIVRITAUVENCIDA"),
    ("ITAÚ CASTIGO",         "PHOENIXIVRITAUCASTIGO"),
    ("CAJA 18",              "PHOENIXIVRCAJA18_3"),
    ("BANCO INTERNACIONAL",  "PHOENIX_BINTERNACIONAL"),
    ("SANTANDER HIPOTECARIO","PHOENIXIVRSANTANDERHIPO"),
    ("SANTANDER CONSUMER",   "PHOENIXSC_ICOMERCIAL"),
    ("GENERAL MOTORS",       "PHOENIXGMPREJUDICIAL"),
]

@app.route("/ivr", methods=["GET"])
def ivr_page():
    # Transformamos a pares label/value para el <option>
    campo1_options = [{"label": label, "value": value} for label, value in CAMPO1_CHOICES]
    usuarios = ["dlopez", "jriveros", "VDAD"]
    return render_template("ivr.html", campo1_options=campo1_options, usuarios=usuarios)

# ---------------------------
# Procesa Athenas (usa CAMPO1)
# ---------------------------
@app.route("/ivr/process", methods=["POST"])
def ivr_process():
    file = request.files.get("file")
    campo1 = (request.form.get("campo1") or "").strip()
    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("ivr_page"))
    if not campo1:
        flash("Debes seleccionar un valor para CAMPO1.", "danger")
        return redirect(url_for("ivr_page"))
    try:
        df = pd.read_excel(file, engine="openpyxl")
        salida = build_ivr_output(df, campo1_value=campo1)
        fecha_actual = datetime.now().strftime("%d-%m")
        name = f"cargaIVR_{fecha_actual}_.xlsx"
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            salida.to_excel(writer, index=False, sheet_name="Hoja1")
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("ivr_page"))
    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("ivr_page"))

# ---------------------------
# Procesa CRM (usa fecha/rango/intervalo/usuario)
# ---------------------------
@app.route("/ivr_crm/process", methods=["POST"])
def ivr_crm_process():
    file          = request.files.get("file")
    usuario       = (request.form.get("usuario") or "").strip()
    fecha_str     = (request.form.get("fecha") or "").strip()
    hora_inicio   = (request.form.get("hora_inicio") or "").strip()
    hora_fin      = (request.form.get("hora_fin") or "").strip()
    intervalo_str = (request.form.get("intervalo") or "").strip()

    intervalo = None
    if intervalo_str:
        try:
            intervalo_val = int(intervalo_str)
            if intervalo_val > 0:
                intervalo = intervalo_val
            else:
                flash("El intervalo debe ser un entero positivo en segundos.", "danger")
                return redirect(url_for("ivr_page"))
        except Exception:
            flash("Intervalo inválido. Usa un entero en segundos.", "danger")
            return redirect(url_for("ivr_page"))

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("ivr_page"))
    if not usuario:
        flash("Debes seleccionar un USUARIO.", "danger")
        return redirect(url_for("ivr_page"))
    if not fecha_str or not hora_inicio or not hora_fin:
        flash("Debes indicar FECHA DE GESTIÓN y el RANGO HORARIO.", "danger")
        return redirect(url_for("ivr_page"))

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        flash("Formato de fecha inválido (usa AAAA-MM-DD).", "danger")
        return redirect(url_for("ivr_page"))

    try:
        df = pd.read_excel(file, engine="openpyxl")
        salida = build_crm_output(
            df=df,
            fecha=fecha,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            usuario_value=usuario,
            intervalo_segundos=intervalo
        )
        fecha_actual = datetime.now().strftime("%d-%m")
        name = f"cargaIVR_CRM_{fecha_actual}.xlsx"
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            salida.to_excel(writer, index=False, sheet_name="Hoja1")
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=name,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except ValueError as e:
        flash(str(e), "danger")
        return redirect(url_for("ivr_page"))
    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("ivr_page"))

# ---------------------------
# Main (si lo usas)
# ---------------------------
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5013)
