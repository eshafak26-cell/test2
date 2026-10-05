import io
import os

import pandas as pd

from tools import read_input, write_input


def prepare_input(settings, names):
    settings = dict(settings)
    if not os.path.exists(settings["mr"]):
        settings["mr"] = settings["mr_alt"]
    dials = []
    fields = []
    for name in settings:
        if name in names["setfield"] and isinstance(settings[name], list):
            dials.append(name)
        elif is_field(settings[name]):
            fields.append(name)
    if dials != []:
        settings["input_file"] = write_dial_input(settings, dials)
    if "scenario_rows" in settings:
        settings["input_file"] = write_scenario_input(settings)
    if fields != []:
        settings["input_file"] = write_collat_input(settings, fields)
    return settings


def is_field(value):
    if isinstance(value, dict):
        return "range" in value or "values" in value
    if isinstance(value, list) and len(value) == 3:
        return not isinstance(value[0], str)
    return False


def range_values(start_end_step):
    start, end, step = start_end_step
    count = int(round((end - start) / step, 9)) + 1
    values = []
    for i in range(count):
        values.append(round(start + i * step, 6))
    return values


def number_text(number):
    number = round(float(number), 6)
    if number == int(number):
        return str(int(number))
    return str(number)


def generated_input(settings):
    return os.path.join(settings["output_dir"], "inputs", settings["run_type"] + "_" + settings["pricing_date"] + ".csv")


def write_dial_input(settings, dials):
    df = read_input(settings["input_file"])
    for dial in dials:
        if dial not in df.columns:
            df[dial] = ""

    parts = []
    all_ones_written = False
    for dial in dials:
        if not settings[dial]:
            continue

        values = []
        for number in range_values(settings[dial]):
            value = number_text(number)
            if value == "1" and all_ones_written:
                continue
            values.append(value)
        if "1" in values:
            all_ones_written = True

        if settings["ramp_month"] != "":
            ramp = "/" + str(settings["ramp_month"]) + ",1"
            values = [value + ramp for value in values]

        row_index = df.index.tolist() * len(values)
        part = df.loc[row_index].copy()
        part[dials] = "1"
        part[dial] = (
            pd.Series(values, dtype=object)
            .repeat(len(df))
            .to_numpy()
        )
        parts.append(part)

    result = pd.concat(parts + [df], ignore_index=True)
    return write_input(result, generated_input(settings))


def write_rule_file(settings):
    rule = settings["sector_rule"]
    first = pd.Timestamp(settings["pricing_date"]) + pd.DateOffset(months=1) + pd.offsets.MonthEnd(0)
    last = pd.Timestamp(settings["horizon_date"]) + pd.offsets.MonthEnd(0)
    days = pd.period_range(first, last, freq="M").to_timestamp(how="end").strftime("%Y%m%d").tolist()
    if settings["horizon_date"] not in days:
        days.append(settings["horizon_date"])

    blocks = []
    for day in days:
        block_name = rule["block_name_prefix"] + day
        tests = []
        for sec_type in rule["sec_types"]:
            tests.append('"' + rule["sec_type_field"] + '" == "' + sec_type + '"')
        condition = "((" + " || ".join(tests) + ') && "' + rule["horizon_date_field"] + '" == "' + day[4:6] + "/" + day[6:8] + "/" + day[:4] + '")'
        lines = [
            block_name,
            condition,
            "@Action_List_Start",
            rule["scenario_name_field"] + "," + block_name,
            rule["scenario_date_field"] + "," + day[:6] + "01",
            rule["is_horizon_field"] + "," + rule["is_horizon_value"],
            "@Action_List_End",
        ]
        blocks.append("\n".join(lines))

    os.makedirs(settings["scenarios_folder"], exist_ok=True)
    rule_path = os.path.join(settings["scenarios_folder"], rule["rule_name"] + ".rul")
    io.open(rule_path, "w", encoding="utf-8").write("\n".join(blocks))
    name = rule["rule_name"]

    if rule["user_rules"] != []:
        stems = [rule["rule_name"]] + rule["user_rules"]
        set_path = os.path.join(settings["scenarios_folder"], rule["rule_name"] + ".set")
        io.open(set_path, "w", encoding="utf-8").write("\n".join(stems))
        name = rule["rule_name"] + ".set"
    return name


def write_scenario_input(settings):
    df = read_input(settings["input_file"])
    parts = [df.iloc[:0]]

    for label in settings["scenario_rows"]:
        part = df.copy()
        for column, number in zip(settings["scenario_columns"], settings["scenario_rows"][label]):
            part[column] = number_text(number)
        part[settings["scenario_label_column"]] = label
        parts.append(part)

    result = pd.concat(parts, ignore_index=True)
    return write_input(result, generated_input(settings))


def write_collat_input(settings, fields):
    df = read_input(settings["input_file"])
    df_numbers = df.apply(pd.to_numeric, errors="coerce")
    parts = [df.iloc[:0]]

    for field in fields:
        rule = settings[field]
        if isinstance(rule, list):
            rule = {"range": rule}
        if "values" in rule:
            values = rule["values"]
        else:
            values = range_values(rule["range"])

        rows = df.index.repeat(len(values))
        part = df.loc[rows].reset_index(drop=True)
        numbers = df_numbers.loc[rows].reset_index(drop=True)
        numbers["value"] = values * len(df)

        if "keep_rows_when" in rule:
            keep = numbers.eval(rule["keep_rows_when"])
            part = part.loc[keep]
            numbers = numbers.loc[keep]

        part[field] = numbers["value"].map(number_text)
        for other in rule:
            if other in ["range", "values", "keep_rows_when"]:
                continue
            if isinstance(rule[other], str):
                numbers[other] = numbers.eval(rule[other])
            else:
                numbers[other] = rule[other]
            part[other] = numbers[other].map(number_text)

        part[settings["scenario_label_column"]] = field
        parts.append(part)

    result = pd.concat(parts, ignore_index=True)
    return write_input(result, generated_input(settings))
