"""
WMO code table constants for SYNOP FM-12 coded parameters.

Each table is a list of (integer_code, display_label) tuples matching the WMO Manual
on Codes (WMO-No. 306). The ``WMO_CODE_TABLES`` dict maps a table identifier string
(as stored in ``DataParameter.wmo_code_table``) to its choices list.

These are used by the manual entry form (OfficeEntryView) to render <select> dropdowns
for coded parameters instead of free number inputs.

Where pymetdecoder ships a ``CodeTableLookup`` subclass with a ``_VALUES`` list for a
table, ``_from_pymetdecoder()`` extracts the choices automatically so we avoid
duplicating static data. Tables not in pymetdecoder, or those that use complex
range-based decode logic (no ``_VALUES``), are hardcoded below.
"""


def _from_pymetdecoder(table_id: str) -> list[tuple[int, str]]:
    """Return (code, label) pairs from a pymetdecoder CodeTableLookup._VALUES list."""
    try:
        import pymetdecoder.code_tables as _ct
        for _name in dir(_ct):
            _cls = getattr(_ct, _name)
            if (isinstance(_cls, type)
                    and getattr(_cls, '_TABLE', None) == table_id
                    and hasattr(_cls, '_VALUES')):
                return [(i, str(v)) for i, v in enumerate(_cls._VALUES)]
    except Exception:
        pass
    return []


# Table 2700 — Cloud amount in oktas (N, Nh)
WMO_TABLE_2700 = [
    (0, "0 — Clear (0 oktas)"),
    (1, "1 — 1 okta or less, but not zero"),
    (2, "2 — 2 oktas"),
    (3, "3 — 3 oktas"),
    (4, "4 — 4 oktas"),
    (5, "5 — 5 oktas"),
    (6, "6 — 6 oktas"),
    (7, "7 — 7 oktas or more, but not 8"),
    (8, "8 — Overcast (8 oktas)"),
    (9, "9 — Sky obscured or cloud amount cannot be estimated"),
]

# Table 0513 — Low cloud type (CL)
WMO_TABLE_0513 = [
    (0, "0 — No low cloud"),
    (1, "1 — Cu humilis or Cu fractus (other than bad weather)"),
    (2, "2 — Cu mediocris or Cu congestus"),
    (3, "3 — Cb calvus, no cirriform cloud"),
    (4, "4 — Sc cumulogenitus"),
    (5, "5 — Sc other than Sc cumulogenitus"),
    (6, "6 — St nebulosus or St fractus (other than bad weather)"),
    (7, "7 — St fractus or Cu fractus (bad weather)"),
    (8, "8 — Cu and Sc (Sc not cumulogenitus), bases at different levels"),
    (9, "9 — Cb capillatus (often with anvil)"),
]

# Table 0515 — Middle cloud type (CM)
WMO_TABLE_0515 = [
    (0, "0 — No middle cloud"),
    (1, "1 — As translucidus"),
    (2, "2 — As opacus or Ns"),
    (3, "3 — Ac translucidus (single level)"),
    (4, "4 — Ac patches, continuously changing"),
    (5, "5 — Ac translucidus in bands or Ac opacus/translucidus/floccus (progressive)"),
    (6, "6 — Ac cumulogenitus"),
    (7, "7 — Ac (double layer), or Ac with As or Ns"),
    (8, "8 — Ac castellanus or Ac floccus"),
    (9, "9 — Ac of chaotic sky"),
]

# Table 0509 — High cloud type (CH)
WMO_TABLE_0509 = [
    (0, "0 — No high cloud"),
    (1, "1 — Ci fibratus or Ci uncinus, not progressively invading"),
    (2, "2 — Ci spissatus, in patches or entangled sheaves, not Cb"),
    (3, "3 — Ci spissatus cumulonimbogenitus"),
    (4, "4 — Ci fibratus or Ci uncinus, progressively invading the sky"),
    (5, "5 — Cs invading sky, below 45° altitude"),
    (6, "6 — Cs invading sky, above 45° altitude"),
    (7, "7 — Cs covering whole sky"),
    (8, "8 — Cs not progressively invading and not covering whole sky"),
    (9, "9 — Cc alone or Cc with some Ci or Cs"),
]

# Table 0200 — Pressure tendency characteristic (a)
WMO_TABLE_0200 = [
    (0, "0 — Increasing, then decreasing"),
    (1, "1 — Increasing, then steady; or increasing, then increasing more slowly"),
    (2, "2 — Increasing (steadily or unsteadily)"),
    (3, "3 — Decreasing or steady, then increasing; or increasing, then increasing more rapidly"),
    (4, "4 — Steady (no change)"),
    (5, "5 — Decreasing, then increasing"),
    (6, "6 — Decreasing, then steady; or decreasing, then decreasing more slowly"),
    (7, "7 — Decreasing (steadily or unsteadily)"),
    (8, "8 — Steady or increasing, then decreasing; or decreasing, then decreasing more rapidly"),
]

# Table 4677 — Present weather (ww) — abbreviated to most common codes
# Full table has 100 codes; include all for completeness
WMO_TABLE_4677 = [
    (0,  "00 — Cloud development not observed or not observable"),
    (1,  "01 — Clouds generally dissolving or becoming less developed"),
    (2,  "02 — State of sky on the whole unchanged"),
    (3,  "03 — Clouds generally forming or developing"),
    (4,  "04 — Visibility reduced by smoke"),
    (5,  "05 — Haze"),
    (6,  "06 — Widespread dust in suspension, not raised by wind"),
    (7,  "07 — Dust or sand raised by wind at or near station"),
    (8,  "08 — Well-developed dust whirl(s)"),
    (9,  "09 — Duststorm or sandstorm within sight"),
    (10, "10 — Mist"),
    (11, "11 — Patches of shallow fog or ice fog"),
    (12, "12 — More or less continuous shallow fog or ice fog"),
    (13, "13 — Lightning visible, no thunder heard"),
    (14, "14 — Precipitation within sight, not reaching ground"),
    (15, "15 — Precipitation within sight, reaching ground, distant"),
    (16, "16 — Precipitation within sight, reaching ground, near but not at station"),
    (17, "17 — Thunderstorm, but no precipitation at the time of observation"),
    (18, "18 — Squalls"),
    (19, "19 — Funnel cloud(s)"),
    (20, "20 — Drizzle (not freezing) or snow grains, not as showers"),
    (21, "21 — Rain (not freezing), not as showers"),
    (22, "22 — Snow, not as showers"),
    (23, "23 — Rain and snow or ice pellets, not as showers"),
    (24, "24 — Freezing drizzle or freezing rain, not as showers"),
    (25, "25 — Shower(s) of rain"),
    (26, "26 — Shower(s) of snow or rain and snow"),
    (27, "27 — Shower(s) of hail or rain and hail"),
    (28, "28 — Fog or ice fog"),
    (29, "29 — Thunderstorm (with or without precipitation)"),
    (30, "30 — Slight or moderate duststorm/sandstorm — decreasing"),
    (31, "31 — Slight or moderate duststorm/sandstorm — no appreciable change"),
    (32, "32 — Slight or moderate duststorm/sandstorm — increasing"),
    (33, "33 — Severe duststorm/sandstorm — decreasing"),
    (34, "34 — Severe duststorm/sandstorm — no appreciable change"),
    (35, "35 — Severe duststorm/sandstorm — increasing"),
    (36, "36 — Slight or moderate drifting snow — below eye level"),
    (37, "37 — Heavy drifting snow — below eye level"),
    (38, "38 — Slight or moderate blowing snow — above eye level"),
    (39, "39 — Heavy blowing snow — above eye level"),
    (40, "40 — Fog or ice fog at a distance"),
    (41, "41 — Fog or ice fog in patches"),
    (42, "42 — Fog or ice fog, sky visible — thinning"),
    (43, "43 — Fog or ice fog, sky invisible — thinning"),
    (44, "44 — Fog or ice fog, sky visible — no appreciable change"),
    (45, "45 — Fog or ice fog, sky invisible — no appreciable change"),
    (46, "46 — Fog or ice fog, sky visible — thickening"),
    (47, "47 — Fog or ice fog, sky invisible — thickening"),
    (48, "48 — Fog, depositing rime, sky visible"),
    (49, "49 — Fog, depositing rime, sky invisible"),
    (50, "50 — Drizzle, not freezing, intermittent — slight"),
    (51, "51 — Drizzle, not freezing, continuous — slight"),
    (52, "52 — Drizzle, not freezing, intermittent — moderate"),
    (53, "53 — Drizzle, not freezing, continuous — moderate"),
    (54, "54 — Drizzle, not freezing, intermittent — heavy"),
    (55, "55 — Drizzle, not freezing, continuous — heavy"),
    (56, "56 — Drizzle, freezing — slight"),
    (57, "57 — Drizzle, freezing — moderate or heavy"),
    (58, "58 — Drizzle and rain — slight"),
    (59, "59 — Drizzle and rain — moderate or heavy"),
    (60, "60 — Rain, not freezing, intermittent — slight"),
    (61, "61 — Rain, not freezing, continuous — slight"),
    (62, "62 — Rain, not freezing, intermittent — moderate"),
    (63, "63 — Rain, not freezing, continuous — moderate"),
    (64, "64 — Rain, not freezing, intermittent — heavy"),
    (65, "65 — Rain, not freezing, continuous — heavy"),
    (66, "66 — Freezing rain — slight"),
    (67, "67 — Freezing rain — moderate or heavy"),
    (68, "68 — Rain or drizzle and snow — slight"),
    (69, "69 — Rain or drizzle and snow — moderate or heavy"),
    (70, "70 — Intermittent fall of snowflakes — slight"),
    (71, "71 — Continuous fall of snowflakes — slight"),
    (72, "72 — Intermittent fall of snowflakes — moderate"),
    (73, "73 — Continuous fall of snowflakes — moderate"),
    (74, "74 — Intermittent fall of snowflakes — heavy"),
    (75, "75 — Continuous fall of snowflakes — heavy"),
    (76, "76 — Diamond dust (with or without fog)"),
    (77, "77 — Snow grains (with or without fog)"),
    (78, "78 — Isolated star-like snow crystals (with or without fog)"),
    (79, "79 — Ice pellets"),
    (80, "80 — Rain shower(s) — slight"),
    (81, "81 — Rain shower(s) — moderate or heavy"),
    (82, "82 — Rain shower(s) — violent"),
    (83, "83 — Shower(s) of rain and snow mixed — slight"),
    (84, "84 — Shower(s) of rain and snow mixed — moderate or heavy"),
    (85, "85 — Snow shower(s) — slight"),
    (86, "86 — Snow shower(s) — moderate or heavy"),
    (87, "87 — Shower(s) of snow pellets or small hail — slight"),
    (88, "88 — Shower(s) of snow pellets or small hail — moderate or heavy"),
    (89, "89 — Shower(s) of hail — slight, no thunder"),
    (90, "90 — Shower(s) of hail — moderate or heavy, no thunder"),
    (91, "91 — Slight rain at time of obs; thunderstorm during past hour"),
    (92, "92 — Moderate or heavy rain at time of obs; thunderstorm during past hour"),
    (93, "93 — Slight snow/rain-snow/hail at time of obs; thunderstorm during past hour"),
    (94, "94 — Moderate or heavy snow/rain-snow/hail; thunderstorm during past hour"),
    (95, "95 — Thunderstorm, slight or moderate, no hail"),
    (96, "96 — Thunderstorm, slight or moderate, with hail"),
    (97, "97 — Heavy thunderstorm, no hail"),
    (98, "98 — Thunderstorm combined with duststorm or sandstorm"),
    (99, "99 — Heavy thunderstorm with hail"),
]

# Table 0901 — Past weather (W1, W2)
WMO_TABLE_0901 = [
    (0, "0 — Cloud covering ½ or less of the sky throughout the period"),
    (1, "1 — Cloud covering more than ½ of the sky during part of the period and ½ or less during part"),
    (2, "2 — Cloud covering more than ½ of the sky throughout the period"),
    (3, "3 — Sandstorm, duststorm, or drifting/blowing snow"),
    (4, "4 — Fog or thick haze"),
    (5, "5 — Drizzle"),
    (6, "6 — Rain"),
    (7, "7 — Snow or mixed rain and snow"),
    (8, "8 — Shower(s)"),
    (9, "9 — Thunderstorm(s) with or without precipitation"),
]

# ---------------------------------------------------------------------------
# Table 0500 — Cloud genus (Ci Cc Cs Ac As Ns Sc St Cu Cb)
# Extracted from pymetdecoder's CodeTable0500._VALUES at import time.
# ---------------------------------------------------------------------------
WMO_TABLE_0500: list[tuple[int, str]] = _from_pymetdecoder("0500")

# ---------------------------------------------------------------------------
# Table 0552 — Description of cloud top (cloud base below station level)
# Extracted from pymetdecoder's CodeTable0552._VALUES at import time.
# ---------------------------------------------------------------------------
WMO_TABLE_0552: list[tuple[int, str]] = _from_pymetdecoder("0552")

# ---------------------------------------------------------------------------
# Table 4531 — State of weather, past period (W1 and W2)
# Same 0–9 content as the existing WMO_TABLE_0901 (past weather codes).
# The pymetdecoder decoded dict stores _table="4531" for past_weather elements,
# so operators must reference "4531" when creating a DataParameter for W1/W2.
# ---------------------------------------------------------------------------
WMO_TABLE_4531 = WMO_TABLE_0901  # reuse — identical codes

# ---------------------------------------------------------------------------
# Table 1677 — Height of base of cloud layer (hh code in group 8NhClhh)
# pymetdecoder uses complex range logic (no _VALUES), so hardcoded here.
# Codes 51–55 are unused per WMO-306 and are omitted.
# ---------------------------------------------------------------------------
WMO_TABLE_1677: list[tuple[int, str]] = [
    (0,  "0 — < 30 m"),
    (1,  "1 — 30 m"),
    (2,  "2 — 60 m"),
    (3,  "3 — 90 m"),
    (4,  "4 — 120 m"),
    (5,  "5 — 150 m"),
    (6,  "6 — 180 m"),
    (7,  "7 — 210 m"),
    (8,  "8 — 240 m"),
    (9,  "9 — 270 m"),
    (10, "10 — 300 m"),
    (11, "11 — 330 m"),
    (12, "12 — 360 m"),
    (13, "13 — 390 m"),
    (14, "14 — 420 m"),
    (15, "15 — 450 m"),
    (16, "16 — 480 m"),
    (17, "17 — 510 m"),
    (18, "18 — 540 m"),
    (19, "19 — 570 m"),
    (20, "20 — 600 m"),
    (21, "21 — 630 m"),
    (22, "22 — 660 m"),
    (23, "23 — 690 m"),
    (24, "24 — 720 m"),
    (25, "25 — 750 m"),
    (26, "26 — 780 m"),
    (27, "27 — 810 m"),
    (28, "28 — 840 m"),
    (29, "29 — 870 m"),
    (30, "30 — 900 m"),
    (31, "31 — 930 m"),
    (32, "32 — 960 m"),
    (33, "33 — 990 m"),
    (34, "34 — 1 020 m"),
    (35, "35 — 1 050 m"),
    (36, "36 — 1 080 m"),
    (37, "37 — 1 110 m"),
    (38, "38 — 1 140 m"),
    (39, "39 — 1 170 m"),
    (40, "40 — 1 200 m"),
    (41, "41 — 1 230 m"),
    (42, "42 — 1 260 m"),
    (43, "43 — 1 290 m"),
    (44, "44 — 1 320 m"),
    (45, "45 — 1 350 m"),
    (46, "46 — 1 380 m"),
    (47, "47 — 1 410 m"),
    (48, "48 — 1 440 m"),
    (49, "49 — 1 470 m"),
    (50, "50 — 1 500 m"),
    # 51–55 not used per WMO-306
    (56, "56 — 1 800 m"),
    (57, "57 — 2 100 m"),
    (58, "58 — 2 400 m"),
    (59, "59 — 2 700 m"),
    (60, "60 — 3 000 m"),
    (61, "61 — 3 300 m"),
    (62, "62 — 3 600 m"),
    (63, "63 — 3 900 m"),
    (64, "64 — 4 200 m"),
    (65, "65 — 4 500 m"),
    (66, "66 — 4 800 m"),
    (67, "67 — 5 100 m"),
    (68, "68 — 5 400 m"),
    (69, "69 — 5 700 m"),
    (70, "70 — 6 000 m"),
    (71, "71 — 6 300 m"),
    (72, "72 — 6 600 m"),
    (73, "73 — 6 900 m"),
    (74, "74 — 7 200 m"),
    (75, "75 — 7 500 m"),
    (76, "76 — 7 800 m"),
    (77, "77 — 8 100 m"),
    (78, "78 — 8 400 m"),
    (79, "79 — 8 700 m"),
    (80, "80 — 9 000 m"),
    (81, "81 — 10 500 m"),
    (82, "82 — 12 000 m"),
    (83, "83 — 13 500 m"),
    (84, "84 — 15 000 m"),
    (85, "85 — 16 500 m"),
    (86, "86 — 18 000 m"),
    (87, "87 — 19 500 m"),
    (88, "88 — 21 000 m"),
    (89, "89 — > 21 000 m"),
    # 90–99: special range codes (used at sea, regulation 12.2.1.3.2)
    (90, "90 — 0–49 m"),
    (91, "91 — 50–99 m"),
    (92, "92 — 100–199 m"),
    (93, "93 — 200–299 m"),
    (94, "94 — 300–599 m"),
    (95, "95 — 600–999 m"),
    (96, "96 — 1 000–1 499 m"),
    (97, "97 — 1 500–1 999 m"),
    (98, "98 — 2 000–2 499 m"),
    (99, "99 — ≥ 2 500 m"),
]

WMO_CODE_TABLES: dict[str, list[tuple[int, str]]] = {
    "2700": WMO_TABLE_2700,
    "0513": WMO_TABLE_0513,
    "0515": WMO_TABLE_0515,
    "0509": WMO_TABLE_0509,
    "0200": WMO_TABLE_0200,
    "4677": WMO_TABLE_4677,
    "0901": WMO_TABLE_0901,
    # new tables for list-valued SYNOP fields
    "4531": WMO_TABLE_4531,
    "0500": WMO_TABLE_0500,
    "0552": WMO_TABLE_0552,
    "1677": WMO_TABLE_1677,
}
