import glob
import json
import os
from datetime import datetime
from config.root_settings import DAILY_DIFFS_PATH


def get_html_file_count_for_path(path):
    if os.path.exists(path):
        return len(glob.glob1(path, "*.html"))
    return 0


def generate_totals_for_path(path, key_prefix=''):
    counts = {}
    if os.path.exists(path):
        for _, dirs, _ in os.walk(path):
            for directory in dirs:
                counts[key_prefix + directory] = get_html_file_count_for_path(path + directory)
    return counts


def compute_diff(dict1, dict2):
    output_diffs = {}
    try:
        for key in dict2.keys():
            if isinstance(dict2[key], dict):
                output_diffs[key] = compute_diff(dict1[key], dict2[key])
            else:
                dict1_current_value = 0

                if key in dict1:
                    dict1_current_value = dict1[key]
                output_diffs[key] = dict2[key] - dict1_current_value
        return output_diffs
    except Exception:
        return output_diffs


if __name__ == '__main__':
    totals = {}

    cti_report_path = './output/cti_reports/'
    totals['cti_reports'] = generate_totals_for_path(cti_report_path)

    threat_encyclopedia_report_symantec_path = './output/threat_encyclopedia_reports/symantec/'
    totals['threat_encyclopedia_reports'] = generate_totals_for_path(threat_encyclopedia_report_symantec_path,
                                                                     'symantec_')

    threat_encyclopedia_report_trendmicro_path = './output/threat_encyclopedia_reports/trendmicro/'
    totals['threat_encyclopedia_reports'].update(
        generate_totals_for_path(threat_encyclopedia_report_trendmicro_path, 'trendmicro_'))

    with open(os.path.dirname(__file__) + "/../{}".format(DAILY_DIFFS_PATH), "r") as read_file:
        all_diffs = json.load(read_file)

    all_diffs_keys = list(all_diffs)
    most_recent_date = all_diffs_keys[len(all_diffs_keys) - 1]
    most_recent_date_totals = all_diffs[most_recent_date]['totals']
    today_diffs = compute_diff(most_recent_date_totals, totals)

    today = datetime.today().strftime('%Y-%m-%d')

    all_diffs[today] = {}
    all_diffs[today]['totals'] = totals
    all_diffs[today]["diff_from_{}".format(most_recent_date)] = today_diffs

    with open(os.path.dirname(__file__) + "/../{}".format(DAILY_DIFFS_PATH), "w+") as write_file:
        json.dump(all_diffs, write_file)
