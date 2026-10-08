from run import gen_settings, run
from tools import merge

csv_two = ".\\data\\Port\\two_secs.csv"
base_pf = ".\\outputs\\PORT\\1008_T0\\results\\base_calc\\base_{pricing_date}.pf"

base_override = {"mode": "local", "positions": "PORT", "input_file": csv_two}

scn_override = {
    "mode": "local", "positions": "PORT", "input_file": base_pf,
    "nc": True, "calculate": "", "clearcalcselections": False, "prc_anchor": "",
    "mr_nofit": False, "mr": "", "mr_alt": "", "Book Price": "", "Calc P/Y": "",
    "PP_OAS_CACHE": "", "PP_DISABLE_ALL_CALIB_FILE_CACHING": "",
    "groupbyflds": "", "User CDU Date": {}, "Use History": ""
}

min_override = {"mode": "local", "positions": "PORT", "input_file": base_pf, "nc": True, "calculate": "",
                "Use History": "", "User CDU Date": {}}

horizon_log = {"x_PRINT_SECONDARY_RATES": "YES", "x_PRINT_PRIMARY_RATES": "YES",
               "x_HPI_OUT": "YES"}


def without(d, *keys):
    d = dict(d)
    for key in keys:
        del d[key]
    return d


def horizon_test(curve_type):
    return merge(merge(scn_override, horizon_log), {"horizon_scenario": {"scn_curve_type": curve_type}})


tests = [
    ("1008_T0",   "base",      base_override),
    ("1008_T0b",  "base",      base_override),
    ("1008_T1",   "oas_shock", scn_override),
    ("1008_T1b",  "oas_shock", scn_override),
    ("1008_TA",   "oas_shock", min_override),
    ("1008_TA1",  "oas_shock", merge(scn_override, {"clearcalcselections": True})),
    ("1008_TA2",  "oas_shock", merge(scn_override, {"prc_anchor": "Price"})),
    ("1008_TA3a", "oas_shock", merge(scn_override, {"Book Price": "$Price"})),
    ("1008_TA3b", "oas_shock", merge(scn_override, {"Calc P/Y": "N"})),
    ("1008_TA4a", "oas_shock", without(scn_override, "mr", "mr_nofit", "mr_alt")),
    ("1008_TA4b", "oas_shock", without(scn_override, "PP_OAS_CACHE", "PP_DISABLE_ALL_CALIB_FILE_CACHING")),
    ("1008_T3",   "oas_shock", without(scn_override, "User CDU Date")),
    ("1008_T5",   "oas_shock", without(scn_override, "groupbyflds")),
    ("1008_TB2",  "oas_shock", merge(scn_override, {"scenario": {"scn_anchor": "Price Constant"}})),
    ("1008_TF3",  "oas_shock", merge(scn_override, {"scenario": {"calculate": "/scnoad /scnoaspd /scnmd /scnvd /scnspd /scnoappspd"}})),
    ("1008_TF4",  "oas_shock", merge(scn_override, {"scenario": {"calculate": "/scnoad /scnoaspd /scnmd /scnvd /scnspd /scnpd"}})),
    ("1008_TS1",  "oas_shock", merge(scn_override, {"calculate": "/skipoutput", "scnrpt_file": "{output_dir}\\results\\oas_shock_calc\\report.csv"})),
    ("1008_TR",   "spot",      scn_override),
    ("1008_TO",   "base",      merge(base_override, {"Use History": ""})),
    ("1008_L1",   "logging",   base_override),
    ("1008_L3",   "logging",   merge(base_override, {"WellsHpiOverrideFile": ""})),
    ("1008_HC0",  "horizon",   horizon_test("PARBOND")),
    ("1008_HC1",  "horizon",   horizon_test("Par Bond")),
    ("1008_HC2",  "horizon",   horizon_test("Spot")),
    ("1008_HC3",  "horizon",   horizon_test("Forward")),
    ("1008_HC4",  "horizon",   horizon_test("Realized Forward")),
    ("1008_H3",   "horizon",   merge(horizon_test("Par Bond"), {"horizon_date": "20261031"})),
    ("1008_C1b",  "bookincome", merge(scn_override, {"alm_flag": "calcmv"})),
    ("1008_P1",   "prepay_dials", merge(base_override, {"groupbyflds": ""})),
    ("1008_P2",   "prepay_breakdown", merge(base_override, {"groupbyflds": ""})),
    ("1008_TS",   "time_series", base_override),
    ("1008_T2",   "oas_shock", without(scn_override, "Use History")),
    ("1008_T2b",  "oas_shock", merge(scn_override, {"Use History": "N"})),
]

for run_name, run_type, override in tests:
    override = merge(override, {"run_name": run_name})
    for settings in gen_settings([run_type], override):
        run(settings)
