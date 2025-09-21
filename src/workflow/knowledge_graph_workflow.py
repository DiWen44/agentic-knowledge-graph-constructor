from typing import Dict, TypedDict
from agno.workflow import Workflow

from ..common.schema import CSVFile, UnstructuredFile, Message, UserGoal
from .user_intent import UserIntentLoop


class KnowledgeGraphCreationWorkflow:
    """
    Wrapper class for the top-level knowledge graph creation workflow

    Attributes:
        workflow - the underlying agno Workflow object
    """

    workflow: Workflow

    class State(TypedDict):
        """ 
        Session state dict schema for the agno workflow. 
        Attributes:
            csv_files - CSV (structured) files provided by user as a map of: filename string (with '.csv' extension) -> CSVFile
            unstructured_files - Unstructured files (i.e. "txt", "pdf", "md", "docx", "html") provided by user as a map of: filename string (with extension) -> UnstructuredFile
            user_goal - finalized/approved user's objective, initially empty/none but set by user intent loop

        """
        csv_files: Dict[str, CSVFile]
        unstructured_files: Dict[str, UnstructuredFile]
        user_goal: UserGoal = None


    def __init__(self, csv_files: Dict[str, CSVFile], unstructured_files: Dict[str, UnstructuredFile]) -> None:

        self.workflow = Workflow(
            name='knowledge-graph-creation-workflow',
            session_state=self.State(csv_files=csv_files, unstructured_files=unstructured_files),
            steps=[
                UserIntentLoop().get_loop()
            ],
        )


    async def run(self, message: Message) -> None:
        response = await self.workflow.arun(input=message['content'])
