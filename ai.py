import json
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_ai_response(messages: list, settings: dict) -> str:
    system_prompt = f"You are an intelligent AI assistant for {settings['user_name']}. Be natural, helpful, and human-like. Answer basic FAQs using this info: {settings['user_info']}. Ask clarifying questions if needed. Set expectations like 'I'll note this down for {settings['user_name']}.' The user is busy, so handle initial queries."
    gpt_messages = [{'role': 'system', 'content': system_prompt}] + messages[-5:]
    response = client.chat.completions.create(
        model="gpt-4",
        messages=gpt_messages,
        temperature=0.7
    )
    return response.choices[0].message.content

def analyze_importance(messages: list, settings: dict, num_exchanges: int) -> dict:
    conv_text = '\n'.join([f"{msg['role']}: {msg['content']}" for msg in messages])
    keywords = [kw.strip().lower() for kw in settings['keywords'].split(',')]
    threshold_desc = {
        'Low': 'Escalate if urgency is medium or higher, or any negative sentiment, or complex.',
        'Medium': 'Escalate if urgency high, or strong negative/positive sentiment, or complex after 2-3 exchanges.',
        'High': 'Escalate only if urgency high and keywords present, or very negative sentiment.'
    }[settings['importance_threshold']]
    analysis_prompt = f"""
    Analyze this conversation:
    {conv_text}

    - Sentiment score: -1 (very negative) to 1 (very positive)
    - Urgency: low, medium, high
    - Intent: brief description
    - Complex question: true if cannot answer confidently after {num_exchanges} exchanges
    - Based on threshold: {threshold_desc} and if keywords like {','.join(keywords)} present.
    - Escalate: true/false

    Output as JSON: {{"sentiment_score": float, "urgency": "low/medium/high", "intent": "str", "complex": bool, "escalate": bool}}
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{'role': 'user', 'content': analysis_prompt}],
        temperature=0.0,
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

def generate_summary(conv_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{'role': 'user', 'content': f"Provide a concise summary of this conversation: {conv_text}"}],
        temperature=0.7
    )
    return response.choices[0].message.content

def generate_key_points(conv_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{'role': 'user', 'content': f"Extract 2-3 key points as bullet points: {conv_text}"}],
        temperature=0.7
    )
    return response.choices[0].message.content

def generate_suggested_action(conv_text: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{'role': 'user', 'content': f"Suggest an action for the user: {conv_text}"}],
        temperature=0.7
    )
    return response.choices[0].message.content