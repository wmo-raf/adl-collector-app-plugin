from adl_collector_app_plugin.synop_utils import extract_value_by_path, FM12_ELEMENT_PATH_CHOICES


# ---------------------------------------------------------------------------
# extract_value_by_path — core traversal tests
# ---------------------------------------------------------------------------

def test_dict_only_path():
    decoded = {"air_temperature": {"value": 25.5, "unit": "Cel"}}
    assert extract_value_by_path(decoded, "air_temperature.value") == 25.5


def test_list_index_happy_path():
    decoded = {"a": [{"b": 5.0}]}
    assert extract_value_by_path(decoded, "a.0.b") == 5.0


def test_list_index_second_element():
    decoded = {"a": [{"b": 1.0}, {"b": 2.0}]}
    assert extract_value_by_path(decoded, "a.1.b") == 2.0


def test_list_index_out_of_range():
    decoded = {"a": [{"b": 1}]}
    assert extract_value_by_path(decoded, "a.2.b") is None


def test_numeric_segment_against_dict_fallback():
    # Digit-string key in a dict should still work (backward compat).
    decoded = {"a": {"0": 3.0}}
    assert extract_value_by_path(decoded, "a.0") == 3.0


def test_string_leaf_in_list_element_returns_none():
    # cloud_genus.value is a string like "Ci"; expect None.
    decoded = {"cloud_layer": [{"cloud_genus": {"value": "Ci", "_code": 0}}]}
    assert extract_value_by_path(decoded, "cloud_layer.0.cloud_genus.value") is None


def test_string_leaf_code_returns_float():
    # cloud_genus._code is an int → should return it as float.
    decoded = {"cloud_layer": [{"cloud_genus": {"value": "Ci", "_code": 0}}]}
    assert extract_value_by_path(decoded, "cloud_layer.0.cloud_genus._code") == 0.0


def test_past_weather_index_0():
    decoded = {"past_weather": [{"value": 2, "_table": "4531"}, {"value": 3, "_table": "4531"}]}
    assert extract_value_by_path(decoded, "past_weather.0.value") == 2.0


def test_past_weather_index_1():
    decoded = {"past_weather": [{"value": 2, "_table": "4531"}, {"value": 3, "_table": "4531"}]}
    assert extract_value_by_path(decoded, "past_weather.1.value") == 3.0


def test_cloud_layer_height_value():
    decoded = {
        "cloud_layer": [
            {"cloud_cover": {"_code": 6}, "cloud_genus": {"_code": 0}, "cloud_height": {"value": 600, "_code": 20}},
            {"cloud_cover": {"_code": 3}, "cloud_genus": {"_code": 9}, "cloud_height": {"value": 3000, "_code": 60}},
        ]
    }
    assert extract_value_by_path(decoded, "cloud_layer.0.cloud_height.value") == 600.0
    assert extract_value_by_path(decoded, "cloud_layer.1.cloud_height.value") == 3000.0


def test_cloud_layer_index_out_of_range():
    decoded = {"cloud_layer": [{"cloud_cover": {"_code": 6}}]}
    assert extract_value_by_path(decoded, "cloud_layer.5.cloud_cover._code") is None


def test_missing_top_level_key_returns_none():
    assert extract_value_by_path({}, "air_temperature.value") is None


def test_intermediate_none_returns_none():
    decoded = {"cloud_layer": [{"cloud_height": None}]}
    assert extract_value_by_path(decoded, "cloud_layer.0.cloud_height.value") is None


# ---------------------------------------------------------------------------
# FM12_ELEMENT_PATH_CHOICES integrity checks
# ---------------------------------------------------------------------------

def test_choices_count():
    assert len(FM12_ELEMENT_PATH_CHOICES) == 70


def test_choices_are_unique_paths():
    paths = [p for p, _ in FM12_ELEMENT_PATH_CHOICES]
    assert len(paths) == len(set(paths)), "Duplicate paths in FM12_ELEMENT_PATH_CHOICES"


def test_all_choices_have_non_empty_labels():
    for path, label in FM12_ELEMENT_PATH_CHOICES:
        assert label.strip(), f"Empty label for path '{path}'"


def test_list_indexed_paths_present():
    paths = {p for p, _ in FM12_ELEMENT_PATH_CHOICES}
    assert "past_weather.0.value" in paths
    assert "past_weather.1.value" in paths
    assert "cloud_layer.0.cloud_height.value" in paths
    assert "cloud_layer.3.cloud_genus._code" in paths
    assert "cloud_base_below_station.0.upper_surface_altitude.value" in paths
    assert "cloud_base_below_station.2.description._code" in paths
