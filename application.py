import streamlit as st
import os
import requests
import json
import time
import module.azure_optimise_code
import pandas as pd
import numpy as np
from datetime import datetime
import ast
import base64
import os
from dotenv import load_dotenvload_dotenv()

load_dotenv()

# Databricks URL and Token
DATABRICKS_URL = os.getenv('DATABRICKS_URL')
TOKEN = os.getenv('TOKEN')

# Headers for authentication
headers = {
    'Authorization': f'Bearer {TOKEN}',
    'Content-Type': 'application/json'
}

@st.cache_resource
def display_file(file):
    file_extension = os.path.splitext(file.name)[1]  # Get the file extension
    if file_extension == '.py':
        code = file.read().decode('utf-8')
        initial_code = code
        optimise_code,test_data = module.azure_optimise_code.ai_optimise(initial_code)
        return initial_code, optimise_code,test_data
    else:
        st.write("Unsupported file type.")

def generate_id(username):
    times = str(int(time.time()))
    chars = ''.join([username[0],username[-1]])
    return f"{chars}{times}"

def file_content(func, test_data,run):
    tree = ast.parse(func)
    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    if len(function_names) != 1:
        st.write(ValueError(f"Expected exactly one function in the file, but found {len(function_names)}: {function_names}"))
    function_name = function_names[0]
    content = f"{func}\n\nif __name__ == '__main__':\n"
    content += f'    for _ in range({run}):\n'
    if isinstance(test_data,dict):
        content += f'        {function_name}(**{test_data})\n'
    elif isinstance(test_data,(tuple,set)):
        content += f'        {function_name}(*{test_data})\n'
    else:    
        content += f'        {function_name}({test_data})\n'
    return content, function_name

def run_notebook_with_file(init_content, opt_content, user_id,username,init_func, opt_func, test_data, run):
    # Job payload
    job_payload = {
        "run_name": "Run Python file",
        "existing_cluster_id": os.getenv('CLUSTER_ID'),
        "notebook_task": {
            "notebook_path": os.getenv('NOTEBOOK_PATH'),
            "base_parameters": {
                "init_code": init_content,
                "opt_code": opt_content,
                "user_id": user_id,
                "username": username,
                "init_func":init_func,
                "opt_func":opt_func,
                "test_data": str(test_data),
                "run": run
            }
        }
    }
    
    # Send POST request to run the notebook
    response = requests.post(
        f'{DATABRICKS_URL}/api/2.0/jobs/runs/submit',
        headers=headers,
        data=json.dumps(job_payload)
    )
    
    if response.status_code == 200:
        run_id = response.json().get('run_id')
        return run_id
    else:
        st.error("Error running the notebook.")
        st.error(response.text)
        return None

def get_run_result(run_id):
    loop=0
    while True:
        response = requests.get(
            f'{DATABRICKS_URL}/api/2.0/jobs/runs/get-output?run_id={run_id}',
            headers=headers
        )
        
        if response.status_code == 200:
            output = response.json().get('notebook_output', {}).get('result')
            if output:
                return output
            else:
                time.sleep(5)  # Wait for 5 seconds before checking again
                loop +=1
            if loop == 25:
                error = response.json().get('error')
                if error:
                    st.error(error)
                    return None
        else:
            st.error("Error fetching run results.")
            st.error(response.text)
            return None
def reset_session_state():
    for key in st.session_state.keys():
        del st.session_state[key]
def main():
    st.set_page_config(layout="wide")
    st.title("Green Code Optimiser")
    
    left_col, right_col = st.columns(2)
    with left_col:
        username = st.text_input("## Username", placeholder = 'Please type your username, ex: johndoe')
        uploaded_file = st.file_uploader("", type=['py'],label_visibility="collapsed")
    with right_col:
        st.write("## Report")
        placeholder = st.empty()
        # with placeholder.container():
        #     col_1, col_2, col_3, col_4 = st.columns(2)
            
        #     col_1.metric(label='**CPU Usage:**', value="")
        #     col_2.metric(label='**Memory Usage:**', value="")
        #     col_3.metric(label='**Runtime:**', value="")
        #     col_4.metric(label='**SCI:**', value="")
    if 'uploaded_file_info' not in st.session_state:
        st.session_state.uploaded_file_info = None    
    if uploaded_file is not None and username is not None:
        file_info = (uploaded_file.name, uploaded_file.size, uploaded_file.type)
        if st.session_state.uploaded_file_info != file_info:
            reset_session_state()
            st.session_state.uploaded_file_info = file_info
        with left_col:
            initial_code, optimise_code,test_data = display_file(uploaded_file)
            col1, col2 = st.columns(2)
            with col1:
                st.write('**Initial Code:**')
                st.code(initial_code,language='python')
            with col2:
                st.write('**Optimised Code:**')
                st.code(optimise_code,language='python')
                st.download_button(label="Download Optimised File", data=optimise_code, file_name="optimise_code.py")

            if 'df' not in st.session_state:
                st.session_state.df = None
            if test_data == None:
                st.write("Please clear the cache, and reupload the file. Thank you.")
            else:
                help = "Test data is the input parameter to put in the function, and Run time is the number of running the function."    
                col_r, col_h = st.columns([3,7])
                col_h.button(":information_source:",help = help)
                radio = col_r.radio("Which one you want to modify",('Test data', 'Run time'), index = 1, horizontal=True)
                confirm = False
                if 'testdata' not in st.session_state:
                    st.session_state.testdata = test_data
                if 'run' not in st.session_state:
                    st.session_state.run = 1
                if radio == 'Test data':
                    if isinstance(test_data,(float, int)):
                        test_data_1 = st.select_slider("",options = [test_data, test_data*50, test_data*100, test_data*500, test_data*1000, test_data*5000 ,
                                                                   test_data*10000,test_data*50000, test_data*100000,test_data*500000, test_data*1000000],
                                                     value = st.session_state.testdata, key = 'data', label_visibility="collapsed")
                        st.session_state.testdata = test_data_1
                    elif isinstance(test_data,(list,str)):
                        cola,colb = st.columns([8.5,1.5])
                        if colb.button('3 times longer',key = 'multiply'):
                            st.session_state.testdata *= 3
                        cola.code(f'Test data Length is {len(st.session_state.testdata)}')
                        if len(st.session_state.testdata) < 1000:
                            cola.code(st.session_state.testdata)
                    else:
                        st.code(test_data)
                if radio == 'Run time':
                    run = st.slider(" ", min_value = 1, max_value = 100, step = 10, value = st.session_state.run, label_visibility="collapsed")
                    st.session_state.run = run
                with st.expander('Modify by yourself'):
                    a = st.text_input(" ",label_visibility = "collapsed")
                    colaa,colbb,colcc = st.columns(3)
                    colaa.code(a)
                    try:
                        a_c = ast.literal_eval(a)
                    except:
                        a_c = a
                    colbb.code(type(a_c))
                    if colcc.button('Modify by myself'):
                        st.session_state.testdata = ast.literal_eval(a)
                # if isinstance(st.session_state.testdata,list):
                #     st.write(f'Test data length is {len(st.session_state.testdata)}, and the number of execusion is {st.session_state.run}')
                # else:
                #     st.write(f'Test data is {st.session_state.testdata}, and the number of execusion is {st.session_state.run}')
                confirm = st.button('Confirm') 
                if 'confirm' not in st.session_state:
                    st.session_state.confirm = False
                if confirm:
                    st.session_state.confirm = True
                    test_data = st.session_state.testdata
                    init_content, init_func = file_content(initial_code, test_data,run)
                    opt_content, opt_func= file_content(optimise_code, test_data,run)
                    user_id = generate_id(username)
                    run_id = run_notebook_with_file(init_content, opt_content, user_id, username, init_func, opt_func,test_data, run)
                    if run_id :
                        result = get_run_result(run_id)
                        st.session_state.df = pd.read_json(result)
        if st.session_state.df is not None:
            df = st.session_state.df
            with placeholder.container():
                col1,col2, col3,col4 = st.columns(4)
                with col1:
                    delta = (df.loc['opt_code','CPU_Usage'] - df.loc['init_code','CPU_Usage'])*100 /  df.loc['init_code','CPU_Usage']
                    delta_display = "" if np.isnan(delta) else f"{delta:.2f}%"
                    st.metric(label='**CPU Usage:**', value=f"{df.loc['opt_code','CPU_Usage']:.2f}%", delta=delta_display,delta_color="inverse")
                    st.bar_chart(df['CPU_Usage']) 
                with col2:
                    delta = (df.loc['opt_code','Memory_Usage'] - df.loc['init_code','Memory_Usage'])*100 /  df.loc['init_code','Memory_Usage']
                    delta_display = "" if np.isnan(delta) else f"{delta:.2f}%"
                    st.metric(label='**Memory Usage:**', value=f"{df.loc['opt_code','Memory_Usage']:.2f}%", delta=delta_display,delta_color="inverse")
                    st.bar_chart(df['Memory_Usage'])
                with col3:
                    delta = (df.loc['opt_code','Runtime'] - df.loc['init_code','Runtime'])*100 /  df.loc['init_code','Runtime']   
                    st.metric(label = '**Runtime:**', value=f"{df.loc['opt_code','Runtime']:.2f} sec", delta = f"{delta:.2f}%", delta_color="inverse")
                    st.line_chart(df['Runtime'])
                with col4:
                    delta = (df.loc['opt_code','SCI'] - df.loc['init_code','SCI'])*100 /  df.loc['init_code','SCI']
                    delta_display = "" if np.isnan(delta) else f"{delta:.2f}%"
                    st.metric(label='**SCI:**', value=f"{df.loc['opt_code','SCI']:.2f} kg CO₂", delta=delta_display,delta_color="inverse")
                    st.line_chart(df['SCI']) 



if __name__ == "__main__":
    main()
