import streamlit as st
from schema import CSVFile, UnstructuredFile, Message
from knowledge_graph_workflow import KnowledgeGraphCreationWorkflow
import logging


def on_files_submit():
    """ 
    Callback for when user submits file selection.
    """

    # Add files to streamlit session data
    st.session_state.csv_files=[CSVFile.from_bytesIO(file) for file in st.session_state.csv_file_uploader]
    st.session_state.unstructured_files=[UnstructuredFile.from_bytesIO(file) for file in st.session_state.unstructured_file_uploader]

    logger = logging.getLogger(__name__)
    logger.info(f"CSV FILES: {[file.name for file in st.session_state.csv_file_uploader]}")
    logger.info(f"UNSTRUCTURED FILES: {[file.name for file in st.session_state.unstructured_file_uploader]}")

    # Initialize langgraph workflow & store it in the session state
    st.session_state.workflow = KnowledgeGraphCreationWorkflow(
        csv_files=st.session_state.csv_files,
        unstructured_files=st.session_state.unstructured_files
    )


def on_msg_submit():
    """ Callback for when user submits a message. """
    
    # If user hasn't uploaded files - meaning the workflow hasn't been initialized yet
    try:
        if st.session_state.csv_files == [] and st.session_state.unstructured_files == []:
            st.error("ERROR: Please upload files first.")
            return
    except AttributeError:
        st.error("ERROR: Please upload files first.")
        return

    # Add message to chat history
    latest_message = Message(role="human", content=st.session_state.user_input)
    if "messages" in st.session_state:
        st.session_state.messages.append(latest_message)
    else:
        st.session_state.messages = [latest_message]

    # Render message history
    for message in st.session_state.messages:
        with st.chat_message(message.role):
            st.markdown(message.content)

    st.session_state.workflow.run(latest_message)
