"""Explicit provider-to-canonical entity resolution for Black Diamond.

No fuzzy or name-only match is ever promoted automatically. Provider IDs and
trusted cross-reference IDs can resolve deterministically; descriptive fields
only produce REVIEW candidates.
"""
from dataclasses import dataclass, field
from datetime import datetime
import re
import unicodedata
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


VALID_ENTITY_TYPES = {"player", "team", "event"}


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = unicodedata.normalize("NFKD", value)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.casefold().strip()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


@dataclass(frozen=True)
class CanonicalEntity:
    canonical_id: str
    entity_type: str
    display_name: str
    birth_date: Optional[str] = None
    external_ids: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)

    def __post_init__(self):
        if self.entity_type not in VALID_ENTITY_TYPES:
            raise ValueError("unsupported entity_type")
        if not isinstance(self.canonical_id, str) or not self.canonical_id.strip():
            raise ValueError("canonical_id required")


@dataclass(frozen=True)
class ResolutionResult:
    status: str
    canonical_id: Optional[str]
    method: str
    candidates: Tuple[str, ...] = field(default_factory=tuple)
    reason: str = ""


class EntityResolutionRegistry:
    """In-memory registry contract; persistence can be layered underneath later."""

    def __init__(self):
        self._canonical: Dict[str, CanonicalEntity] = {}
        self._provider_map: Dict[Tuple[str, str, str], str] = {}
        self._external_map: Dict[Tuple[str, str, str], str] = {}

    def register_canonical(self, entity: CanonicalEntity) -> None:
        if not isinstance(entity, CanonicalEntity):
            raise ValueError("CanonicalEntity required")
        if entity.canonical_id in self._canonical:
            raise ValueError("duplicate canonical_id")
        self._canonical[entity.canonical_id] = entity
        for namespace, value in entity.external_ids:
            key = (entity.entity_type, str(namespace), str(value))
            if key in self._external_map:
                raise ValueError("duplicate external identity")
            self._external_map[key] = entity.canonical_id

    def bind_provider_identity(
        self, *, entity_type: str, provider_id: str,
        provider_entity_id: Any, canonical_id: str
    ) -> None:
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError("unsupported entity_type")
        if canonical_id not in self._canonical:
            raise ValueError("unknown canonical_id")
        if self._canonical[canonical_id].entity_type != entity_type:
            raise ValueError("canonical entity type mismatch")
        key = (entity_type, str(provider_id), str(provider_entity_id))
        existing = self._provider_map.get(key)
        if existing is not None and existing != canonical_id:
            raise ValueError("provider identity already bound to another canonical entity")
        self._provider_map[key] = canonical_id

    def resolve(
        self, *, entity_type: str, provider_id: str,
        provider_entity_id: Any, external_ids: Optional[Mapping[str, Any]] = None,
        display_name: Optional[str] = None, birth_date: Optional[str] = None
    ) -> ResolutionResult:
        if entity_type not in VALID_ENTITY_TYPES:
            raise ValueError("unsupported entity_type")
        direct = self._provider_map.get(
            (entity_type, str(provider_id), str(provider_entity_id)))
        if direct:
            return ResolutionResult("RESOLVED", direct, "PROVIDER_ID")

        external_matches = set()
        for namespace, value in (external_ids or {}).items():
            if value is None or value == "":
                continue
            match = self._external_map.get(
                (entity_type, str(namespace), str(value)))
            if match:
                external_matches.add(match)
        if len(external_matches) == 1:
            return ResolutionResult(
                "RESOLVED", next(iter(external_matches)), "EXTERNAL_ID")
        if len(external_matches) > 1:
            return ResolutionResult(
                "CONFLICT", None, "EXTERNAL_ID_CONFLICT",
                tuple(sorted(external_matches)),
                "trusted cross-reference IDs disagree")

        # Descriptive matching is suggestion-only. Never auto-bind on names.
        name_key = normalize_text(display_name)
        candidates = []
        if name_key:
            for entity in self._canonical.values():
                if entity.entity_type != entity_type:
                    continue
                if normalize_text(entity.display_name) != name_key:
                    continue
                if birth_date and entity.birth_date and entity.birth_date != birth_date:
                    continue
                candidates.append(entity.canonical_id)
        if candidates:
            return ResolutionResult(
                "REVIEW", None, "DESCRIPTIVE_MATCH",
                tuple(sorted(candidates)),
                "descriptive identity requires explicit binding")
        return ResolutionResult(
            "UNRESOLVED", None, "NO_MATCH", (),
            "no deterministic provider or external identity mapping")


def canonicalize_provider_record(
    raw_record: Mapping[str, Any], *, provider_id: str,
    registry: EntityResolutionRegistry,
    player_external_ids: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Replace provider event/team/player IDs with canonical IDs or fail closed."""
    if not isinstance(raw_record, Mapping):
        raise ValueError("raw_record mapping required")
    out = dict(raw_record)

    resolutions = {
        "event": registry.resolve(
            entity_type="event", provider_id=provider_id,
            provider_entity_id=raw_record.get("event_id")),
        "team": registry.resolve(
            entity_type="team", provider_id=provider_id,
            provider_entity_id=raw_record.get("team_id")),
        "player": registry.resolve(
            entity_type="player", provider_id=provider_id,
            provider_entity_id=raw_record.get("player_id"),
            external_ids=player_external_ids,
            display_name=raw_record.get("player_name"),
            birth_date=raw_record.get("player_birth_date")),
    }
    unresolved = {
        kind: result for kind, result in resolutions.items()
        if result.status != "RESOLVED"
    }
    if unresolved:
        detail = ", ".join(
            f"{kind}:{result.status}/{result.method}"
            for kind, result in sorted(unresolved.items()))
        raise ValueError(f"canonical entity resolution HOLD: {detail}")

    out["provider_event_id"] = str(raw_record.get("event_id"))
    out["provider_team_id"] = str(raw_record.get("team_id"))
    out["provider_player_id"] = str(raw_record.get("player_id"))
    out["event_id"] = resolutions["event"].canonical_id
    out["team_id"] = resolutions["team"].canonical_id
    out["player_id"] = resolutions["player"].canonical_id
    out["entity_resolution"] = {
        kind: {"canonical_id": result.canonical_id, "method": result.method}
        for kind, result in resolutions.items()
    }
    return out
