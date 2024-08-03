import psutil
import pandas as pd
import os
import time
from datetime import datetime

def SCI_calculation(hardware_info: list):
    p_mem = 0.4 * hardware_info[1]
    # cpu_type = cpuinfo.get_cpu_info()['brand_raw']: Intel(R) Xeon(R) Platinum 8259CL CPU @ 2.50GHz
    num_cpu = 4   # vm type is Standard_DS3_v2

    # 3rd Generation Intel® Xeon® Platinum 8370C: 270
    # Intel® Xeon® Platinum 8272CL: 195
    # Intel® Xeon® 8171M 2.1GHz: 165
    # Intel® Xeon® E5-2673 v4 2.3 GHz: 135
    # Intel® Xeon® E5-2673 v3 2.4 GHz: 105
    p_cpu = 174*num_cpu 
    E = (hardware_info[0] * p_cpu + p_mem) / 1000
    I = 0.207074
    M = 0
    R = 1
    SCI = (E * I + M) / R
    code_info = hardware_info + [SCI]
    return code_info

def report_generate(init_code_info,opt_code_info,username,user_id):
    df = pd.DataFrame([init_code_info + opt_code_info],
                      columns = ['init_CPU_Usage', 'init_Memory_Usage', 'init_Runtime', 'init_SCI', 'opt_CPU_Usage', 'opt_Memory_Usage', 'opt_Runtime', 'opt_SCI'])
    df['id'] = user_id
    df['username'] = username
    df['timestamp'] = datetime.now()
    df['init_filename'], df['opt_filename'] = generate_filename(user_id)
    
    if os.path.exists('database.csv'):
        existing_df = pd.read_csv('database.csv')
        updated_df = pd.concat([existing_df, df], ignore_index=True)
    else:
        updated_df = df[['id','username','timestamp','init_filename', 'opt_filename','init_CPU_Usage', 'init_Memory_Usage', 'init_Runtime', 'init_SCI', 'opt_CPU_Usage', 'opt_Memory_Usage', 'opt_Runtime', 'opt_SCI']]
    
    updated_df.to_csv('database.csv', index=False)
    return pd.DataFrame(data = [init_code_info, opt_code_info],
                      columns = ['CPU_Usage', 'Memory_Usage', 'Runtime', 'SCI'],index = ['init_code','opt_code'])

def generate_filename(user_id):
    init_filename = f'init_code_{user_id}.py'
    opt_filename = f'opt_code_{user_id}.py'
    return init_filename, opt_filename
