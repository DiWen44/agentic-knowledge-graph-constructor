import streamlit as st
import streamlit_callbacks as callbacks

with st.sidebar:
    st.title("Agentic Knowledge Graph Constructor")
    st.text("This is a multi-agent system that automates the creation\nof a knowledge graph from provided structured and\nunstructured data files.")
    
    file_upload_form = st.form("Upload files")
    file_upload_form.file_uploader("Upload structured (CSV) files:", accept_multiple_files=True, key="csv_file_uploader", type="csv") 
    file_upload_form.file_uploader("Upload unstructured files:", accept_multiple_files=True, key="unstructured_file_uploader", type=["txt", "pdf", "md", "docx", "html"]) 
    file_upload_form.form_submit_button("Confirm", on_click=callbacks.on_files_submit)

st.chat_input(placeholder="Type here", on_submit=callbacks.on_msg_submit, key="user_input")





