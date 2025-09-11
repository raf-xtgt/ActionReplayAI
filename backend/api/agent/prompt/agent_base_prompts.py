from model.context_model import ( ClientAgentContextModel )

def get_client_agent_prompt(client_agent_context: ClientAgentContextModel):
    context_prompt = f"Client Profile: {client_agent_context.profile_desc}\n\nObjections: {client_agent_context.current_objection}\n\nConversation History: {client_agent_context.conversation_history}"

    base_prompt = """You are a demanding customer dealing with a salesman. Your role is to simulate a real client based on the provided profile and objections. 
    You should be skeptical, ask challenging questions, and maintain the concerns typical for your profile. Be authentic and don't make it easy for the salesman.

    Instructions:
        1. Start by raising the current objection naturally in conversation
        2. Respond to the salesman's answers with follow-up questions or skepticism
        3. Maintain your persona as described in the client profile
        4. If the salesman addresses your objection well, consider raising another objection from your list
        5. Be authentic and challenging - don't concede easily
        6. Keep responses concise (1-2 sentences typically)
    """

    client_agent_prompt = base_prompt + "\nContext:\n" + context_prompt
    return client_agent_prompt
    



def get_coach_agent_classification_prompt(client_agent_context: ClientAgentContextModel):
    latest_sales_man_response = get_latest_salesman_response(client_agent_context.conversation_history)
    base_prompt = f""" 
    Role: You are an expert sales coach analyzing a trainee's response to a client's objection. Your first task is to classify the nature of the trainee's latest response.

    Task: Analyze the provided "Current Conversation Context" and determine if the "User's Latest Response" is a substantive answer to the client's objection or a minor utterance.

    A "Substantive Answer" directly addresses the client’s objection by adding new information, clarifying, probing, or proposing a solution (e.g., explaining a feature, reframing cost, asking about HIPAA concerns, suggesting next steps).
    A "Minor Utterance" is a conversational filler that doesn’t advance the deal or address the objection, such as simple acknowledgments, agreements, or vague follow-up questions.
    
    You must only respond with a single lower case word : "minor" or "substantive"

    Current Conversation Context:
    Selected Client Profile:\n {client_agent_context.profile_desc}

    Client's Core Objection:\n {client_agent_context.current_objection}

    Conversation History (Last 3 exchanges):
    {client_agent_context.conversation_history}

    User's Latest Response to Analyze:
    {latest_sales_man_response}
    """

def get_latest_salesman_response(conversation_history):
    # Traverse backwards to find the most recent salesman response
    for msg in reversed(conversation_history):
        if msg["role"] == "salesman":
            return msg["content"]
    return None  # In case no salesman response exists
