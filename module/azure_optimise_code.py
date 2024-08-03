from openai import AzureOpenAI
import time
import ast
import os
from dotenv import load_dotenvload_dotenv() 

load_dotenv()

client = AzureOpenAI(
        api_key = os.getenv('API_KEY'),  
        api_version = "2024-05-01-preview",
        azure_endpoint = os.getenv('ENDPOINT')
    )

def ai_optimise(prompt,create=False):
    a=0
    assistant_id = get_assistant_id(create)
    while True:
        optimise_code,test_data = optimised_code(prompt,assistant_id)
        # show_optimised_code(optimise_code)
        if optimise_code != 'failed':
            return optimise_code, test_data
        a+=1    
        time.sleep(20)
        if a==6:
            return 'Error', None
        
def get_assistant_id(create=False):
    if create:
        instructions = "You are a code expert who can optimise the code into green code to save not only the runtime but also energy usage.\
            When you received the code you should follow these steps:\
            1. Optimise the code. \
            2. Create and run a unit test for the code to confirm that it runs.\
            3. If the code is successful, return the optimised code.\
            4. If the code is unsuccessful, try to revise the code and rerun going through the steps from above again.\
            The response should be format as this:\
            {\"optimise_code\",\"test_data\":{\"value\",\"data_type\"}} \
            and test data should only has one test data value and the data type of the test data"
        
        assistant = client.beta.assistants.create(
            name="Green code optimiser",
            instructions=instructions,
            tools=[{"type": "code_interpreter"}],
            model="DemoModel4o",
        )
        print(assistant.id)
        return assistant.id
        
    return os.getenv('ASSISTANT_ID')
    
def optimised_code(prompt,assistant_id):
    thread = client.beta.threads.create(
    messages=[{"role": "user","content": prompt}])
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id)
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id,
        run_id=run.id)
        if run_status.status == 'completed':
            response = client.beta.threads.messages.list(thread_id=thread.id).data[0].content[0].text.value
            # print(response)
            if response.startswith('{') and response.endswith('}'):
                response = ast.literal_eval(response)
            else:
                response = response[response.find('{'):response.rfind('}')+1]
                response = ast.literal_eval(response)
            test_data = response['test_data']
            optimised_code = response['optimise_code']
            return optimised_code, test_data
        
        elif run_status.status =='failed':    
                return 'failed', None
        else:
            print(f"Run status: {run_status.status}")
        time.sleep(5)

def show_optimised_code(response):
    if response == 'failed':
        print('The response is not generated. Please wait 20 seconds for regeneration.')
    else:
        print(response)

 
if __name__ == "__main__":
    with open('/dbfs/FileStore/tables/test.py', 'r') as file:
        content = file.read()
    ai_optimise(content)
