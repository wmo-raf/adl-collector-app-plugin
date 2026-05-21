import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FM12 element path choices
#
# Exhaustive list of dot-notation paths that extract_value_by_path() can
# reach from a pymetdecoder SYNOP dict.  Only paths whose leaf is a numeric
# int or float are listed (i.e. paths that return a non-None value).
#
# Integer path segments (e.g. "cloud_layer.0.cloud_cover._code") index into
# list-valued keys; extract_value_by_path() handles them since the 2024
# extension.  Supported list-valued keys:
#   - past_weather          — always 2 elements (W1=index 0, W2=index 1)
#   - cloud_layer           — 0–4 elements (section 3 "8NhClhh" groups)
#   - cloud_base_below_station — variable (section 4 "444…" groups)
# ---------------------------------------------------------------------------

FM12_ELEMENT_PATH_CHOICES: list[tuple[str, str]] = [
    # ── Physical quantities (returns a measurement, unit conversion applies) ──
    ("air_temperature.value", "Air Temperature (°C)"),
    ("dewpoint_temperature.value", "Dew-Point Temperature (°C)"),
    ("wet_bulb_temperature.value", "Wet-Bulb Temperature (°C)"),
    ("maximum_temperature.value", "Maximum Temperature (°C)"),
    ("minimum_temperature.value", "Minimum Temperature (°C)"),
    ("ground_minimum_temperature.value", "Ground Minimum Temperature (°C)"),
    ("relative_humidity.value", "Relative Humidity (%)"),
    ("station_pressure.value", "Station Pressure (hPa)"),
    ("sea_level_pressure.value", "Sea-Level Pressure (hPa)"),
    ("pressure_change.value", "Pressure Change (hPa)"),
    ("pressure_tendency.change.value", "Pressure Tendency — Change Amount (hPa)"),
    ("surface_wind.speed.value", "Surface Wind Speed (m/s or kn)"),
    ("surface_wind.direction.value", "Surface Wind Direction (degrees)"),
    ("highest_gust.speed.value", "Highest Gust Speed (m/s or kn)"),
    ("highest_gust.direction.value", "Highest Gust Direction (degrees)"),
    ("visibility.value", "Visibility (m)"),
    ("lowest_cloud_base.min", "Lowest Cloud-Base Height — lower bound (m)"),
    ("precipitation_s1.amount.value", "Precipitation — Section 1 (mm)"),
    ("precipitation_s3.amount.value", "Precipitation — Section 3 (mm)"),
    ("precipitation_24h.amount.value", "Precipitation — 24-hour (mm)"),
    ("local_precipitation.amount.value", "Local Precipitation Amount (mm)"),
    ("snow_fall.amount.value", "Snowfall Amount (cm)"),
    ("sunshine.amount.value", "Sunshine Duration (h)"),
    ("evapotranspiration.amount.value", "Evapotranspiration (mm)"),
    ("temperature_change.value", "Temperature Change (°C)"),
    ("ground_state.temperature.value", "Ground-State — Surface Temperature (°C)"),
    ("sea_surface_temperature.value", "Sea-Surface Temperature (°C)"),
    ("wind_waves.height.value", "Wind Waves — Height (m)"),
    ("wind_waves.period.value", "Wind Waves — Period (s)"),
    ("exact_obs_time.value", "Exact Observation Time (minutes past hour)"),
    # cloud_layer — physical height in metres per layer (section 3)
    ("cloud_layer.0.cloud_height.value", "Cloud Layer 1 — Base Height (m)"),
    ("cloud_layer.1.cloud_height.value", "Cloud Layer 2 — Base Height (m)"),
    ("cloud_layer.2.cloud_height.value", "Cloud Layer 3 — Base Height (m)"),
    ("cloud_layer.3.cloud_height.value", "Cloud Layer 4 — Base Height (m)"),
    # cloud_base_below_station — physical altitude in metres per entry (section 4)
    ("cloud_base_below_station.0.upper_surface_altitude.value", "Cloud Base Below Station 1 — Upper Altitude (m)"),
    ("cloud_base_below_station.1.upper_surface_altitude.value", "Cloud Base Below Station 2 — Upper Altitude (m)"),
    ("cloud_base_below_station.2.upper_surface_altitude.value", "Cloud Base Below Station 3 — Upper Altitude (m)"),
    
    # ── Coded integers (WMO lookup-table codes; pint conversion skipped) ──
    ("cloud_cover._code", "Total Cloud Cover — N (WMO table 2700, oktas)"),
    ("cloud_types.low_cloud_type.value", "Low Cloud Type — CL (WMO table 0513)"),
    ("cloud_types.middle_cloud_type.value", "Middle Cloud Type — CM (WMO table 0515)"),
    ("cloud_types.high_cloud_type.value", "High Cloud Type — CH (WMO table 0509)"),
    ("cloud_types.low_cloud_amount.value", "Low Cloud Amount — Nh (oktas)"),
    ("lowest_cloud_base._code", "Lowest Cloud-Base Height — WMO table code (table 1600)"),
    ("present_weather.value", "Present Weather — ww (WMO table 4677 / 4680)"),
    ("pressure_tendency.tendency.value", "Pressure Tendency Characteristic — a (WMO table 0200)"),
    ("visibility._code", "Visibility — WMO table code (table 4377)"),
    ("ground_state.state.value", "Ground State — E (WMO table 0901)"),
    ("ground_state_snow.state.value", "Ground State (Snow) — E' (WMO table 0975)"),
    ("ground_state_snow.depth.value", "Snow Depth (cm)"),
    ("sea_state.value", "Sea State (WMO table 3700)"),
    # past_weather — W1 and W2 (section 1 group 7wwW1W2)
    ("past_weather.0.value", "Past Weather W1 (WMO table 4531, codes 0–9)"),
    ("past_weather.1.value", "Past Weather W2 (WMO table 4531, codes 0–9)"),
    # cloud_layer coded fields per layer (section 3)
    ("cloud_layer.0.cloud_cover._code", "Cloud Layer 1 — Amount (WMO table 2700, oktas)"),
    ("cloud_layer.0.cloud_genus._code", "Cloud Layer 1 — Genus (WMO table 0500)"),
    ("cloud_layer.0.cloud_height._code", "Cloud Layer 1 — Height Code (WMO table 1677)"),
    ("cloud_layer.1.cloud_cover._code", "Cloud Layer 2 — Amount (WMO table 2700, oktas)"),
    ("cloud_layer.1.cloud_genus._code", "Cloud Layer 2 — Genus (WMO table 0500)"),
    ("cloud_layer.1.cloud_height._code", "Cloud Layer 2 — Height Code (WMO table 1677)"),
    ("cloud_layer.2.cloud_cover._code", "Cloud Layer 3 — Amount (WMO table 2700, oktas)"),
    ("cloud_layer.2.cloud_genus._code", "Cloud Layer 3 — Genus (WMO table 0500)"),
    ("cloud_layer.2.cloud_height._code", "Cloud Layer 3 — Height Code (WMO table 1677)"),
    ("cloud_layer.3.cloud_cover._code", "Cloud Layer 4 — Amount (WMO table 2700, oktas)"),
    ("cloud_layer.3.cloud_genus._code", "Cloud Layer 4 — Genus (WMO table 0500)"),
    ("cloud_layer.3.cloud_height._code", "Cloud Layer 4 — Height Code (WMO table 1677)"),
    # cloud_base_below_station coded fields per entry (section 4)
    ("cloud_base_below_station.0.cloud_cover._code", "Cloud Base Below Station 1 — Amount (WMO table 2700)"),
    ("cloud_base_below_station.0.description._code", "Cloud Base Below Station 1 — Description (WMO table 0552)"),
    ("cloud_base_below_station.1.cloud_cover._code", "Cloud Base Below Station 2 — Amount (WMO table 2700)"),
    ("cloud_base_below_station.1.description._code", "Cloud Base Below Station 2 — Description (WMO table 0552)"),
    ("cloud_base_below_station.2.cloud_cover._code", "Cloud Base Below Station 3 — Amount (WMO table 2700)"),
    ("cloud_base_below_station.2.description._code", "Cloud Base Below Station 3 — Description (WMO table 0552)"),
]


def decode_fm12(raw_message: str) -> dict:
    """
    Decode a FM12 SYNOP message using pymetdecoder.
    Returns the full decoded dict. Raises ValueError on parse failure.
    """
    try:
        from pymetdecoder import synop as pymet_synop
    except ImportError as exc:
        raise ImportError("pymetdecoder is not installed. Add it to requirements/base.in.") from exc
    
    try:
        decoded = pymet_synop.SYNOP().decode(raw_message.strip())
        return decoded
    except Exception as exc:
        raise ValueError(f"Failed to decode SYNOP message: {exc}") from exc


def extract_value_by_path(decoded: dict, path: str) -> Optional[float]:
    """
    Extract a numeric value from a decoded SYNOP dict using dot-notation path.
    Supports both dict traversal and list indexing via integer path segments.

    Examples:
      "air_temperature.value"          → scalar dict traversal
      "cloud_layer.0.cloud_height.value" → list index 0, then dict traversal

    Returns None if any segment is missing, an index is out of range,
    or the final leaf is not a numeric int/float.
    """
    obj = decoded
    for part in path.split("."):
        if obj is None:
            return None
        if isinstance(obj, list):
            try:
                obj = obj[int(part)]
            except (ValueError, IndexError):
                return None
        elif isinstance(obj, dict):
            obj = obj.get(part)
        else:
            return None
    
    if obj is None:
        return None
    if isinstance(obj, (int, float)):
        return float(obj)
    return None


def get_unmapped_elements(decoded: dict, synop_mappings) -> list[dict]:
    """
    Return FM12 elements that are present in decoded (non-None value) but are NOT
    covered by any entry in synop_mappings.  Used to show users what will be skipped.
    """
    mapped_paths = {m.fm12_element_path for m in synop_mappings}
    result = []
    for path, label in FM12_ELEMENT_PATH_CHOICES:
        if path in mapped_paths:
            continue
        value = extract_value_by_path(decoded, path)
        if value is not None:
            result.append({"path": path, "label": label, "value": value})
    return result


def sync_synop_mappings_for_station(station_link) -> int:
    """
    Create ManualObservationStationLinkVariableMapping rows for every global
    SynopParameterMapping that the station_link does not already have.

    show_in_direct_entry is derived (in priority order):
      1. Sibling station on the same connection that already has this adl_parameter mapped.
      2. FM12 metadata: is_coded=True → False, is_coded=False → True.
      3. Safe default: True.

    Returns the count of new rows created.
    """
    from .models import (
        SynopParameterMapping,
        ManualObservationStationLinkVariableMapping,
    )
    from .synop_wizard_data import _path_to_meta
    
    existing_param_ids = set(
        station_link.variable_mappings.values_list("adl_parameter_id", flat=True)
    )
    
    # Build sibling lookup: other stations on the same connection
    conn = station_link.network_connection
    sibling_qs = (
        ManualObservationStationLinkVariableMapping.objects
        .filter(station_link__network_connection=conn)
        .exclude(station_link=station_link)
        .values("adl_parameter_id", "show_in_direct_entry")
    )
    sibling_show: dict[int, bool] = {}
    for row in sibling_qs:
        # First sibling value wins; don't overwrite with a later sibling
        if row["adl_parameter_id"] not in sibling_show:
            sibling_show[row["adl_parameter_id"]] = row["show_in_direct_entry"]
    
    created = 0
    for spm in SynopParameterMapping.objects.select_related("adl_parameter", "source_unit").all():
        if spm.adl_parameter_id in existing_param_ids:
            continue
        # Derive show_in_direct_entry
        if spm.adl_parameter_id in sibling_show:
            show = sibling_show[spm.adl_parameter_id]
        else:
            meta = _path_to_meta.get(spm.fm12_element_path)
            show = (not meta["is_coded"]) if meta else True
        
        ManualObservationStationLinkVariableMapping.objects.create(
            station_link=station_link,
            adl_parameter=spm.adl_parameter,
            obs_parameter_unit=spm.source_unit,
            show_in_direct_entry=show,
        )
        created += 1
    
    return created


def build_submission_records_from_synop(decoded: dict, synop_mappings) -> list[dict]:
    """
    Given a decoded SYNOP dict and an iterable of SynopParameterMapping objects,
    return a list of dicts suitable for creating CollectorSubmissionRecord rows:
      [{"variable_mapping_id": ..., "value": ...}, ...]

    Skips mappings whose element path returns None.
    """
    records = []
    for mapping in synop_mappings:
        value = extract_value_by_path(decoded, mapping.fm12_element_path)
        if value is not None:
            records.append({
                "synop_mapping_id": mapping.id,
                "fm12_element_path": mapping.fm12_element_path,
                "adl_parameter_id": mapping.adl_parameter_id,
                "adl_parameter_name": mapping.adl_parameter.name,
                "source_unit_name": mapping.source_unit.name,
                "value": value,
            })
    return records
