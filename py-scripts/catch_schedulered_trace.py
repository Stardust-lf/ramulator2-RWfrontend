import os
import yaml
import subprocess
import re

config_path = "exp_configs/tpch_test_config.yaml"
trace_dir = "TPCH_traces"


def extract_info(output):
    info_dict = {}
    key_counter = {}

    for line in output.splitlines():
        kv_match = re.match(r"^\s*(\w+):\s*([\d.]+|nan)", line)
        if kv_match:
            key, value = kv_match.groups()
            try:
                value = float(value) if value != "nan" else float("nan")
            except ValueError:
                pass

            if key in info_dict or key in key_counter:
                key_counter[key] = key_counter.get(key, 0) + 1
                key = f"{key}_{key_counter[key]}"
            else:
                key_counter[key] = 0

            info_dict[key] = value

    return info_dict


# Initialize list to store results
results = []

# Load the initial configuration file
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)
print(config)
# Get a list of all trace files in the directory
# trace_files = [f for f in os.listdir(trace_dir) if f.endswith('.trace')]
# trace_files = ["bc_twi.trace","bc_web.trace",
#                "cc_twi.trace","cc_web.trace",
#                "pr_twi.trace","pr_web.trace"]
# trace_files = ["bfs_twi.trace","bfs_web.trace","bfs_road.trace"
#                "bc_road.trace","cc_road.trace","pr_road.trace"]
trace_files = [filename for filename in os.listdir(trace_dir)]
print(trace_files)
# Iterate over each trace file and each slow_chip_perf value
for i in range(1, 23):
    for trace_name in [filename for filename in os.listdir("TPCH_traces/Q{}".format(i))]:
        trace_path = os.path.join(
            "TPCH_traces", "Q{}".format(i), trace_name)
        print(trace_path)
        config['Frontend']['path'] = trace_path

        print(f"Running simulation with trace {trace_path}")

        # Update slow_chip_perf for this iteration
        config['MemorySystem']['Controller']['exe_trace_path'] = os.path.join(
            "scheduled_traces", "TPCH", "Q{}".format(i), trace_name)
        print(config)
        # Save the updated configuration to a temporary file
        temp_config_path = "temp_config.yaml"
        with open(temp_config_path, 'w') as temp_config:
            yaml.dump(config, temp_config)

        # Run the simulation and capture the output with a timeout
        result = subprocess.run(
            ['./ramulator2', '-f', temp_config_path], capture_output=True, text=True)
