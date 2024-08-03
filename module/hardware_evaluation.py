import psutil
import subprocess
import time
import ast
import numpy as np

def monitor_usage(proc):
    cpu_usage_lst = []
    memory_usage_lst = []
    try:
        ps_process = psutil.Process(proc.pid)
        cpu_usage_lst.append(ps_process.cpu_percent(interval=None))
        while proc.poll() is None:
            cpu_usage = ps_process.cpu_percent(interval=None)
            memory_usage = ps_process.memory_percent()
            cpu_usage_lst.append(cpu_usage)
            memory_usage_lst.append(memory_usage)
            time.sleep(1)
        cpu_usage_lst = list(np.array(cpu_usage_lst) - cpu_usage_lst[0])
        cpu_usage = np.mean(cpu_usage_lst[1:])
        memory_usage = np.mean(memory_usage_lst[:-1])
        return cpu_usage, memory_usage
    except psutil.NoSuchProcess:
        print("Process terminated")

def code_evaluation(func, run, test_data):
    tree = ast.parse(func)
    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    if len(function_names) != 1:
        raise ValueError(f"Expected exactly one function in the file, but found {len(function_names)}: {function_names}")

    function_name = function_names[0]
    if test_data:
        file = open('file.py','w')
        file.write(func)
        file.write('\n\nif __name__ == "__main__":\n')
        file.write(f'    for _ in range({run}):\n')
        file.write(f'        {function_name}({test_data})\n')
        file.close()
        
    process = subprocess.Popen(['python', 'file.py'])
    start_time = time.perf_counter()
    cpu_usage, memory_usage = monitor_usage(process)
    process.wait()  # Wait for the worker process to complete
    end_time = time.perf_counter()
    duration = end_time-start_time
    return [cpu_usage, memory_usage, duration]

if __name__ == "__main__":
    with open('/dbfs/FileStore/tables/test.py', 'r') as file:
        content = file.read()
    hardware_info = code_evaluation(content, 1000000, 5)
    print(f'CPU Usage: {hardware_info[0]}%')
    print(f'Memory Usage: {hardware_info[1]}%')
    print(f'Runtime: {hardware_info[2]}%')
