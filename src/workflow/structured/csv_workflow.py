from typing import Dict, TypedDict
from agno.workflow import Workflow, Step, StepInput, StepOutput

from src.common import UserGoal
from src.common.structured import CSVFile

class CSVWorkflow:
    """
    Wrapper class for the structured (csv) data processing workflow

    Attributes:
        workflow - the underlying agno Workflow object
    """

    workflow: Workflow


    class State(TypedDict):
        """ 
        Session state dict schema for the agno workflow. 
        Attributes:
            files - CSV files provided by user, mapped by filename
            user_goal - user's objective, passed from top-level workflow
        """
        files: Dict[str, CSVFile]
        user_goal: UserGoal = None 


    def __init__(self, csv_files: Dict[str, CSVFile], user_goal: UserGoal) -> None:
        self.workflow = Workflow(
            name='structured-data-workflow',
            session_state=self.State(
                files=csv_files,
                user_goal=user_goal
            ),
            steps=[
                # Define the steps for the structured data workflow here
            ],
        )


    def get_workflow(self) -> Workflow:
        """ Get underlying Workflow object, for construction of higher-level workflow """
        return self.workflow