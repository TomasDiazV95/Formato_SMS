from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
from datetime import datetime, date, time
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
      dataFrame.loc[i, nombreColumna]=dataFrame.loc[i, nombreColumna].replace(',','.')


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



        df['POS/Curr. Acc. Bal.* ']=df['POS/Curr. Acc. Bal.* '].astype(str)
        df['EMI']=df['EMI'].astype(str)
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


# --- Sinónimos flexibles de columnas (case-insensitive) ---
POSSIBLE_NAMES = {
    "TELEFONO": {"telefono", "teléfono", "fono", "celular", "movil", "móvil"},
    "RUT": {"rut", "id_cliente", "id cliente", "id_cliente (rut)", "id cliente (rut)"},
    "OP": {"op", "operacion", "operación", "nro_documento", "nro documento", "documento"},
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

def build_ivr_output(df: pd.DataFrame, campo1_value: str) -> pd.DataFrame:
    base = df.copy()

    # Localizar columnas (tolerante)
    tel_col = _pick_col(base, "TELEFONO")
    rut_col = _pick_col(base, "RUT")
    op_col  = _pick_col(base, "OP")
    nom_col = _pick_col(base, "NOMBRE")

    # Validación mínima: al menos debe venir el teléfono
    if not tel_col:
        raise ValueError("Falta columna de TELEFONO (acepta: Telefono, Teléfono, Fono, Celular, Móvil).")

    # Normalizar a texto para evitar '... .0' y espacios sobrantes
    def _as_text(series):
        return series.astype(str).str.replace(r"\\.0$", "", regex=True).str.strip()

    telefono = _as_text(base[tel_col])

    # Si faltan RUT/OP/NOMBRE, se crean series vacías de la misma longitud
    nombre = _as_text(base[nom_col]) if nom_col else pd.Series([""] * len(base), index=base.index)
    rut    = _as_text(base[rut_col]) if rut_col else pd.Series([""] * len(base), index=base.index)
    oper   = _as_text(base[op_col])  if op_col  else pd.Series([""] * len(base), index=base.index)

    # Armar DataFrame final con encabezados EXACTOS (incluye uno vacío)
    final_cols = ["TELEFONO", "MENSAJE", "ID_CLIENTE", "", "OPCIONAL", "CAMPO1", "CAMPO2"]
    out = pd.DataFrame(columns=final_cols)

    out["TELEFONO"]   = telefono
    out["MENSAJE"]    = nombre            # NOMBRE si existe; sino blanco
    out["ID_CLIENTE"] = rut               # RUT si existe; sino blanco
    out[""]           = ""                # Columna sin encabezado, en blanco
    out["OPCIONAL"]   = oper              # OPERACIÓN si existe; sino blanco
    out["CAMPO1"]     = campo1_value      # Valor desde desplegable
    out["CAMPO2"]     = ""                # Blanco

    return out



@app.route("/ivr", methods=["GET"])
def ivr_page():
    # Opciones del desplegable CAMPO1
    campo1_options = [
        "PHOENIXIVRITAUVENCIDA",
        "PHOENIXIVRITAUCASTIGO",
        "PHOENIXIVRCAJA18_3",
        "PHOENIX_BINTERNACIONAL",
        "PHOENIXIVRSANTANDERHIPO",
        "PHOENIXSC_ICOMERCIAL",
        "PHOENIXGMPREJUDICIAL",
    ]
    return render_template("ivr.html", campo1_options=campo1_options)

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
        # Lee Excel base
        df = pd.read_excel(file, engine="openpyxl")

        # Construye salida IVR
        salida = build_ivr_output(df, campo1_value=campo1)

        # Nombre de archivo
        fecha_actual = datetime.now().strftime("%d-%m")
        name = f"cargaIVR_{fecha_actual}_.xlsx"

        # Escribe a memoria y descarga
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            # Nombre de hoja igual al ejemplo: Hoja1
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
    
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5013)
