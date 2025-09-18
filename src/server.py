import secrets
import asyncio
import logging
from flask import Flask, redirect, request, render_template, session

from schema import Message, CSVFile, UnstructuredFile
from knowledge_graph_workflow import KnowledgeGraphCreationWorkflow
from signalling import USER_SENT_MESSAGE


app = Flask(__name__, template_folder="templates")
app.secret_key = secrets.token_urlsafe(16)
logger = logging.getLogger(__name__)


@app.route("/", methods=["GET"])
def root():
    return render_template("file_upload.html")


@app.route("/upload_files", methods=["POST"])
def upload_files():

    # Initialize session storage for files & a message history list
    session['csv_files'] = []
    session['unstructured_files'] = []
    session['messages'] = []
    session.modified = True

    for file in request.files.getlist("fileUploader"):

        if file.filename.endswith('.csv'): # CSV files
            csv_file = CSVFile.from_bytesIO(file.filename, file.stream._file)
            session['csv_files'].append(csv_file)

        else: # Unstructured files
            unstructured_file = UnstructuredFile.from_bytesIO(file.filename, file.stream._file)
            session['unstructured_files'].append(unstructured_file)
        
        session.modified = True

    logger.info(f"CSV FILES: { [file.name for file in session['csv_files']]}")
    logger.info(f"UNSTRUCTURED FILES: { [file.name for file in session['unstructured_files']] }")

    # Initialize top-level workflow and store in session
    session['workflow'] = KnowledgeGraphCreationWorkflow(
        csv_files=session['csv_files'],
        unstructured_files=session['unstructured_files']
    )

    return redirect("/chat")


@app.route("/chat", methods=["GET"])
def chat():
    return render_template(
        "chat.html", 
        messages=[message for message in session.get('messages', [])]
    )


@app.route("/send_message", methods=["POST"])
async def send_message():
    user_message = request.form.get('message')
    session['messages'].append(Message(sender='user', content=user_message))
    session.modified = True

    # Run workflow if this is user's 1st message
    if len(session['messages']) == 1:
        await session['workflow'].arun(user_message)

    USER_SENT_MESSAGE.set() 

    return redirect("/chat")


if __name__ == "__main__":
    app.run(debug=True)