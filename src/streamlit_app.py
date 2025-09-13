import streamlit as st

with st.sidebar:
    st.title("Agentic Knowledge Graph Constructor")
    st.text("This is a multi-agent system that automates the creation\nof a knowledge graph from provided structured and\nunstructured data files.")
    st.file_uploader("Upload files") 



def on_msg_submit():
    """ 
    Callback for when user submits a message. 
    Add message to chat history & show full message history
    """
    
    if "messages" in st.session_state:
        st.session_state.messages.append({"role": "user", "content": st.session_state.user_input})
    else:
        st.session_state.messages = [{"role": "user", "content": st.session_state.user_input}]
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

st.chat_input(placeholder="Type here", on_submit=on_msg_submit, key="user_input")



