from dotenv import load_dotenv
import chainlit as cl
import json
import movie_functions
import traceback

load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())

from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI
 
client = AsyncOpenAI()

gen_kwargs = {
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 1000
}

SYSTEM_PROMPT = """\
You are a helpful assistant with knowledge about movies. Your primary tasks are:

1. Respond to user queries about movies and provide information.
2. Detect when a user is requesting specific movie-related actions.
3. A user may make multiple requests in a single chat session, or the same request repeatedly.
4. When a specific action is requested, generate a function call instead of a direct response.
5. If there is no function call needed, respond directly to the user with your knowledge about movies, or let the user know if you don't have the answer.
6. If there is a function call, respond back to the user with the results of the function call appropriately. If the function call returns an empty result, let the user know.

For function calls, use the following format:
{"function": "function_name", "parameters": {param1: value1, param2: value2, ...}}

Make sure that only json is returned and no other text is a part of the response to a function call request.

The list of functions you can call are:
- get_now_playing_movies(): Use when the user asks for current or now playing movies.
- get_showtimes(title, location): This function is to list the showtimes of a movie in a specific location. Make sure to get the location from the user if not specified.
note that the location can be city or zipcode. If the user provides an unknown location, ask them for the city and state/zipcode to better assist them.
- buy_ticket(theater, movie, showtime): This is to be used to buy a ticket. This function may be invoked only after confirms their purchase from the confirm_ticket_purchase function. 
- confirm_ticket_purchase(theater, movie, showtime): Use when the user wants to purchase for a specific movie, theater, and showtime.
Make sure you have all the necessary information from the user for this call. It should ask the user for confirmation, and 
once the user confirms the purchase invoke the buy_ticket function.
- get_reviews(movie_id): Use when the user requests reviews for a specific movie and provide a brief summary of the reviews with audience score, critic score, 
some key quotes from the reviews with the link to the full reviews, and also some notable moments from the film without revealing the plot of the movie.

Only generate a function call when the user explicitly requests information that requires one of these functions. 
For all other queries, respond directly to the user with your knowledge about movies.

After receiving the results of a function call, incorporate that information into your response to the user.

Examples:
1. User: "What movies are playing now?"
   Function call: {"function": "get_now_playing_movies", "parameters": {}}

2. User: "What are the showtimes for Inception in New York?"
   Function call: {"function": "get_showtimes", "parameters": {"title": "Inception", "location": "New York"}}

3. User: "I want to buy a ticket for Avengers at AMC Theater for the 7 PM show."
   Function call: {"function": "buy_ticket", "parameters": {"theater": "AMC Theater", "movie": "Avengers", "showtime": "7 PM"}}

4. User: "Can you get me reviews for The Godfather?"
   Function call: {"function": "get_reviews", "parameters": {"movie_id": "The Godfather"}}

A user may make multiple requests in a single chat session.
Remember, only use these function calls when necessary. For general movie questions or discussions, respond directly using your knowledge.
"""

@observe
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()

    return response_message

def parse_response_for_function_call(response_message):
    function_call = None
    try:
        parsed_content = json.loads(response_message.content)
        if "function" in parsed_content and "parameters" in parsed_content:
            function_call = parsed_content
    except json.JSONDecodeError:
        pass

    return function_call

'''@cl.on_message
@observe()
async def on_message(message: cl.Message):
    response_contains_function_call = False
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)
    response_contains_function_call = parse_response_for_function_call(response_message)

    while(response_contains_function_call):
        if response_contains_function_call:

            # If a function call is detected, execute the corresponding function
            function_name = response_contains_function_call["function"]
            parameters = response_contains_function_call["parameters"]

            # Let the user know which function is being called
            await cl.Message(content=f"Calling function: {function_name}").send()
                
            # Append the function result to the message history
            message_history.append({"role": "assistant", "name": function_name, "content": function_name})
            
            print("Function Name:", function_name, "Parameters:", parameters)
        
            if hasattr(movie_functions, function_name) and callable(getattr(movie_functions, function_name)):
                function_result = getattr(movie_functions, function_name)(**parameters)
                
                # Send the function result to the user
                await cl.Message(content=f"Here's the result of the function call:\n\n{function_result}").send()
                
                # Append the function result to the message history
                message_history.append({"role": "assistant", "name": function_name, "content": function_result})
                
                # Generate a new response incorporating the function result
                response_message = await generate_response(client, message_history, gen_kwargs)
                response_contains_function_call = parse_response_for_function_call(response_message)
        else:
            response_contains_function_call = False

    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)
'''

@cl.on_message
@observe()
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    while True:
        response_message = await generate_response(client, message_history, gen_kwargs)
        function_call = parse_response_for_function_call(response_message)
        
        if not function_call:
            # No function call, send the response to the user and break the loop
            # await cl.Message(content=response_message.content).send()
            message_history.append({"role": "assistant", "content": response_message.content})
            break
        
        # Function call detected
        function_name = function_call["function"]
        parameters = function_call["parameters"]
        
        # await cl.Message(content=f"Calling function: {function_name}").send()
        
        if hasattr(movie_functions, function_name) and callable(getattr(movie_functions, function_name)):
            try:
                function_result = getattr(movie_functions, function_name)(**parameters)
                await cl.Message(content=f"Function result:\n\n{function_result}").send()
                
                # Append function call and result to message history
                message_history.append({"role": "assistant", "content": json.dumps(function_call)})
                message_history.append({"role": "function", "name": function_name, "content": function_result})
            except Exception as e:
                error_message = f"Error calling function {function_name}: {str(e)}"
                await cl.Message(content=error_message).send()
                message_history.append({"role": "system", "content": error_message})
        else:
            error_message = f"Function {function_name} not found"
            await cl.Message(content=error_message).send()
            message_history.append({"role": "system", "content": error_message})
    
    cl.user_session.set("message_history", message_history)
if __name__ == "__main__":
    cl.main()
