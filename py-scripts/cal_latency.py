import pandas as pd
import numpy as np
import os
import pickle

def count_reads_between_writes(trace_file, write_threshold=24):
    read_count = 0
    write_count = 0
    results = []

    with open(trace_file, "r") as infile:
        for line in infile:
            parts = line.split()
            if len(parts) < 2:
                continue

            operation = parts[1]
            if operation == "R":
                read_count += 1
            elif operation == "W":
                write_count += 1

            if write_count == write_threshold:
                results.append(read_count)
                read_count = 0
                write_count = 0

    return results

def calculate_cost(data, trace_name, timing, request_type):
    column_requests = f"total_num_read_requests"
    filtered_data = data[(data['timing'] == timing) & (data['trace'] == trace_name)]

    if not filtered_data.empty:
        average_cost = (filtered_data["memory_system_cycles"] / filtered_data[column_requests]).sum()
        return average_cost
    return None

def get_total_system_cycles(data, trace_name, timing):
    filtered_data = data[(data['timing'] == timing) & (data['trace'] == trace_name)]
    if not filtered_data.empty:
        return filtered_data["memory_system_cycles"].sum()
    return None

def calculate_write_proportion(trace_file):
    total_operations = 0
    write_operations = 0

    with open(trace_file, "r") as infile:
        for line in infile:
            parts = line.split()
            if len(parts) < 2:
                continue

            total_operations += 1
            if parts[1] == "W":
                write_operations += 1

    if total_operations > 0:
        return write_operations / total_operations
    return 0.0

# Initialize results storage for different write thresholds
all_results = []
r_count_pickle_data = {}

# Configuration
write_thresholds = [6, 12, 24]
trace_folder = "offest_base_traces"
read_speed_data = pd.read_csv('R_perf.csv')
write_speed_data = pd.read_csv('W_perf.csv')
slow_chips = ["DDR5_1600AN", "DDR5_2400AN", "DDR5_2800AN", "DDR5_3200AN", "DDR5_6400AN"]

# Add a calculated "DDR5_2400AN" based on linear interpolation between DDR5_1600AN and DDR5_3200AN
def calculate_interpolated_speed(data, timing1, timing2, new_timing, ratio):
    numeric_cols = data.select_dtypes(include=[np.number]).columns
    data_1 = data[data['timing'] == timing1].set_index('trace')
    data_2 = data[data['timing'] == timing2].set_index('trace')
    interpolated_data = (1 - ratio) * data_1[numeric_cols] + ratio * data_2[numeric_cols]
    interpolated_data = interpolated_data.reset_index()
    interpolated_data['timing'] = new_timing
    return interpolated_data

interpolated_write_speed_data_2400 = calculate_interpolated_speed(write_speed_data, "DDR5_1600AN", "DDR5_3200AN", "DDR5_2400AN", 0.33)
interpolated_write_speed_data_2800 = calculate_interpolated_speed(write_speed_data, "DDR5_1600AN", "DDR5_3200AN", "DDR5_2800AN", 0.5)
write_speed_data = pd.concat([write_speed_data, interpolated_write_speed_data_2400, interpolated_write_speed_data_2800], ignore_index=True)

interpolated_read_speed_data_2400 = calculate_interpolated_speed(read_speed_data, "DDR5_1600AN", "DDR5_3200AN", "DDR5_2400AN", 0.33)
interpolated_read_speed_data_2800 = calculate_interpolated_speed(read_speed_data, "DDR5_1600AN", "DDR5_3200AN", "DDR5_2800AN", 0.5)
read_speed_data = pd.concat([read_speed_data, interpolated_read_speed_data_2400, interpolated_read_speed_data_2800], ignore_index=True)

# Process traces for each threshold
for write_threshold in write_thresholds:
    for slow_chip in slow_chips:
        for trace_file in os.listdir(trace_folder):
            if not trace_file.endswith(".trace"):
                continue

            trace_path = os.path.join(trace_folder, trace_file)
            trace_name = trace_file.split('.')[0]

            # Calculate costs
            fast_read_cost = calculate_cost(read_speed_data, trace_name, "DDR5_6400AN", "read")
            fast_write_cost = calculate_cost(write_speed_data, trace_name, "DDR5_6400AN", "read")
            slow_write_cost = calculate_cost(write_speed_data, trace_name, slow_chip, "read")
            total_system_cycles_6400 = get_total_system_cycles(write_speed_data, trace_name, "DDR5_6400AN")
            write_proportion = calculate_write_proportion(trace_path)

            # Analyze costs
            if fast_read_cost is not None and fast_write_cost is not None and slow_write_cost is not None:
                r_count = count_reads_between_writes(trace_path, write_threshold)
                r_count_pickle_data[f"{trace_name}_th{write_threshold}"] = r_count  # Store r_count in pickle data
                cost_sum = np.sum([
                    max(write_threshold * (slow_write_cost - fast_write_cost) - i * fast_read_cost, 0) for i in r_count
                ])
                normalized_cost = cost_sum / total_system_cycles_6400 if total_system_cycles_6400 else None

                # Calculate additional statistics
                r_count_mean = np.mean(r_count) if len(r_count) != 0 else 0
                r_count_variance = np.var(r_count) if len(r_count) != 0 else 0
                r_count_std_dev = np.std(r_count) if len(r_count) != 0 else 0
                r_count_max = np.max(r_count) if len(r_count) != 0 else 0
                r_count_min = np.min(r_count) if len(r_count) != 0 else 0

                threshold_value = write_threshold * (slow_write_cost - fast_write_cost) / fast_read_cost
                below_threshold_count = sum(i < threshold_value for i in r_count)
                below_threshold_values = [i for i in r_count if i < threshold_value]
                below_threshold_mean = np.mean(below_threshold_values) if len(below_threshold_values) != 0 else 0
                below_threshold_variance = np.var(below_threshold_values) if len(below_threshold_values) != 0 else 0
                below_threshold_std_dev = np.std(below_threshold_values) if len(below_threshold_values) != 0 else 0
                below_threshold_max = np.max(below_threshold_values) if len(below_threshold_values) != 0 else 0
                below_threshold_min = np.min(below_threshold_values) if len(below_threshold_values) != 0 else 0
            else:
                normalized_cost = None
                r_count_mean = r_count_variance = r_count_std_dev = r_count_max = r_count_min = 0
                below_threshold_count = below_threshold_mean = below_threshold_variance = below_threshold_std_dev = below_threshold_max = below_threshold_min = 0

            # Collect results
            all_results.append({
                "Write Threshold": write_threshold,
                "Trace Name": trace_name,
                "Slow Chip": slow_chip,
                "Fast Read Cost": fast_read_cost,
                "Fast Write Cost": fast_write_cost,
                "Slow Write Cost": slow_write_cost,
                "Write Proportion": write_proportion,
                "Average Read Block Size": r_count_mean,
                "Read Block Size Variance": r_count_variance,
                "Read Block Size Std Dev": r_count_std_dev,
                "Read Block Size Max": r_count_max,
                "Read Block Size Min": r_count_min,
                "Damage Threshold": write_threshold * (slow_write_cost - fast_write_cost) / fast_read_cost,
                "Normalized Cost (%)": 100 * normalized_cost if normalized_cost is not None else None
            })

# Save results to CSV
all_results_df = pd.DataFrame(all_results)
output_file = "avg_latency_results.csv"
all_results_df.to_csv(output_file, index=False)

# Save r_count data to pickle
r_count_pickle_path = "r_count_data.pkl"
with open(r_count_pickle_path, "wb") as pickle_file:
    pickle.dump(r_count_pickle_data, pickle_file)
