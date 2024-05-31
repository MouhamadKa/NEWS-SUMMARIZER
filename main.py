import json
import os
import openai
from dotenv import load_dotenv
import logging
import time
from datetime import datetime
import streamlit as st
from get_news_api import get_news


load_dotenv()
client = openai.OpenAI()
model = "gpt-4o"
        
        
class AssistantManager:
    assistant_id = os.getenv("ASSISTANT_ID")
    thread_id = os.getenv("THREAD_ID")
    
    def __init__(self, model : str = model):
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None
        
        
        # Retrieve existing assistant and thread if IDs are already exists
        if self.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                assistant_id = self.assistant_id
            )
        if self.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                thread_id = self.thread_id
            )
            
            
    def create_assistant(self, name, instructions, tools):
        if not self.assistant:
            self.assistant = self.client.beta.assistants.create(
                name = name,
                model = self.model,
                instructions= instructions,
                tools = tools
            )
            self.assistant_id = self.assistant.id
            # print(f"Assistant ID: {self.assistant_id}")

    def create_thread(self):
        if not self.thread:
            self.thread = self.client.beta.threads.create()
            self.thread_id = self.thread.id 
            # print(f"Thread ID: {self.thread_id}")   
            
    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id = self.thread_id,
                role = role,
                content = content
            )
            
    def run_assistant(self, instructions):
        if self.assistant and self.thread:
            self.run = self.client.beta.threads.runs.create(
                assistant_id = self.assistant_id,
                thread_id = self.thread_id,
                instructions = instructions
            )
            
    def process_messages(self):
        if self.thread:
            messages = self.client.beta.threads.messages.list(thread_id= self.thread_id)
            summary = []
            
            last_message = messages.data[0]
            role = last_message.role
            response = last_message.content[0].text.value
            summary.append(response)
            
            self.summary = "\n".join(summary)
            print(f"SUMMARY ------> {role.capitalize()}: ====> {response}")
            # I don't know if I have to return the summary here or not 1:42:45

            # We could have did this instead
            # for msg in messages:
            #     role = msg.role
            #     content = msg.content[0].text.value
            #     print(f"SUMMARY ------> {role.capitalize()}: ====> {content}")
                
    def call_required_functions(self, required_actions):
        if not self.run:
            return 
        
        tool_outputs = []
        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])
            
            if func_name == "get_news":
                output = get_news(topic=arguments["topic"])
                # print(f"FUNCTION CALLING OUTPUT =====> {output}")
                
                finall_str = ''
                for item in output:
                    finall_str += "\n".join(item)

                tool_outputs.append({
                    "tool_call_id" : action["id"],
                    "output" : finall_str
                })
                
            else:
                raise ValueError(f"Unknown Function: {func_name}")
        
        print("Submitting outputs back to the Assistant...")
        self.client.beta.threads.runs.submit_tool_outputs(
            thread_id= self.thread_id,
            run_id= self.run.id,
            tool_outputs= tool_outputs
        )
                
    # for streamlit
    def get_summary(self):
        return self.summary
                
    def wait_for_completion(self):
        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status = self.client.beta.threads.runs.retrieve(
                    thread_id = self.thread_id,
                    run_id = self.run.id
                )                
                print(f"RUN STATUS:: {run_status.model_dump_json(indent=4)}")

                if run_status.status == "completed":
                    self.process_messages()
                    break
                
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW...")
                    self.call_required_functions(
                        required_actions=run_status.required_action.submit_tool_outputs.model_dump()
                    )

    # Run the steps
    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id= self.thread_id,
            run_id= self.run.id
        )
        # print(f"Run Steps ===> {run_steps}")
        return run_steps


def main():
    # news = get_news("bitcoin")
    # print(news[0])
    
    manager  = AssistantManager()
    
    # Streamlit interface
    st.title("News Summarizer")
    with st.form(key="user_input_form"):
        instructions = st.text_input("Enter a Topic")
        submit_button = st.form_submit_button(label="Run Assistant")
        
        if submit_button:
            manager.create_assistant(
                name = "News Summarizer",
                instructions = """Yow are a personal article summarizer Assistant who knows how to take a list of articles, titles, and descriptions and then write a short summary of all the news articles.
                    Please write the result articles in a nice readable form like this:
                    Title: Champions League Final: Real Madrid Beats Liverpool for 14th Title.
                    Source: The New York times.
                    Author: Rory Smith, Tariq Panja and Andrew Das.
                    Description: "A small, beautiful summary of two to three lines"
                    Read more link
                    Also but two empty lines between each two articels""",
                tools = [
                    {
                    "type" : "function",
                    "function" : {
                        "name" : "get_news",
                        "description" : "Get list of articles/news for the given topic",
                        "parameters" : {
                            "type" : "object",
                            "properties" : {
                                "topic" : {
                                    "type" : "string",
                                    "description" : "The topic for the news, e.g. bitcoin",
                                }
                            },
                            "required" : ["topic"],
                        },
                    },
                }
                ]
            )
            
            manager.create_thread()
            
            # Add the message and run the assistant
            manager.add_message_to_thread(
                role = "user",
                content = f"Summarize the news on this topic {instructions}"
            )
            manager.run_assistant(instructions="Summarizr the news and make sure to mention the link to it at the end of each article.")
            
            
            # Wait for completion and process messages
            manager.wait_for_completion()
            summary = manager.get_summary()
            
            
            st.write(summary)
            st.text("Run Steps")
            st.code(manager.run_steps(), line_numbers=True)
            
        

if __name__ == "__main__":
    main()