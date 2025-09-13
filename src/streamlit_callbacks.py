import streamlit as st
from agent.schema import CSVFile, UnstructuredFile, AgentsState
import logging


def on_files_submit():
    """ 
    Callback for when user submits file selection.
    """

    # Create & Keep track of agents' state object 
    agents_state = AgentsState(
        messages=[], 
        csv_files=[CSVFile.from_bytesIO(file) for file in st.session_state.csv_file_uploader],
        unstructured_files=[UnstructuredFile.from_bytesIO(file) for file in st.session_state.unstructured_file_uploader]
    )
    st.session_state.agents_state = agents_state

    logger = logging.getLogger(__name__)
    logger.info(f"CSV FILES: {[file.name for file in st.session_state.csv_file_uploader]}")
    logger.info(f"UNSTRUCTURED FILES: {[file.name for file in st.session_state.unstructured_file_uploader]}")


def on_msg_submit():
    """ Callback for when user submits a message. """

    # Add message to chat history & agents' state
    message = {"role": "user", "content": st.session_state.user_input}
    if "messages" in st.session_state:
        st.session_state.messages.append(message)
    else:
        st.session_state.messages = [message]
    st.session_state.agents_state.messages.append(message)

    # Render message history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
