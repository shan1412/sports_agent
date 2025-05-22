import os
import asyncio
import logging
from typing import Dict, Optional, Union
from dotenv import load_dotenv
import gradio as gr
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from agents import Agent, Runner, trace, function_tool
import pprint

# Logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('chatbot')

load_dotenv()

# --- Pydantic Models ---

class schedule_details(BaseModel):
    contact: str = Field(..., description="Contact Number of the User")
    schedule_date_from: str = Field(..., description="Schedule date from in format 'YYYY-MM-DD'")
    schedule_date_to: str = Field(..., description="Schedule date to in format 'YYYY-MM-DD'")

class NLP2SQLOutput(BaseModel):
    sql_query: str
    "Generated SQL Query based on user's natural language request."

    def __iter__(self):
        # Allow unpacking or list conversion, e.g., list(obj) or obj1, obj2 = obj
        yield self.sql_query

class IntentChecker(BaseModel):
    """
    Model to determine which agent should handle a given request.
    """
    SQL_agent: bool = Field(
        ...,
        description="Set to True if SQL Agent is required for querying schedules or existing information of athletes or coaches."
    )
    knowledge_agent: bool = Field(
        ...,
        description="Set to True if the Knowledge Agent is required to handle general information queries."
    )

class KnowledgeAgentOutput(BaseModel):
    response_to_frontdesk_agent: str = Field(..., description="Knowledge Agent's response in a way that the Front Desk Agent can understand.")

class FrontDeskOutput(BaseModel):
    respond_to_user: Union[str, bool] = Field(..., description="A response the End user will have from the Call center Agent")
    ask_the_agent: Union[str, bool] = Field(..., description="This is the prompt with details emphasized to the intent detection Agent")

# --- Agent Declarations ---

intent_agent = Agent(
    name="Intent Judge",
    instructions=(
        "You are an intent classifier. Based on the user's message, decide which functional agent should handle it.\n"
        "- Set `SQL_agent` to True **if the message includes queries about schedules, training sessions, matches, or anything involving database lookups** for athletes or coaches.\n"
        "- Set `knowledge_agent` to True **if the message includes informational, instructional, or explanatory questions**, such as rules, guidelines, or general knowledge.\n"
        "Return a JSON with True or False for both `SQL_agent` and `knowledge_agent`. If the message includes both types of intent, set both to True."
    ),
    model="gpt-4o-mini",
    output_type=IntentChecker
)

sql_agent = Agent(
    name="SQL Agent",
    instructions=(
        "Convert the user's natural language query into a valid SQL query "
        "to retrieve or update athlete/coach schedule information. "
        """Respond only with a valid SQL query string in the 'sql_query' field.
        You are an SQL Architect and you are tasked to generate Postgress SQL based on natural langauge question and schema below: 
        ### Schema: 
            CREATE TABLE public.athlete_batches (
                id serial4 NOT NULL,
                contact_no varchar(15) NOT NULL,
                athlete_name text NOT NULL,
                batch_name text NOT NULL,
                "date" date NOT NULL,
                start_time time NOT NULL,
                end_time time NOT NULL,
                status varchar(10) NOT NULL,
                CONSTRAINT athlete_batches_pkey PRIMARY KEY (id),
                CONSTRAINT athlete_batches_status_check CHECK (((status)::text = ANY ((ARRAY['Open'::character varying, 'Cancelled'::character varying])::text[])))""" 
    ),
    model="gpt-4o-mini",
    output_type=NLP2SQLOutput
)

knowledge_agent = Agent(
    name="Knowledge Agent",
    instructions=(
        "You are an expert on sports rules, strategies, and official sports news only. "
        "Answer **only** questions related to sports rules, game strategies, "
        "or recent verified sports news. "
        "Do not answer questions about controversies, politics, personal opinions, or any unrelated topics. "
        "If asked about topics outside this scope, respond politely stating you can only provide information about sports rules, strategies, or official sports news."
    ),
    model="gpt-4o-mini",
    output_type=KnowledgeAgentOutput
)

frontdesk_agent = Agent(
    name="Front Desk Agent",
    instructions=(
        """
You are a friendly and professional Relationship Manager assisting athletes, coaches, and customers. Your role is to understand their needs clearly, provide accurate information, guide them politely, and route their requests to the right specialist agent when needed.

- When you receive a message, first determine if it is from a user or from another agent.
- If the message is from a user:
    - Greet warmly and confirm understanding.
    - Listen carefully to the user's queries about schedules, training, game rules, or general information.
    - If the request is unclear or off-topic, politely ask for clarification or offer help on common topics.
    - Maintain a helpful and respectful tone throughout the conversation.
    - If the user's request requires a specialist, route it to the appropriate agent and inform the user.
- If the message is from another agent:
    - Respond professionally and concisely, providing the requested information or assistance.
    - If you cannot help, politely indicate so and suggest the next best step.
"""
    ),
    model="gpt-4o-mini",
    output_type=FrontDeskOutput
)

# --- Tool for SQL Execution ---

@function_tool
def get_sql_respo(sql_query: str):
    """Executes SQL query and returns results from athlete schedules."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="Privacy@100",
            port=5432
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.commit()  # Commit the transaction to ensure changes are saved
        cursor.close()
        conn.close()
        return results
    except Exception as e:
        print("Error executing SQL:", e)
        return []

moderator_agent = Agent(
    name="Agents Response Moderator",
    instructions=(
        "You are an Agents' Response Moderator. Your task is to take the agent's response and rephrase it into a clear, "
        "simple, and smooth version that is easy to understand and friendly in tone.\n"
        "- Maintain the original meaning and key details.\n"
        "- Use natural, conversational language.\n"
        "- Make the response concise but complete.\n"
        "- Ensure the tone is polite, approachable, and professional.\n"
        "- Avoid jargon or overly complex phrases.\n"
        "Your goal is to enhance readability and improve the user's experience with clear, friendly communication."
    ),
    tools=[get_sql_respo]
)

# --- Agent Caller ---

async def call_agent(agent, user_query):
    with trace(f"{agent.name}"):
        # Always pass a string as user_query unless the agent expects a dict
        # Fix: Always wrap input in a dict if agent expects a pydantic model
        # This avoids passing a dict directly to Runner.run, which can cause attribute errors
        if hasattr(agent, "output_type") and hasattr(agent.output_type, "__fields__"):
            # If the agent expects a pydantic model, pass a dict with the correct keys
            if isinstance(user_query, dict):
                result = await Runner.run(agent, user_query)
            else:
                # Try to wrap string input into the expected field if possible
                # For most agents, the input is just a string, so pass as is
                result = await Runner.run(agent, user_query)
        else:
            result = await Runner.run(agent, user_query)
    return result.final_output

# --- Chatbot Function ---

def ensure_chat_format(history):
    safe_history = []
    for msg in history:
        if (
            isinstance(msg, dict)
            and "role" in msg
            and "content" in msg
            and isinstance(msg["content"], str)
            and msg["content"].strip() != ""
        ):
            safe_history.append({
                "role": str(msg["role"]),
                "content": msg["content"]
            })
    return safe_history

async def handle_conversation(user_input, history=None):
    if history is None:
        history = []

    # 1. Detect intent
    intent_result = await call_agent(intent_agent, user_input)
    is_sql = intent_result.SQL_agent
    is_knowledge = intent_result.knowledge_agent

    responses = []
    final_response = ""

    if not is_sql and not is_knowledge:
        final_response = "I'm not sure how to help with that yet, but I'll note it down."
    else:
        if is_sql:
            sql_response = await call_agent(sql_agent, user_input)
            sql_query = getattr(sql_response, "sql_query", None)
            moderated_sql_response = await call_agent(moderator_agent, sql_query)
            responses.append(moderated_sql_response)
            final_response = await call_agent(frontdesk_agent, str(moderated_sql_response))

        if is_knowledge:
            knowledge_response = await call_agent(knowledge_agent, user_input)
            responses.append(knowledge_response)
            final_response = await call_agent(frontdesk_agent, str(knowledge_response))

    # Add to chat history
    history.append({"role": "user", "content": str(user_input)})
    if hasattr(final_response, "respond_to_user"):
        val = final_response.respond_to_user
        if isinstance(val, bool):
            assistant_message = "Okay." if val else "No further action."
        else:
            assistant_message = str(val)
    else:
        assistant_message = str(final_response)
    history.append({"role": "assistant", "content": assistant_message})

    # 4. Store context
    context = {}
    context["last_intent"] = intent_result
    context["last_response"] = final_response

    # Debug: print what you are returning
    logger.debug("Returning history to Gradio:")
    pprint.pprint(history)

    return ensure_chat_format(history), history

# --- Gradio Interface ---

demo = gr.Interface(
    fn=handle_conversation,
    inputs=[
        gr.Textbox(label="Message", placeholder="Type your message here..."),
        gr.State()  # exactly one state input
    ],
    outputs=[
        gr.Chatbot(label="Chat History", height=600, type="messages"),
        gr.State()  # exactly one state output
    ],
    title="Athlete Assistant",
    description="Your personal assistant for managing athlete schedules and information"
)

if __name__ == "__main__":
    demo.launch(debug=True)
