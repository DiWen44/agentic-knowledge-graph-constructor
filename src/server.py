import secrets
import logging
from flask import Flask, redirect, request, render_template, session
from flask_session import Session
from redis import Redis

from schema import Message, CSVFile, UnstructuredFile
from knowledge_graph_workflow import KnowledgeGraphCreationWorkflow

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates")

# Support for serverside sessions
SESSION_TYPE = 'redis'
SESSION_REDIS = Redis(host='localhost', port=6379)
app.config.from_object(__name__)
Session(app)
logger.info("CONNECTED TO REDIS SERVER")


@app.route("/", methods=["GET"])
def root():
    return render_template("file_upload.html")


@app.route("/upload_files", methods=["POST"])
def upload_files():

    # Initialize session storage for files & a message history list
    session['csv_files'] = []
    session['unstructured_files'] = []
    session['messages'] = []

    for file in request.files.getlist("fileUploader"):

        if file.filename.endswith('.csv'): # CSV files
            csv_file = CSVFile.from_bytesIO(file.filename, file.stream._file)
            session['csv_files'].append(csv_file)

        else: # Unstructured files
            unstructured_file = UnstructuredFile.from_bytesIO(file.filename, file.stream._file)
            session['unstructured_files'].append(unstructured_file)

    logger.info(f"CSV FILES: { [file.name for file in session['csv_files']]}")
    logger.info(f"UNSTRUCTURED FILES: { [file.name for file in session['unstructured_files']] }")

    """
    # Initialize top-level workflow and store in session
    session['workflow'] = KnowledgeGraphCreationWorkflow(
        csv_files=session['csv_files'],
        unstructured_files=session['unstructured_files']
    )
    """
    return redirect("/chat")


@app.route("/chat", methods=["GET"])
def chat():
    return render_template(
        "chat.html", 
        messages=[message for message in session.get('messages', [])]
    )


@app.route("/send_message", methods=["POST"])
async def send_message():
    user_message = Message(
        sender='user', 
        content=request.form.get('message')
    )
    session['messages'].append(user_message)

    # Run workflow if this is user's 1st message
    # NOTE: Workflow initialized here as part of placeholder
    # ENTIRE WORKFLOW IS RUN WITHIN THIS ENDPT. USER INPUT GOT VIA CLI
    if len(session['messages']) == 1:
        workflow = KnowledgeGraphCreationWorkflow(
                csv_files=session['csv_files'],
                unstructured_files=session['unstructured_files']
        )
        await workflow.run(user_message)

    return redirect("/chat")


if __name__ == "__main__":
    app.run(debug=True)