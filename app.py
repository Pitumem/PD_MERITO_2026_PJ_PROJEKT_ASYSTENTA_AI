import streamlit as st
from datetime import datetime
from src.chat.chatOrchestrator import handle_user_message, start_user_session
import os
import hmac

def log(msg: str):
    if "log" not in st.session_state:
        st.session_state.log = []

    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.log.append(f"[{ts}] {msg}")

def get_review_password():
    try:
        return st.secrets["REVIEW_PASSWORD"]
    except Exception:
        return os.getenv("REVIEW_PASSWORD")


def validate_review_password(input_password: str) -> bool:
    expected_password = get_review_password()

    if not expected_password:
        return False

    if not input_password:
        return False

    return hmac.compare_digest(str(input_password), str(expected_password))

def render_logs():
    if "log" not in st.session_state:
        st.session_state.log = []

    if st.session_state.log:
        st.text("\n".join(reversed(st.session_state.log)))
    else:
        st.caption("No logs yet.")


def greeting_message(logger):
    header = {
        "user_id": st.session_state.get("user_id"),
        "logged_in": st.session_state.get("is_logged_in", False),
        "user_chosen_model": st.session_state.get("model", "ai"),
        "chat_history": st.session_state.get("history"),
        "history": st.session_state.get("history"),
        "last_microservice": st.session_state.get("last_microservice"),
        "user_message": "This is a handshake message. Greet yourself, state your role and capabilities."
    }

    system_msg = "This is a handshake message. Greet yourself, state your role and capabilities."

    payload = handle_user_message(system_msg, header, logger=log)

    reply = payload.get("llm_message")

    st.session_state.messages = [
        {
            "role": "assistant",
            "call_context": payload.get("call_context", "main"),
            "content": reply or "Hello 👋"
        }
    ]


if "is_logged_in" not in st.session_state:
    st.session_state.is_logged_in = False

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "tool_decision" not in st.session_state:
    st.session_state.tool_decision = None

if "chat_active" not in st.session_state:
    st.session_state.chat_active = False

if "log" not in st.session_state:
    st.session_state.log = []

if "last_microservice" not in st.session_state:
    st.session_state.last_microservice = None

if "messages" not in st.session_state:
    st.session_state.messages = []

if "tokens" not in st.session_state:
    st.session_state.tokens = 0

if "model" not in st.session_state:
    st.session_state.model = "ai"

if "history" not in st.session_state:
    st.session_state.history = None


# ---------- sidebar: login + log
with st.sidebar:
    if st.session_state.is_logged_in == False:
        st.subheader("Login 🧙‍♂️")
        user_id_input = st.text_input("User ID", value="Tester")
        review_password_input = st.text_input("Password", type="password")
        st.session_state.user_id = user_id_input
        st.session_state.model = "ai"

        if st.button("Login"):
            if not validate_review_password(review_password_input):
                st.session_state.is_logged_in = False
                st.session_state.chat_active = False
                st.session_state.user_id = None
                st.error("Access denied")
                st.stop()

            try:
                user_payload, model_status = start_user_session(user_id_input)

                allowed = user_payload.get("allowed", False)
                tokens = user_payload.get("tokens", 0)

                st.session_state.tokens = tokens
                st.session_state.user_id = user_id_input

                if allowed and tokens > 0:
                    st.session_state.chat_active = True
                else:
                    st.session_state.chat_active = False

                if "messages" not in st.session_state or not st.session_state.messages:
                    greeting_message(logger=log)

            except Exception as e:
                st.error(f"Error during login: {e}")
                allowed = False
                model_status = None
                st.session_state.chat_active = False

            if allowed:
                st.toast("🧙‍♂️ Success!")
                st.session_state.is_logged_in = True
                log("Login OK")

                if model_status:
                    log("Handshake successful, chat was created")
                else:
                    log("Handshake error")
                    st.error("Handshake error")

                st.rerun()
            else:
                st.session_state.is_logged_in = False
                st.session_state.chat_active = False
                st.session_state.user_id = None
                st.error("Access denied")
    
    else:
        user_id_input = st.session_state.user_id

        st.subheader("Zalogowany jako:")
        st.code(user_id_input)
        st.code(f"Tokeny: {st.session_state.tokens}")

        with st.expander("Options"):
            if st.toggle("Chat History", value=True, key="toggle_history"):
                history_length = st.slider(
                    "History length",
                    min_value=3,
                    max_value=10,
                    value=3,
                    step=1,
                    key="history_length"
                )

                passed_messages = st.session_state.messages[-history_length:]
                st.session_state.history = passed_messages
            else:
                st.session_state.history = None

            st.divider()

            action = st.menu_button(
                "Clear chat history",
                options=["YES, Delete", "NO, Keep it"]
            )

            if action == "YES, Delete":
                greeting_message(logger=log)
                st.session_state.log = []
                st.rerun()

            logout_action = st.menu_button(
                "Logout",
                options=["YES, logout", "NO, stay logged in"]
            )

            if logout_action == "YES, logout":
                st.session_state.is_logged_in = False
                st.session_state.chat_active = False
                st.session_state.user_id = None
                st.session_state.log = []
                st.session_state.tokens = 0
                st.session_state.history = None
                st.session_state.last_microservice = None
                st.session_state.tool_decision = None
                st.rerun()

        with st.expander("Last Report"):
            st.session_state.last_report = st.session_state.last_microservice

            if st.session_state.last_report:
                st.write(st.session_state.last_report["name"])
            else:
                st.write("No report generated yet.")

            st.divider()

            with st.expander("Użyte Toole:"):
                if st.session_state.tool_decision is not None:
                    st.write(st.session_state.tool_decision or "No tools used yet.")
                else:
                    st.write("Brak")

        st.divider()

        with st.expander("Backend log", expanded=False):
            if st.button("Clear log"):
                st.session_state.log = []

            with st.container(height=600, border=False):
                render_logs()


# ---------- main gate
if not st.session_state.is_logged_in:
    st.info("Enter User ID and click Login to continue.")
    st.stop()
else:
    st.title("🧙‍♂️ Raport Wizard", anchor=False)


# ---------- render chat
CONTEXT_LABELS = {
    "main": "Main assistant",
    "analyst": "Business analyst",
    "microservice_router": "Report router",
    "data": "Report data",
    "error": "Access control"
}


def render_message(m):
    with st.chat_message(m["role"]):
        content = m.get("content")

        if m.get("call_context") == "data":
            st.dataframe(content, width="stretch")
        elif m.get("call_context") == "error":
            st.error(content)
        else:
            st.write(content)

        if m["role"] == "assistant":
            call_context = m.get("call_context")

            if call_context:
                st.caption(f"Answered by: {CONTEXT_LABELS.get(call_context, call_context)}")

            if "tokens_used" in m:
                st.caption(f"Tokens used: {m['tokens_used']}")


def build_header(user_msg):
    return {
        "logged_in": st.session_state.is_logged_in,
        "user_chosen_model": st.session_state.model,
        "user_id": st.session_state.user_id,
        "chat_history": st.session_state.get("history"),
        "user_message": user_msg,
        "history": st.session_state.get("history"),
        "last_microservice": st.session_state.get("last_microservice")
    }


for m in st.session_state.messages:
    render_message(m)


user_msg = st.chat_input(
    "Say something",
    disabled=not st.session_state.chat_active
)

if st.session_state.chat_active == False:
    st.warning("Chat is inactive. Log in again or contact support.")


if user_msg:
    user_message = {
        "role": "user",
        "content": user_msg
    }

    st.session_state.messages.append(user_message)
    st.session_state.last_user_message = user_msg
    log("User message received")

    render_message(user_message)

    tokens_used = 0
    tool_decision = None
    last_microservice = st.session_state.get("last_microservice")
    reply = ""
    user_backend_object = ""
    microservice_llm_reply = ""
    hasFile = False
    display_data = False

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            header = build_header(user_msg)

            payload = handle_user_message(user_msg, header, logger=log)

            if payload.get("call_context") == "error":
                error_message = payload.get("llm_message") or "Brak aktywnego dostępu do aplikacji."

                st.session_state.chat_active = False
                st.session_state.is_logged_in = False

                assistant_message = {
                    "role": "assistant",
                    "call_context": "error",
                    "content": error_message,
                    "tokens_used": 0
                }

                st.session_state.messages.append(assistant_message)
                render_message(assistant_message)

                log("Access denied during message handling")
                st.rerun()

            tool_decision = payload.get("tool_decision")
            last_microservice = payload.get("last_microservice")
            token_payload = payload.get("token_payload")
            reply = payload.get("llm_message")
            user_backend_object = payload.get("user_backend_message")
            microservice_llm_reply = payload.get("microservice_llm_message")
            hasFile = payload.get("has_file")
            display_data = payload.get("display_data")

            if token_payload:
                st.session_state.tokens = token_payload.get(
                    "token_balance",
                    st.session_state.tokens
                )

                tokens_used = token_payload.get("tokens_used", 0)

                if token_payload.get("active") == False:
                    st.session_state.chat_active = False
            else:
                tokens_used = 0

            if tool_decision:
                st.session_state.tool_decision = tool_decision

            st.session_state.last_microservice = last_microservice

    log("Backend handler finished")

    if microservice_llm_reply:
        assistant_message = {
            "role": "assistant",
            "call_context": "analyst",
            "content": microservice_llm_reply,
            "tokens_used": tokens_used
        }

        st.session_state.messages.append(assistant_message)
        render_message(assistant_message)

    elif reply:
        assistant_message = {
            "role": "assistant",
            "call_context": "main",
            "content": reply,
            "tokens_used": tokens_used
        }

        st.session_state.messages.append(assistant_message)
        render_message(assistant_message)

    if hasFile and display_data:
        data_message = {
            "role": "assistant",
            "call_context": "data",
            "content": user_backend_object
        }

        st.session_state.messages.append(data_message)
        render_message(data_message)

    st.rerun()