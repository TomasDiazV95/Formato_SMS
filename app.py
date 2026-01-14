
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
from datetime import datetime, date, time, timedelta
import io
import zipfile
import tempfile


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

@app.route("/cargaGM", methods=['GET', 'POST'])
def gm_page():
    if request.method == 'POST':
        archivo = request.files['archivo']
        df = pd.read_excel(archivo)

        columnas_requeridas = ["campana_1", "campana_2", "campana_3", "campana_4", "campana_5"]
        for col in columnas_requeridas:
            if col not in df.columns:
                df[col] = ""

        df['POS/Curr. Acc. Bal.* '] = df['POS/Curr. Acc. Bal.* '].astype(str)
        df['EMI'] = df['EMI'].astype(str)
        df['POS/Curr. Acc. Bal.* '] = df['POS/Curr. Acc. Bal.* '].apply(lambda x: '{:,.0f}'.format(float(x.replace(',', ''))))
        df['EMI'] = df['EMI'].apply(lambda x: '{:,.0f}'.format(float(x.replace(',', ''))))

        reemplazarComa('EMI', df)
        reemplazarComa('POS/Curr. Acc. Bal.* ', df)

        fecha_actual = datetime.now().strftime("%d-%m")

        # Guardar el DataFrame en un archivo Excel
        archivo_excel = f"ARCHIVO COLLECTION {fecha_actual}.xlsx"
        df.to_excel(archivo_excel, index=False)

        # Crear y enviar ZIP directamente dentro del mismo bloque
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w') as zipf:
                zipf.write(archivo_excel)
            return send_file(
                temp_zip.name,
                as_attachment=True,
                download_name=f"Procesamiento_GM_{fecha_actual}.zip"
            )
    return render_template('cargagm.html')


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
