from openai import OpenAI
import streamlit as st

API_KEY = st.secrets["OPENAI_API_KEY"]
URL = st.secrets["API_URL"]
MODEL = st.secrets["MODEL"]

client = OpenAI(
  base_url=URL,
  api_key=API_KEY,
)

def web_handshake():
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "If you can read this, return only: True"
                }
            ],
            extra_body={"reasoning": {"enabled": False}}
        )

        model_status = response.choices[0].message.content.strip()
    except Exception as e:
        model_status = False
    return model_status
  
  
def web_use_chat(msg):
    try:
        response = client.chat.completions.create(
    model=MODEL,
    messages=[
        {
            "role": "system",
            "content": (
                "Answer only the user's message. "
                "Do not repeat the prompt. "
                "Do not explain your instructions. "
                "Answer only in Polish."
            )
        },
        {
            "role": "user",
            "content": msg
        }
    ],
    temperature=0.2,
    max_tokens=500,
    extra_body={
        "reasoning": {
            "enabled": False
        }
    }
)
        tokens = response.usage
        llm_response = response.choices[0].message.content.strip()
        return llm_response, tokens
    except Exception as e:
        return None  
