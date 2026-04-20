from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd


INPUT_FILE = Path("AGENTE_PHOENIX/REENVIADORES AGENTES SC TERRENO.xlsx")
OUTPUT_FILE = Path("inserts_ejecutivos_sc_terreno.sql")
MANDANTE = "Santander Consumer Terreno"


def clean(value: str) -> str:
    raw = str(value or "").replace("\u200b", "").replace("\ufeff", "").strip()
    return re.sub(r"\s+", " ", raw)


def slug_name(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", clean(name)).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", normalized).strip("_").lower()
    return normalized or "sin_nombre"


def sql_quote(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def main() -> None:
    df = pd.read_excel(INPUT_FILE, dtype=str).fillna("")

    rows: list[tuple[str, str, str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for _, record in df.iterrows():
        nombre = clean(record.get("NOMBRE", ""))
        reenviador = clean(record.get("REENVIADOR", ""))
        correo = clean(record.get("CORREO", ""))
        telefono = re.sub(r"\D+", "", clean(record.get("FONO AGENTE", "")))

        if not nombre:
            continue

        dedupe_key = (nombre.lower(), correo.lower(), reenviador.lower())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        rows.append((MANDANTE, slug_name(nombre), nombre, correo, telefono, reenviador))

    lines: list[str] = []
    lines.append("-- Ejecutivos Santander Consumer Terreno (upsert)")
    lines.append("INSERT INTO ejecutivos_phoenix (mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador)")
    lines.append("VALUES")
    for index, (mandante, nombre_clave, nombre_mostrar, correo, telefono, reenviador) in enumerate(rows):
        suffix = "," if index < len(rows) - 1 else ""
        lines.append(
            "    ("
            + ", ".join(
                [
                    sql_quote(mandante),
                    sql_quote(nombre_clave),
                    sql_quote(nombre_mostrar),
                    sql_quote(correo),
                    sql_quote(telefono),
                    sql_quote(reenviador),
                ]
            )
            + ")"
            + suffix
        )
    lines.extend(
        [
            "ON DUPLICATE KEY UPDATE",
            "    nombre_mostrar = VALUES(nombre_mostrar),",
            "    correo = VALUES(correo),",
            "    telefono = VALUES(telefono),",
            "    reenviador = VALUES(reenviador),",
            "    activo = 1;",
            "",
            "-- Alias recomendados para match de CARTERIZADO",
        ]
    )

    for _, nombre_clave, nombre_mostrar, _, _, _ in rows:
        for alias in (nombre_mostrar, nombre_mostrar.lower(), nombre_mostrar.upper()):
            lines.append(
                "INSERT IGNORE INTO ejecutivos_alias (ejecutivo_id, alias) "
                f"SELECT id, {sql_quote(alias)} FROM ejecutivos_phoenix "
                f"WHERE mandante = {sql_quote(MANDANTE)} AND nombre_clave = {sql_quote(nombre_clave)};"
            )

    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generado {OUTPUT_FILE} con {len(rows)} ejecutivos.")


if __name__ == "__main__":
    main()
