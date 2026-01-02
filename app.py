from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import pandas as pd
from datetime import datetime, date, time
import io
import zipfile

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


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    file = request.files.get("file")
    mensaje = (request.form.get("mensaje") or "").strip()
    usuario = (request.form.get("usuario") or "").strip()

    if not file or file.filename == "":
        flash("Debes subir un archivo Excel.", "danger")
        return redirect(url_for("index"))

    if not mensaje:
        flash("Debes ingresar un Mensaje.", "danger")
        return redirect(url_for("index"))

    if not usuario:
        flash("Debes ingresar un Usuario.", "danger")
        return redirect(url_for("index"))

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
        return redirect(url_for("index"))
    except Exception as e:
        flash(f"Ocurrió un error procesando el archivo: {e}", "danger")
        return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5013)
