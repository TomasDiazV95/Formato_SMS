from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SantanderConsumerTemplate:
    key: str
    label: str
    message_id: int
    nro_cuotas: str


SANTANDER_CONSUMER_TEMPLATES: tuple[SantanderConsumerTemplate, ...] = (
    SantanderConsumerTemplate(key="susceptible", label="Susceptible", message_id=84132, nro_cuotas=""),
    SantanderConsumerTemplate(key="reconduccion", label="Reconduccion", message_id=84436, nro_cuotas=""),
    SantanderConsumerTemplate(key="dacion", label="Dacion", message_id=86663, nro_cuotas=""),
    SantanderConsumerTemplate(key="vigente", label="Vigente", message_id=80463, nro_cuotas=""),
    SantanderConsumerTemplate(key="castigo", label="Castigo", message_id=80465, nro_cuotas=""),
    SantanderConsumerTemplate(key="3_cuotas", label="3 cuotas", message_id=90818, nro_cuotas="3 cuotas"),
    SantanderConsumerTemplate(key="2_cuotas", label="2 cuotas", message_id=90818, nro_cuotas="2 cuotas"),
)


def get_santander_consumer_template(template_key: str) -> SantanderConsumerTemplate | None:
    key = (template_key or "").strip().lower()
    for template in SANTANDER_CONSUMER_TEMPLATES:
        if template.key == key:
            return template
    return None
