import pyperclip

def generate_prompt():
    try:
        # Read simulation code
        with open('simulation.py', 'r', encoding='utf-8') as file:
            code = file.read()
        
        # Read simulation logs
        with open('simulation_log.txt', 'r', encoding='utf-8') as file:
            logs = file.read()
        
        
        # Construct the prompt
        prompt = f"""You are a professional software developer. Below is the code for a middle-aged village simulation. 
        Please analyze the code and logs to see if you find anything that don't make sense( like some number seems too large or too many people die) . 
        Carefully validate each identified issue, and if it is valid, modify the code accordingly while ensuring that the improvements remain practical and do not introduce unnecessary complexity.

Code:
{code}

logs:
{logs}

"""
        
        # Copy to clipboard
        pyperclip.copy(prompt)
        print("Prompt copied to clipboard successfully!")
        
    except FileNotFoundError as e:
        print(f"Error: {e.filename} not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")



def generate_prompt_2():
    try:
        # Read simulation code
        with open('simulation.py', 'r', encoding='utf-8') as file:
            code = file.read()
                
        # Read simulation logs
        with open('comments.txt', 'r', encoding='utf-8') as file:
            comments = file.read()
        
        
       
        # Construct the prompt
        prompt = f"""
You are a professional software developer. Below is the code for a middle-aged village simulation and some comments on the code. 
Please analyze the code and comments. 
Then carefully validate each identified issue, and if it is valid, modify the code accordingly while ensuring that the improvements remain practical and do not introduce unnecessary complexity. 
write the full modified code in the end. 
Code: 
{code} 

Comment on the code: 
{comments} 

revised code:
"""
        
        # Copy to clipboard
        pyperclip.copy(prompt)
        print("Prompt copied to clipboard successfully!")
        
    except FileNotFoundError as e:
        print(f"Error: {e.filename} not found")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    generate_prompt()