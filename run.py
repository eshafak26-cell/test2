import os
import subprocess

import pandas as pd

from prepare import prepare_input, write_rule_file
from tools import last_trading_day, merge, read_json, replace_tokens, setting_to_args, write_cmd_file

def run(settings):
    made = make_cmd_file(settings)
    if settings["run_batchcal"]:
        subprocess.run(made["cmd_file"])


def make_cmd_file(settings):
    settings = prepare_input(settings, names)
    scen = scen_settings(settings)
    cmds = {}
    if "horizon_date" in settings:
        target_scn = horizon_scn(settings)
        rule = write_rule_file(settings)
        cmds["copy_rule"] = ["copy", "/Y", os.path.join(settings["scenarios_folder"], settings["sector_rule"]["rule_name"] + ".*"), settings["PP_SECTOR_DIR"]]
        cmds["scn_to_csv"] = build_cmd(scn_to_csv_settings(settings, target_scn))
        cmds["csv_to_scn"] = build_cmd(csv_to_scn_settings(settings, target_scn, rule))
        scen["scn"] = target_scn
    cmds["calc"] = build_cmd(scen)
    csv_file = os.path.splitext(scen["output_file"])[0] + "_cft*.csv"
    if not scen.get("cftscn", False):
        pf_to_csv = pf_to_csv_settings(scen)
        cmds["pf_to_csv"] = build_cmd(pf_to_csv)
        csv_file = pf_to_csv["output_file"]
    os.makedirs(os.path.dirname(scen["output_file"]), exist_ok=True)
    if settings["PPBDG_OUTPUT_PATH"] != "":
        os.makedirs(settings["PPBDG_OUTPUT_PATH"], exist_ok=True)
        os.makedirs(settings["PPBDG_LOG_PATH"], exist_ok=True)
    if settings["DEBUG_FILE"] != "":
        os.makedirs(os.path.dirname(settings["DEBUG_FILE"]), exist_ok=True)
    cmd_text = write_cmd_file(settings, cmds)
    return {"cmd_file": settings["cmd_file"], "cmd_text": cmd_text, "csv_file": csv_file}


def scen_settings(settings):
    scen = dict(settings)
    scen.update(settings["scenario"])
    scen["calculate"] = settings["calculate"] + " " + settings["scenario"]["calculate"]
    return scen


def horizon_scn(settings):
    name = os.path.splitext(os.path.basename(settings["scenario"]["scn"]))[0]
    return os.path.join(settings["scenarios_folder"], name + "_" + settings["pricing_date"] + "_" + settings["horizon_date"] + ".scn")


def scn_to_csv_settings(settings, target_scn):
    return {"BatchCal": settings["BatchCal"], "mode": "local", "scn_export": True,
            "input_file": settings["scenario"]["scn"],
            "output_file": os.path.splitext(target_scn)[0] + ".csv"}


def csv_to_scn_settings(settings, target_scn, rule):
    csv_to_scn = {"BatchCal": settings["BatchCal"], "mode": "local"}
    csv_to_scn.update(settings["horizon_scenario"])
    csv_to_scn.update({"scn_horizon_date": settings["horizon_date"], "secrule": rule, "scn_import": True,
                       "input_file": os.path.splitext(target_scn)[0] + ".csv",
                       "output_file": target_scn})
    return csv_to_scn


def pf_to_csv_settings(settings):
    csv_settings = {"BatchCal": settings["BatchCal"], "mode": "local", "nc": True}
    if "groupbyflds" in settings:
        csv_settings["groupbyflds"] = settings["groupbyflds"]
    csv_settings.update({
        "template": settings["template"],
        "input_file": settings["output_file"],
        "output_file": os.path.splitext(settings["output_file"])[0] + ".csv",
    })
    return csv_settings


def build_cmd(settings):
    cmd = [settings["BatchCal"]]
    for name in names["ppconfig"] + names["ppconfig_local"] + names["setfield"] + names["flag"]:
        if name in settings:
            cmd = cmd + setting_to_args(name, settings[name], names)
    if settings["mode"] == "remote":
        cmd = cmd + ["/remote"]
        for name in names["ppconfig"]:
            if name in settings and name not in config["remote"] and settings[name] != "":
                cmd = cmd + ["/remote_restart_calcs_with", name + "=" + str(settings[name])]
    cmd = cmd + [settings["input_file"], settings["output_file"]]
    return cmd


def gen_settings(run_types, override={}):
    all_settings = []
    for run_type in run_types:
        all_settings = all_settings + prepare_settings(run_type, override)
    return all_settings


def prepare_settings(run_type, override):
    not_common = ["temporary_override", "TBA", "PORT", "bridge_logging_settings", "pp_debug_settings", "remote", "run_type_settings"]
    common = {}
    for key in config:
        if key in not_common:
            continue
        if isinstance(config[key], dict):
            common.update(config[key])
        else:
            common[key] = config[key]

    run_section = config["run_type_settings"][run_type]
    override = merge(config["temporary_override"], override)

    switches = merge(merge(common, run_section), override)

    settings = merge(common, config[switches["positions"]])
    settings = merge(settings, config["bridge_logging_settings"])
    settings = merge(settings, config["pp_debug_settings"])
    if switches["mode"] == "remote":
        settings = merge(settings, config["remote"])
    settings = merge(settings, run_section)
    settings = merge(settings, override)
    settings["run_type"] = run_type

    bridge_logging = False
    for name in config["bridge_logging_settings"]:
        if settings[name] == "YES":
            bridge_logging = True
    if not bridge_logging:
        settings["PPBDG_OUTPUT_PATH"] = ""
        settings["PPBDG_LOG_PATH"] = ""
    if settings["DEBUG_LEVEL"] == "":
        settings["DEBUG_FILE"] = ""

    dates = [settings["pricing_date"]]
    if "pricing_dates" in settings:
        dates = settings["pricing_dates"]
        if isinstance(dates, dict):
            first = pd.to_datetime(dates["start"], format="%Y%m%d")
            last = pd.to_datetime(dates["end"], format="%Y%m%d")
            dates = pd.period_range(first, last, freq="M").to_timestamp(how="end").strftime("%Y%m%d").tolist()

    all_settings = []
    for date in dates:
        date = last_trading_day(date)
        one_day = dict(settings)
        one_day["pricing_date"] = date
        if one_day.get("User CDU Date") == "":
            one_day["User CDU Date"] = date[4:6] + "/" + date[6:8] + "/" + date[:4]
        tokens = {"{pricing_month}": date[:6]}
        for name in one_day:
            if isinstance(one_day[name], str):
                tokens["{" + name + "}"] = one_day[name]
        tokens = replace_tokens(tokens, tokens)
        all_settings.append(replace_tokens(one_day, tokens))
    return all_settings


config = read_json("config.json")
names = read_json("names.json")


if __name__ == "__main__":
    run_types = ["base"]
    settings_list = gen_settings(run_types)

    for settings in settings_list:
        run(settings)
