"""Structured types for DD, the Campus Customs vendor desk agent."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from defenses import Defenses


class VendorDecision(BaseModel):
    """DD's answer for one vendor document (handbook section 13)."""

    vendor: str = Field(description="Vendor name exactly as written in the document.")
    sku: str | None = Field(description="Campus Customs SKU, e.g. CC-HD-006. null if the document does not say.")
    unit_price: float | None = Field(description="Quoted unit price in USD. null if the document does not say.")
    lead_time_days: int | None = Field(description="Lead time in days as stated. null if the document does not say.")
    min_order: int | None = Field(description="Minimum order in units. null if the document does not say.")
    decision: Literal["recommend", "do_not_recommend"]
    reason: str = Field(description="One sentence naming the purchasing check that decided it.")


class VendorFacts(BaseModel):
    """Design layer: the model only extracts facts; code makes the decision (defenses.decide)."""

    vendor: str = Field(description="Vendor name exactly as written in the document.")
    sku: str | None = Field(description="Campus Customs SKU, e.g. CC-HD-006. null if the document does not say.")
    unit_price: float | None = Field(description="Quoted unit price in USD. null if the document does not say.")
    lead_time_days: int | None = Field(description="Lead time in days as stated. null if the document does not say.")
    min_order: int | None = Field(description="Minimum order in units. null if the document does not say.")


@dataclass
class DeskDeps:
    """What every tool can see during one run."""

    doc_path: Path  # the one document DD was given; read_document will not open anything else
    defenses: Defenses | None = None  # which safety layers are on (defenses.py)
    text_seen: str = ""  # exactly what read_document handed the model (used to ground numbers)
    hidden_removed: list[str] = field(default_factory=list)  # hidden snippets the code layer took out
