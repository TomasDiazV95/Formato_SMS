from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata

import pandas as pd


ADDRESS_OUTPUT_COLUMNS = [
    "RUT",
    "DV",
    "RUT+DV",
    "NOMBRE",
    "DIRECCION",
    "NUMERO",
    "COMUNA",
    "CIUDAD",
]

STREET_PREFIX_REPLACEMENTS = {
    "AVDA": "AVENIDA",
    "AV.": "AVENIDA",
    "AV": "AVENIDA",
    "PJE": "PASAJE",
    "PJ": "PASAJE",
    "PSJE": "PASAJE",
    "PSJ": "PASAJE",
    "CALLE": "CALLE",
    "CL": "CALLE",
    "V": "VILLA",
}

UNIT_WORDS = {
    "DEPTO",
    "DPTO",
    "DTO",
    "DP",
    "DEPARTAMENTO",
    "CASA",
    "BLOCK",
    "BLK",
    "TORRE",
    "OF",
    "OFICINA",
    "LOCAL",
    "PISO",
    "LT",
    "LOTE",
    "PARCELA",
    "KM",
}

REFERENCE_WORDS = {
    "ALERCE",
    "AMERICAS",
    "BARRIO",
    "CONDOMINIO",
    "CONJUNTO",
    "ESTADIO",
    "MISTRAL",
    "NACIONAL",
    "PARQUE",
    "PLAZA",
    "POB",
    "POBLACION",
    "SECTOR",
    "VILLA",
}

SOFT_IGNORED_WORDS = {
    "AVENIDA",
    "AV",
    "AVDA",
    "CALLE",
    "NRO",
    "NUMERO",
    "PASAJE",
    "PJ",
    "PJE",
    "PSJE",
}

SOFT_TOKEN_REPLACEMENTS = {
    "COND": "CONDOMINIO",
    "DEP": "DEPTO",
    "DEPT": "DEPTO",
    "DTO": "DEPTO",
    "DP": "DEPTO",
    "DPTO": "DEPTO",
    "DTPO": "DEPTO",
    "MZ": "MANZANA",
    "MZA": "MANZANA",
    "MANZ": "MANZANA",
    "NVA": "NUEVA",
    "NVO": "NUEVO",
    "SGTO": "SARGENTO",
    "STA": "SANTA",
}

SOFT_SINGLE_TOKEN_BLOCKLIST = {
    "NORTE",
    "SUR",
    "ORIENTE",
    "PONIENTE",
    "SAN",
    "SANTA",
    "SANTO",
}

GLUED_REFERENCE_SUFFIXES = {
    "ALERCE",
    "AMERICAS",
    "ESTADIO",
    "LAS",
    "LOS",
    "MISTRAL",
    "NACIONAL",
    "PARQUE",
    "PLAZA",
    "POB",
    "POBLACION",
    "VILLA",
}

NO_VALUE = {"", "0", "00", "000", "NAN", "NONE", "NULL", "SIN INFORMACION"}


@dataclass
class AddressAnalysis:
    clean_address: str
    street_base: str
    number: str
    fingerprint: str
    score: int
    reason: str
    comuna: str
    ciudad: str


def _ascii_fold(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return text.encode("ascii", "ignore").decode("ascii")


def _normalize_key(value: object) -> str:
    text = _ascii_fold(value).lower()
    return re.sub(r"[^a-z0-9]", "", text)


def _find_col(df: pd.DataFrame, aliases: set[str]) -> str | None:
    idx = {_normalize_key(col): col for col in df.columns}
    for alias in aliases:
        key = _normalize_key(alias)
        if key in idx:
            return idx[key]
    return None


def _raw_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.strip()


def _display_text(value: object) -> str:
    return _normalize_text(value)


def _empty_if_zero(value: object) -> str:
    text = _raw_text(value)
    if _ascii_fold(text).upper() in NO_VALUE:
        return ""
    return text


def _normalize_text(value: object) -> str:
    text = _empty_if_zero(value)
    if not text:
        return ""
    text = _ascii_fold(text).upper()
    text = re.sub(r"([A-Z])(\d)", r"\1 \2", text)
    text = re.sub(r"(\d)([A-Z])", r"\1 \2", text)
    text = re.sub(r"[^A-Z0-9#\-/ ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _separate_glued_reference_words(text)


def _separate_glued_reference_words(text: str) -> str:
    for suffix in sorted(GLUED_REFERENCE_SUFFIXES, key=len, reverse=True):
        unit_pattern = rf"\b((?:DEPTO|DPTO|DTO|DP|BLOCK|BLK|TORRE|CASA|OF|LOCAL)\s+)([A-Z])({suffix})\b"
        text = re.sub(unit_pattern, rf"\1\2 {suffix}", text)
        if suffix == "NACIONAL":
            text = re.sub(r"\b(ESTADIO)(NACIONAL)\b", r"\1 \2", text)
            continue
        common_pattern = rf"\b([A-Z]{{4,}})({suffix})\b"
        text = re.sub(common_pattern, rf"\1 {suffix}", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_prefixes(text: str) -> str:
    parts = text.split()
    if not parts:
        return ""
    first = parts[0].rstrip(".")
    if first in STREET_PREFIX_REPLACEMENTS:
        parts[0] = STREET_PREFIX_REPLACEMENTS[first]
    return " ".join(parts)


def _collapse_suspicious_tail(text: str) -> tuple[str, bool]:
    """Trim common dirty tails like duplicated sector + score letters at the end."""
    original = text
    text = re.sub(r"\b([A-Z ]{3,})\s+\1\s+\d+\s+[A-Z]\s*$", r"\1", text)
    text = re.sub(r"\b([A-Z ]{3,})\s+\1\s+\d+\s*$", r"\1", text)
    text = re.sub(r"\b([A-Z][A-Z ]{2,})\s+\d+\s+[A-Z]\s*$", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text, text != original


def _extract_number(clean_address: str, numero_value: object) -> str:
    explicit = _empty_if_zero(numero_value)
    if explicit:
        digits = re.search(r"\d+", explicit)
        if digits:
            return digits.group(0)

    tokens = clean_address.split()
    number_candidates: list[tuple[int, str]] = []
    for index, token in enumerate(tokens):
        if not re.fullmatch(r"\d+[A-Z]?", token):
            continue
        previous = tokens[index - 1] if index > 0 else ""
        if previous in UNIT_WORDS:
            continue
        if index == 1 and tokens[0] in {"AVENIDA", "CALLE", "PASAJE"} and len(token) <= 2:
            continue
        digits = re.match(r"\d+", token)
        if digits:
            number_candidates.append((index, digits.group(0)))
    if not number_candidates:
        return ""
    return number_candidates[0][1]


def _street_base_from_address(clean_address: str, number: str) -> str:
    if not clean_address:
        return ""
    if number:
        base = re.sub(rf"\b{re.escape(number)}[A-Z]?\b.*$", "", clean_address).strip()
        if base:
            return base
    return clean_address


def _fingerprint(street_base: str, number: str, comuna: str, ciudad: str) -> str:
    base = _normalize_prefixes(street_base)
    base = re.sub(r"[^A-Z0-9 ]+", " ", base)
    base_parts = []
    for token in re.sub(r"\s+", " ", base).strip().split():
        normalized = SOFT_TOKEN_REPLACEMENTS.get(token, token)
        if normalized in {"NRO", "NUMERO"}:
            continue
        base_parts.append(normalized)
    base = " ".join(base_parts)
    parts = [base, number]
    if comuna:
        parts.append(comuna)
    elif ciudad:
        parts.append(ciudad)
    return "|".join(part for part in parts if part)


def _has_glued_common_word(text: str) -> bool:
    return bool(re.search(r"\b[A-Z]{4,}(LAS|LOS|EL|LA|VILLA|POB|POBLACION)\b", text))


def _reference_detail(clean_address: str) -> tuple[int, set[str], set[str]]:
    tokens = set(clean_address.split())
    unit_hits = tokens & UNIT_WORDS
    reference_hits = tokens & REFERENCE_WORDS
    bonus = min(len(unit_hits) * 4, 12) + min(len(reference_hits) * 6, 24)
    if unit_hits and reference_hits:
        bonus += 5
    return bonus, unit_hits, reference_hits


def _score(clean_address: str, number: str, comuna: str, ciudad: str, trimmed_tail: bool) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    if clean_address:
        score += min(len(clean_address), 80)
    if number:
        score += 35
        reasons.append("numero detectado")
    else:
        reasons.append("sin numero")
    if comuna:
        score += 15
        reasons.append("comuna valida")
    if ciudad:
        score += 10
        reasons.append("ciudad valida")
    detail_bonus, unit_hits, reference_hits = _reference_detail(clean_address)
    if detail_bonus:
        score += detail_bonus
    if unit_hits:
        reasons.append("detalle unidad")
    if reference_hits:
        reasons.append("referencia util")
    if trimmed_tail:
        if reference_hits:
            reasons.append("sufijo operativo recortado")
        else:
            score -= 18
            reasons.append("cola sospechosa recortada")
    if _has_glued_common_word(clean_address):
        score -= 25
        reasons.append("texto pegado detectado")
    if re.search(r"\d+\s+[A-Z]\s*$", clean_address):
        score -= 8
        reasons.append("posible sufijo operativo")
    return max(score, 0), "; ".join(reasons)


def _analyze_address(row: pd.Series, *, direccion_col: str, numero_col: str | None, comuna_col: str | None, ciudad_col: str | None) -> AddressAnalysis:
    address = _normalize_text(row.get(direccion_col, ""))
    address = _normalize_prefixes(address)
    address, trimmed_tail = _collapse_suspicious_tail(address)
    comuna = _normalize_text(row.get(comuna_col, "")) if comuna_col else ""
    ciudad = _normalize_text(row.get(ciudad_col, "")) if ciudad_col else ""
    numero_value = row.get(numero_col, "") if numero_col else ""
    number = _extract_number(address, numero_value)
    street_base = _street_base_from_address(address, number)
    fingerprint = _fingerprint(street_base, number, comuna, ciudad)
    score, reason = _score(address, number, comuna, ciudad, trimmed_tail)
    return AddressAnalysis(address, street_base, number, fingerprint, score, reason, comuna, ciudad)


def _rut_parts(row: pd.Series, rut_col: str, dv_col: str | None) -> tuple[str, str, str]:
    raw_rut = _raw_text(row.get(rut_col, ""))
    raw_dv = _raw_text(row.get(dv_col, "")) if dv_col else ""
    dv = re.sub(r"[^0-9Kk]", "", raw_dv).upper()
    rut = re.sub(r"\D+", "", raw_rut)

    if not dv:
        compact = re.sub(r"[^0-9Kk]", "", raw_rut).upper()
        has_explicit_dv = "-" in raw_rut or compact.endswith("K")
        if has_explicit_dv and len(compact) > 1 and compact[-1] in "0123456789K":
            rut = re.sub(r"\D+", "", compact[:-1])
            dv = compact[-1]

    rut_dv = f"{rut}-{dv}" if rut and dv else rut
    return rut, dv, rut_dv


def _clean_joined_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,;])", r"\1", text)
    return text.strip(" ,;-")


def _remove_number_from_address(text: str, number: str) -> str:
    if not text or not number:
        return text
    pattern = rf"(?<![A-Z0-9]){re.escape(number)}[A-Z]?(?![A-Z0-9])"
    return _clean_joined_text(re.sub(pattern, " ", text, count=1))


def _remove_phrase_from_address(text: str, phrase: str) -> str:
    if not text or not phrase:
        return text
    escaped = r"\s+".join(re.escape(part) for part in phrase.split())
    pattern = rf"(?<![A-Z0-9]){escaped}(?![A-Z0-9])"
    return _clean_joined_text(re.sub(pattern, " ", text))


def _direccion_separada(analysis: AddressAnalysis) -> str:
    address = _remove_number_from_address(analysis.clean_address, analysis.number)
    for value in sorted({analysis.comuna, analysis.ciudad} - {""}, key=len, reverse=True):
        address = _remove_phrase_from_address(address, value)
    return address


def _is_prefix_duplicate(current: AddressAnalysis, candidate: AddressAnalysis) -> bool:
    if not current.number or current.number != candidate.number:
        return False
    if not current.street_base or not candidate.street_base:
        return False
    short, long = sorted([current.street_base, candidate.street_base], key=len)
    if len(short) < 6:
        return False
    return long.startswith(short)


def _record_quality_key(record: dict[str, object]) -> tuple[int, int, int, int]:
    return (
        int(record["__score"]),
        1 if str(record.get("COMUNA", "")).strip() else 0,
        1 if str(record.get("CIUDAD", "")).strip() else 0,
        len(str(record.get("DIRECCION", "")).strip()),
    )


def _soft_direction_tokens(record: dict[str, object]) -> set[str]:
    text = _normalize_text(record.get("DIRECCION", ""))
    text = re.sub(r"\bS\s+ANTA\b", "SANTA", text)
    tokens: set[str] = set()
    for token in text.split():
        token = SOFT_TOKEN_REPLACEMENTS.get(token, token)
        if token in SOFT_IGNORED_WORDS:
            continue
        if not re.search(r"[A-Z0-9]", token):
            continue
        tokens.add(token)
    return tokens


def _soft_numeric_tokens(tokens: set[str]) -> set[str]:
    return {token for token in tokens if token.isdigit()}


def _soft_addresses_match(left: dict[str, object], right: dict[str, object]) -> bool:
    left_tokens = _soft_direction_tokens(left)
    right_tokens = _soft_direction_tokens(right)
    if not left_tokens or not right_tokens:
        return False

    left_numbers = _soft_numeric_tokens(left_tokens)
    right_numbers = _soft_numeric_tokens(right_tokens)
    if left_numbers and right_numbers and not (left_numbers & right_numbers):
        return False

    left_words = left_tokens - left_numbers
    right_words = right_tokens - right_numbers
    compare_left = left_words or left_tokens
    compare_right = right_words or right_tokens

    if compare_left == compare_right:
        return True

    shorter, longer = sorted([compare_left, compare_right], key=len)
    if shorter <= longer and len(shorter) >= 2:
        return True

    intersection = compare_left & compare_right
    if len(intersection) >= 2:
        union = compare_left | compare_right
        return len(intersection) / len(union) >= 0.55

    if len(intersection) == 1 and len(compare_left) <= 2 and len(compare_right) <= 2:
        token = next(iter(intersection))
        return len(token) >= 4 and token not in SOFT_SINGLE_TOKEN_BLOCKLIST and not token.isdigit()

    return False


def _merge_record_sources(target: dict[str, object], source: dict[str, object]) -> None:
    target["__source_rows"] = f"{target['__source_rows']}, {source['__source_rows']}"


def _merge_similar_same_number(records: list[dict[str, object]]) -> list[dict[str, object]]:
    by_rut_number: dict[tuple[str, str], list[dict[str, object]]] = {}
    passthrough: list[dict[str, object]] = []

    for record in records:
        number = str(record.get("NUMERO", "")).strip()
        if not number:
            passthrough.append(record)
            continue
        key = (str(record["__rut_key"]), number)
        by_rut_number.setdefault(key, []).append(record)

    merged: list[dict[str, object]] = passthrough[:]
    for group in by_rut_number.values():
        if len(group) == 1:
            merged.extend(group)
            continue

        clusters: list[list[dict[str, object]]] = []
        for record in sorted(group, key=_record_quality_key, reverse=True):
            for cluster in clusters:
                if any(_soft_addresses_match(record, existing) for existing in cluster):
                    cluster.append(record)
                    break
            else:
                clusters.append([record])

        for cluster in clusters:
            survivor = max(cluster, key=_record_quality_key)
            for record in cluster:
                if record is not survivor:
                    _merge_record_sources(survivor, record)
            merged.append(survivor)

    return merged


def build_direcciones_depuradas(df_input: pd.DataFrame) -> pd.DataFrame:
    df = df_input.copy()
    df.columns = [str(col).replace("\ufeff", "").strip() for col in df.columns]

    rut_col = _find_col(df, {"RUT", "RUT_CLIENTE", "ID_CLIENTE", "RUTDEUDOR"})
    dv_col = _find_col(df, {"DV", "DIGITO", "DIGITO_VERIFICADOR", "DV_RUT"})
    nombre_col = _find_col(df, {"NOMBRE", "CLIENTE", "NOMBRE_CLIENTE", "NOMBRE_DEUDOR"})
    direccion_col = _find_col(df, {"DIRECCION", "DOMICILIO", "DIRECCION_PARTICULAR", "DIRECCION1"})
    numero_col = _find_col(df, {"NUMERO", "NRO", "NRO_DIRECCION", "NUMERO_DIRECCION"})
    comuna_col = _find_col(df, {"COMUNA", "LOCALIDAD", "SECTOR"})
    ciudad_col = _find_col(df, {"CIUDAD", "REGION", "PROVINCIA"})

    missing = []
    if rut_col is None:
        missing.append("RUT")
    if direccion_col is None:
        missing.append("DIRECCION")
    if missing:
        detected = ", ".join(str(col) for col in df.columns)
        raise ValueError(f"Faltan columnas requeridas: {', '.join(missing)}. Columnas detectadas: {detected}")

    enriched_rows: list[dict[str, object]] = []
    for original_index, row in df.iterrows():
        rut, dv, rut_dv = _rut_parts(row, rut_col, dv_col)
        analysis = _analyze_address(
            row,
            direccion_col=direccion_col,
            numero_col=numero_col,
            comuna_col=comuna_col,
            ciudad_col=ciudad_col,
        )
        record = {
            "RUT": rut,
            "DV": dv,
            "RUT+DV": rut_dv,
            "NOMBRE": _display_text(row.get(nombre_col, "")) if nombre_col else "",
            "DIRECCION": _direccion_separada(analysis),
            "NUMERO": analysis.number,
            "COMUNA": analysis.comuna,
            "CIUDAD": analysis.ciudad,
            "__rut_key": rut_dv or rut,
            "__fingerprint": analysis.fingerprint,
            "__score": analysis.score,
            "__source_rows": str(original_index + 2),
            "__analysis": analysis,
        }
        enriched_rows.append(record)

    groups: dict[tuple[str, str], dict[str, object]] = {}
    for record in enriched_rows:
        key = (str(record["__rut_key"]), str(record["__fingerprint"]))
        current = groups.get(key)
        if current is None or _record_quality_key(record) > _record_quality_key(current):
            if current is not None:
                record["__source_rows"] = f"{current['__source_rows']}, {record['__source_rows']}"
            groups[key] = record
        else:
            current["__source_rows"] = f"{current['__source_rows']}, {record['__source_rows']}"

    by_rut: dict[str, list[dict[str, object]]] = {}
    for record in groups.values():
        by_rut.setdefault(str(record["__rut_key"]), []).append(record)

    selected: list[dict[str, object]] = []
    for records in by_rut.values():
        keep: list[dict[str, object]] = []
        for record in sorted(records, key=_record_quality_key, reverse=True):
            analysis = record["__analysis"]
            duplicate_of_existing = False
            for existing in keep:
                existing_analysis = existing["__analysis"]
                if _is_prefix_duplicate(analysis, existing_analysis):
                    existing["__source_rows"] = f"{existing['__source_rows']}, {record['__source_rows']}"
                    duplicate_of_existing = True
                    break
            if not duplicate_of_existing:
                keep.append(record)
        selected.extend(sorted(keep, key=lambda item: (str(item["__rut_key"]), tuple(-part for part in _record_quality_key(item)))))

    selected = _merge_similar_same_number(selected)
    out = pd.DataFrame(selected)
    return out.reindex(columns=ADDRESS_OUTPUT_COLUMNS).fillna("")


def direcciones_depuradas_filename() -> str:
    return f"DIRECCIONES_DEPURADAS_{datetime.now().strftime('%d-%m-%y')}.xlsx"
