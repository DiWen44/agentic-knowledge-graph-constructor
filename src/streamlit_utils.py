import streamlit as st
from schema import Message


def write_to_streamlit(content: str):
    """ 
    For an agent/workflow to use to write a message to the streamlit UI
    Args:
        content - message content, can contain markdown formatting
    """

    # Add message to chat history
    latest_message = Message(role="ai", content=content)
    if "messages" in st.session_state:
        st.session_state.messages.append(latest_message)
    else:
        st.session_state.messages = [latest_message]

    # Render latest message
    with st.chat_message(latest_message.role):
        st.markdown(latest_message.content)


async def get_latest_user_message() -> Message:
    """
    For an agent/workflow to use to get the user's latest message from streamlit
    """
    await st.session_state.USER_SENT_MESSAGE.wait() # Block until user sends message
    msg = st.session_state.messages[-1]
    st.session_state.USER_SENT_MESSAGE.clear() # Retrieved message, so clear 
    return msg

