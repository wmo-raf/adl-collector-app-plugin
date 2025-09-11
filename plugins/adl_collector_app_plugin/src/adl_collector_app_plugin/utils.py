import hashlib
import json
from typing import Iterable, Mapping


def compute_submission_hash(*, station_link_id: int, observation_time, records: Iterable[Mapping],
                            meta: Mapping | None):
    """
    Stable SHA-256 over normalized payload:
      - sort records by variable_mapping_id
      - drop any transient/unknown keys
      - ensure meta is dict (or {})
    """
    norm = {
        "station_link_id": station_link_id,
        "observation_time": observation_time.isoformat(),
        "records": sorted(
            [{"variable_mapping_id": int(r["variable_mapping_id"]), "value": float(r["value"])} for r in records],
            key=lambda x: x["variable_mapping_id"]
        ),
        "meta": meta or {},
    }
    blob = json.dumps(norm, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()
