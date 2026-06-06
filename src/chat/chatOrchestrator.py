from src.chat.userValidation import validateUser
from src.connectors.web_llm_connector import web_handshake, web_use_chat
from src.system.load_prompt import load_prompt
from src.microservices.microServiceManager import microManager
from src.system.token_managment import update_token_balance
from src.system.load_microservice import fetch_all_microservices
from src.analytics.report_tools import run_analytics_tool
from src.microservices.helpers import tool_result_to_df
import streamlit as st
import json


def make_payload(
    last_microservice=None,
    llm_message="",
    user_backend_message="",
    microservice_llm_message="",
    has_file=False,
    usage=None,
    display_data=False,
    token_payload=None,
    call_context=None,
    tool_decision=None
):
    return {
        "last_microservice": last_microservice,
        "llm_message": llm_message,
        "user_backend_message": user_backend_message,
        "microservice_llm_message": microservice_llm_message,
        "has_file": has_file,
        "tool_decision": tool_decision,
        "usage": usage or {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        },
        "display_data": display_data,
        "token_payload": token_payload,
        "call_context": call_context
    }


def start_user_session(user_id):
    validation_payload = validateUser(user_id)
    allowed = validation_payload.get("allowed")
    model_status = False

    if allowed:
        model_status = web_handshake()
    else:
        model_status = None

    return validation_payload, model_status


def handle_user_message(user_msg: str, header: dict, logger=None):
    logger = logger or (lambda *_: None)

    user_id = header.get("user_id")

    validation_payload = validateUser(user_id)
    allowed = validation_payload.get("allowed", False)

    if not allowed:
        logger("User not allowed to send messages")

        return make_payload(
            llm_message="Brak aktywnego dostępu do aplikacji. Zaloguj się ponownie lub skontaktuj się z administratorem.",
            user_backend_message="",
            microservice_llm_message="",
            has_file=False,
            usage={
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            },
            token_payload=None,
            display_data=False,
            call_context="error"
        )

    logger("Validating message")

    payload = chat_flow(
        user_msg,
        header,
        allow_microservice=True,
        logger=logger,
        call_context="main"
    )

    token_payload = update_tokens_from_usage(header, payload.get("usage"), logger)
    payload["token_payload"] = token_payload

    logger("Request completed")

    return payload



def handle_backend_message(backend_msg: str, header: dict, logger=None, call_context="analyst"):
    logger = logger or (lambda *_: None)

    if not call_context:
        call_context = "analyst"

    logger("Generating response")

    payload = chat_flow(
        backend_msg,
        header,
        allow_microservice=False,
        logger=logger,
        call_context=call_context
    )

    token_payload = update_tokens_from_usage(header, payload.get("usage"), logger)
    payload["token_payload"] = token_payload

    logger("Response generated")

    return payload


def update_tokens_from_usage(header: dict, usage, logger=None):
    logger = logger or (lambda *_: None)

    user_id = header.get("user_id")

    if not user_id:
        logger("Token update skipped: missing user_id")
        return None

    token_used = usage.get("total_tokens") if usage else 0

    logger(f"Updating token balance. Tokens used: {token_used}")

    token_payload = update_token_balance(user_id, token_used)

    return token_payload


def chat_flow(msg: str, header: dict, allow_microservice=True, logger=None, call_context="main"):
    logger = logger or (lambda *_: None)

    if not call_context:
        call_context = "main" if allow_microservice else "analyst"

    logger(f"Call context: {call_context}")

    last_microservice = header.get("last_microservice", "")

    contexted_msg = prepare_llm_message(
        msg=msg,
        header=header,
        allow_microservice=allow_microservice,
        call_context=call_context
    )

    raw_llm_response, usage = call_llm(
        contexted_msg=contexted_msg,
        logger=logger
    )

    if not allow_microservice:
        return make_payload(
            last_microservice=last_microservice,
            llm_message=raw_llm_response,
            usage=usage,
            display_data=False,
            call_context=call_context
        )

    logger("Parsing LLM response")

    try:
        llm_response = parse_main_response(raw_llm_response)
    except Exception as e:
        logger(f"Error parsing LLM response: {type(e).__name__}: {e}")
        st.error(f"Error parsing LLM response: {e}")

        return make_payload(
            last_microservice=last_microservice,
            llm_message="Sorry, I had trouble understanding the response from the LLM.",
            usage=usage,
            display_data=False,
            call_context=call_context
        )

    header_data = llm_response.get("header", {})

    route = str(header_data.get("routing") or "conversation").strip()
    microservice_route = str(header_data.get("microservice") or "").strip()
    display_data = header_data.get("display_data", False)
    llm_message = llm_response.get("llmMsg", "")

    logger(f"Route selected: {route}")
    logger(f"Microservice selected: {microservice_route}")

    service_list = fetch_all_microservices()
    available_routes = get_available_route_names(service_list)

    logger(f"Available routes: {available_routes}")

    if route == "conversation":
        return make_payload(
            last_microservice=last_microservice,
            llm_message=llm_message,
            usage=usage,
            display_data=False,
            call_context=call_context
        )

    if route == "endConnection":
        return make_payload(
            last_microservice=last_microservice,
            llm_message=llm_message,
            usage=usage,
            display_data=False,
            call_context=call_context
        )

    if not microservice_route or microservice_route not in available_routes:
        logger("Microservice missing or unavailable. Preparing alternatives.")

        backend_llm_message = microservice_context_glossary(
            user_question=msg,
            requested_microservice=microservice_route,
            service_list=service_list
        )

        fallback_payload = handle_backend_message(
            backend_llm_message,
            header,
            logger=logger,
            call_context="microservice_router"
        )

        final_message = extract_user_message_from_possible_json(
            fallback_payload.get("llm_message", "")
        )

        return make_payload(
            last_microservice=last_microservice,
            llm_message="",
            user_backend_message="",
            microservice_llm_message=final_message,
            has_file=False,
            usage=usage,
            display_data=False,
            call_context="microservice_router"
        )

    # Valid microservice/report
    logger(f"Running microservice: {microservice_route}")

    try:
        user_backend_message, backend_llm_message, user_id = microManager(
            microservice_route,
            logger=logger
        )

        logger("Microservice completed")
        tool_result = None
        tool_usage = None
        tool_decision = None

        request = header.get("user_message", msg)
        is_number_selection = str(request).strip().isdigit()

        if is_number_selection:
            logger("Tool selector skipped: report selected by number")
        else:
            tool_context = {
                "row_count": len(user_backend_message),
                "columns": list(user_backend_message.columns),
                "note": "Only schema information is provided. The backend will execute the calculation on the full DataFrame."
            }

            tool_result, tool_usage, tool_decision = run_tools_selector(
                msg=request,
                report_columns=tool_context,
                data=user_backend_message,
                logger=logger
            )

            logger(f"Tool result exists: {bool(tool_result)}")

            if tool_result:
                backend_llm_message = tool_result
                display_data = False



        logger("Generating explanation from result")

        analyst_payload = handle_backend_message(
            backend_llm_message,
            header,
            logger=logger,
            call_context="analyst"
        )

        microservice_llm_message = analyst_payload.get("llm_message", "")
        has_file = has_backend_object(user_backend_message)

        if has_file:
            last_microservice = {
                "name": microservice_route,
                "route": route,
                "report_user_request": msg,
                "last_llm_response": microservice_llm_message
            }

        return make_payload(
            last_microservice=last_microservice,
            llm_message=llm_message,
            user_backend_message=user_backend_message,
            microservice_llm_message=microservice_llm_message,
            has_file=has_file,
            usage=usage,
            display_data=display_data,
            call_context=call_context,
            tool_decision=tool_decision
        )

    except Exception as e:
        logger(f"Microservice failed: {type(e).__name__}: {e}")
        logger("Preparing available alternatives")

        backend_llm_message = microservice_context_glossary(
            user_question=msg,
            requested_microservice=microservice_route,
            service_list=service_list
        )

        fallback_payload = handle_backend_message(
            backend_llm_message,
            header,
            logger=logger,
            call_context="microservice_router"
        )

        final_message = extract_user_message_from_possible_json(
            fallback_payload.get("llm_message", "")
        )

        return make_payload(
            last_microservice=last_microservice,
            llm_message="",
            user_backend_message="",
            microservice_llm_message=final_message,
            has_file=False,
            usage=usage,
            display_data=False,
            call_context="microservice_router"
        )


def prepare_llm_message(msg: str, header: dict, allow_microservice=True, call_context="main"):
    additional_context = load_prompt(call_context)

    history = header.get("chat_history") or header.get("history") or ""
    last_microservice = header.get("last_microservice", "")

    if allow_microservice:
        available_microservices = fetch_all_microservices()

        return f"""
{additional_context}

MICROSERVICE CATALOGUE:
{available_microservices}

CONVERSATION HISTORY:
{history}

LAST USED MICROSERVICE:
{last_microservice}

USER MESSAGE:
{msg}
"""

    if call_context == "analyst":
        if isinstance(additional_context, dict):
            additional_context["input"]["user_message"] = header.get("user_message", "")
            additional_context["input"]["report_data"] = msg
            return json.dumps(additional_context, ensure_ascii=False)

        return f"""
{additional_context}

USER MESSAGE:
{header.get("user_message", "")}

REPORT DATA:
{msg}
"""

    return msg


def call_llm(contexted_msg: str, logger=None):
    logger = logger or (lambda *_: None)

    logger("Calling LLM")
    raw_llm_response, tokens = web_use_chat(contexted_msg)
    usage = build_usage_payload(tokens)

    return raw_llm_response, usage


def parse_main_response(raw_llm_response: str):
    return clean_llm_json(raw_llm_response)


def get_available_route_names(service_list):
    if not service_list:
        return []

    if isinstance(service_list, list):
        return [
            str(s.get("name", "")).strip()
            for s in service_list
            if isinstance(s, dict) and s.get("name")
        ]

    if isinstance(service_list, dict):
        if "name" in service_list:
            return [str(service_list["name"]).strip()]

        return [
            str(s.get("name", "")).strip()
            for s in service_list.values()
            if isinstance(s, dict) and s.get("name")
        ]

    return []


def has_backend_object(obj):
    if obj is None:
        return False

    if hasattr(obj, "empty"):
        return not obj.empty

    if isinstance(obj, str):
        return obj.strip() != ""

    return bool(obj)


def microservice_context_glossary(user_question="", requested_microservice=None, service_list=None):
    prompt = load_prompt("microservice_router")

    backend_llm_message = f"""
{prompt}

USER QUESTION:
{user_question}

REQUESTED MICROSERVICE:
{requested_microservice}

AVAILABLE MICROSERVICES:
{service_list}
"""

    return backend_llm_message



def run_tools_selector(msg, report_columns, data, logger=None):
    logger = logger or (lambda *_: None)

    prompt = load_prompt("tool_selector")

    constructed_msg = f"""
{prompt}

USER QUESTION:
{msg}

REPORT COLUMNS:
{json.dumps(report_columns, ensure_ascii=False)}
"""

    raw_response, usage = call_llm(constructed_msg, logger=logger)

    logger("LLM response for tool selector received")

    try:
        tool_decision = clean_llm_json(raw_response)
    except Exception as e:
        logger(f"Tool selector parse failed: {type(e).__name__}: {e}")
        return None, usage, None

    if not tool_decision.get("use_tool"):
        logger("Tool selector decided: no tool needed")
        return None, usage, tool_decision

    logger(f"Tool selector selected: {tool_decision.get('tool_name')}")

    try:
        tool_result = run_analytics_tool(
            data,
            tool_decision,
            user_question=msg
        )
    except Exception as e:
        logger(f"Analytics tool failed: {type(e).__name__}: {e}")
        return None, usage, tool_decision

    return tool_result, usage, tool_decision
    


def build_usage_payload(tokens):
    if not tokens:
        return {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }

    return {
        "prompt_tokens": getattr(tokens, "prompt_tokens", 0),
        "completion_tokens": getattr(tokens, "completion_tokens", 0),
        "total_tokens": getattr(tokens, "total_tokens", 0)
    }


def clean_llm_json(raw_response):
    if raw_response is None:
        raise ValueError("LLM response is None. Cannot parse JSON.")

    cleaned = raw_response.strip()

    if not cleaned:
        raise ValueError("LLM response is empty. Cannot parse JSON.")

    cleaned = cleaned.replace("```json", "")
    cleaned = cleaned.replace("```", "")
    cleaned = cleaned.strip()

    if not cleaned:
        raise ValueError("LLM response became empty after cleaning. Cannot parse JSON.")

    return json.loads(cleaned)


def extract_user_message_from_possible_json(raw_response):
    if raw_response is None:
        return ""

    if not isinstance(raw_response, str):
        return str(raw_response)

    cleaned = raw_response.strip()

    if not cleaned:
        return ""

    try:
        parsed = clean_llm_json(cleaned)

        if isinstance(parsed, dict):
            return parsed.get("llmMsg") or cleaned

        return cleaned

    except Exception:
        return cleaned