import pytest

from app.api.calculations import _build_network_from_elements as build_calc_network
from app.api.scenarios import _build_network_from_elements as build_scenario_network
from app.engine.iec60909 import calculate_short_circuit


EXPECTED_IK3_KA = {
    "bus_22kv_tpa": 7.2,
    "bus_6kv_tpa": 20.2,
    "bus_g1": 20.2,
    "bus_hc_slatina": 17.3,
}


ENERGA_ELEMENTS = {
    "busbars": [
        {"id": "bus_ssd", "Un": 22.0},
        {"id": "bus_22kv_tpa", "Un": 22.0},
        {"id": "bus_t1_lv", "Un": 6.3},
        {"id": "bus_t2_lv", "Un": 6.3},
        {"id": "bus_t7_lv", "Un": 6.3},
        {"id": "bus_6kv_tpa", "Un": 6.3},
        {"id": "bus_g1", "Un": 6.3},
        {"id": "bus_hc_slatina", "Un": 6.3},
        {"id": "bus_nn_ekv1", "Un": 0.4},
        {"id": "bus_nn_ekv2", "Un": 0.4},
    ],
    "external_grids": [
        {
            "id": "ext_ssd",
            "bus_id": "bus_ssd",
            "s_sc_max_mva": 199.3,
            "s_sc_min_mva": 199.3,
            "rx_max": 0.1,
            "c_max": 1.1,
            "c_min": 1.0,
        }
    ],
    "lines": [
        {
            "id": "line_22kv_ssd_tpa",
            "type": "cable",
            "bus_from": "bus_ssd",
            "bus_to": "bus_22kv_tpa",
            "length": 0.060,
            "r1_per_km": 0.125,
            "x1_per_km": 0.1131,
            "r0_per_km": 0.375,
            "x0_per_km": 0.1131,
            "parallel_cables": 2,
            "in_service": True,
        },
        {
            "id": "line_t1_6tpa",
            "type": "cable",
            "bus_from": "bus_t1_lv",
            "bus_to": "bus_6kv_tpa",
            "length": 0.020,
            "r1_per_km": 0.125,
            "x1_per_km": 0.1539,
            "r0_per_km": 0.375,
            "x0_per_km": 0.1539,
            "parallel_cables": 2,
            "in_service": True,
        },
        {
            "id": "line_t2_6tpa",
            "type": "cable",
            "bus_from": "bus_t2_lv",
            "bus_to": "bus_6kv_tpa",
            "length": 0.020,
            "r1_per_km": 0.125,
            "x1_per_km": 0.1539,
            "r0_per_km": 0.375,
            "x0_per_km": 0.1539,
            "parallel_cables": 2,
            "in_service": False,
        },
        {
            "id": "line_t7_6tpa",
            "type": "cable",
            "bus_from": "bus_t7_lv",
            "bus_to": "bus_6kv_tpa",
            "length": 0.020,
            "r1_per_km": 0.125,
            "x1_per_km": 0.0880,
            "r0_per_km": 0.375,
            "x0_per_km": 0.0880,
            "parallel_cables": 4,
            "in_service": True,
        },
        {
            "id": "line_g1",
            "type": "cable",
            "bus_from": "bus_6kv_tpa",
            "bus_to": "bus_g1",
            "length": 0.050,
            "r1_per_km": 0.125,
            "x1_per_km": 0.1131,
            "r0_per_km": 0.375,
            "x0_per_km": 0.1131,
            "parallel_cables": 3,
            "in_service": True,
        },
        {
            "id": "line_slatina",
            "type": "cable",
            "bus_from": "bus_6kv_tpa",
            "bus_to": "bus_hc_slatina",
            "length": 1.000,
            "r1_per_km": 0.1673,
            "x1_per_km": 0.1200,
            "r0_per_km": 0.502,
            "x0_per_km": 0.1200,
            "parallel_cables": 4,
            "in_service": True,
        },
    ],
    "transformers_2w": [
        {
            "id": "t1",
            "bus_hv": "bus_22kv_tpa",
            "bus_lv": "bus_t1_lv",
            "Sn": 10.0,
            "Un_hv": 22.0,
            "Un_lv": 6.3,
            "vk_percent": 7.08,
            "vkr_percent": 0.60915,
            "vector_group": "YNd11",
            "in_service": True,
        },
        {
            "id": "t2",
            "bus_hv": "bus_22kv_tpa",
            "bus_lv": "bus_t2_lv",
            "Sn": 10.0,
            "Un_hv": 22.0,
            "Un_lv": 6.3,
            "vk_percent": 7.08,
            "vkr_percent": 0.60915,
            "vector_group": "YNd11",
            "in_service": True,
        },
        {
            "id": "t7",
            "bus_hv": "bus_22kv_tpa",
            "bus_lv": "bus_t7_lv",
            "Sn": 10.0,
            "Un_hv": 22.0,
            "Un_lv": 6.3,
            "vk_percent": 7.08,
            "vkr_percent": 0.60915,
            "vector_group": "YNd11",
            "in_service": True,
        },
        {
            "id": "t101",
            "bus_hv": "bus_6kv_tpa",
            "bus_lv": "bus_nn_ekv1",
            "Sn": 0.63,
            "Un_hv": 6.3,
            "Un_lv": 0.4,
            "vk_percent": 6.0,
            "vkr_percent": 1.2142857142857142,
            "vector_group": "Dyn5",
            "in_service": True,
        },
        {
            "id": "t102",
            "bus_hv": "bus_6kv_tpa",
            "bus_lv": "bus_nn_ekv2",
            "Sn": 0.63,
            "Un_hv": 6.3,
            "Un_lv": 0.4,
            "vk_percent": 6.0,
            "vkr_percent": 1.2142857142857142,
            "vector_group": "Dyn5",
            "in_service": False,
        },
    ],
    "transformers_3w": [],
    "autotransformers": [],
    "impedances": [],
    "grounding_impedances": [],
    "psus": [],
    "generators": [
        {
            "id": "g1",
            "bus_id": "bus_g1",
            "Sn": 11.338,
            "Un": 6.3,
            "Xd_pp": 14.1,
            "Ra": 96,
            "cos_phi": 0.8,
            "in_service": True,
        },
        {
            "id": "hg1",
            "bus_id": "bus_hc_slatina",
            "Sn": 1.25,
            "Un": 6.3,
            "Xd_pp": 14.0,
            "Ra": 127,
            "cos_phi": 0.8,
            "in_service": True,
        },
    ],
    "motors": [
        {
            "id": "ekv1",
            "bus_id": "bus_nn_ekv1",
            "Un": 0.4,
            "input_mode": "power",
            "Pn": 400.0,
            "eta": 1.0,
            "cos_phi": 0.8,
            "Ia_In": 5.5,
            "pole_pairs": 4,
            "include_in_sc": True,
            "in_service": True,
        },
        {
            "id": "evk2",
            "bus_id": "bus_nn_ekv2",
            "Un": 0.4,
            "input_mode": "power",
            "Pn": 400.0,
            "eta": 1.0,
            "cos_phi": 0.8,
            "Ia_In": 5.5,
            "pole_pairs": 4,
            "include_in_sc": True,
            "in_service": False,
        },
    ],
}


def assert_within_one_percent(actual: float, expected: float) -> None:
    rel_error = abs(actual - expected) / expected
    assert rel_error <= 0.01, (
        f"Expected {expected:.3f} kA, got {actual:.3f} kA "
        f"(error {rel_error * 100:.2f}%)"
    )


@pytest.mark.parametrize("builder", [build_calc_network, build_scenario_network])
def test_large_generator_ra_values_are_interpreted_as_milliohms(builder):
    network = builder(ENERGA_ELEMENTS)

    g1 = network.get_element("g1")
    hg1 = network.get_element("hg1")

    assert g1 is not None and hg1 is not None
    assert g1.Ra == pytest.approx((0.096 / ((6.3 ** 2) / 11.338)) * 100.0, rel=1e-6)
    assert hg1.Ra == pytest.approx((0.127 / ((6.3 ** 2) / 1.25)) * 100.0, rel=1e-6)


@pytest.mark.parametrize("builder", [build_calc_network, build_scenario_network])
def test_energa_reference_case_matches_ik3_targets(builder):
    network = builder(ENERGA_ELEMENTS)
    run = calculate_short_circuit(
        network,
        ["Ik3"],
        list(EXPECTED_IK3_KA.keys()),
        "max",
    )

    assert run.is_success, run.errors
    actual = {result.bus_id: result.Ik for result in run.results}

    for bus_id, expected in EXPECTED_IK3_KA.items():
        assert_within_one_percent(actual[bus_id], expected)