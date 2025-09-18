from typing import List, TypedDict
from agno.workflow import Workflow, Step, Loop, StepOutput

from schema import CSVFile, UnstructuredFile, Message, UserGoal
from user_intent import propose_user_goal, get_user_input


class KnowledgeGraphCreationWorkflow:
    """
    Wrapper class for the top-level knowledge graph creation workflow
    """

    class State(TypedDict):
        """ 
        Session state dict schema for the agno workflow. 
        Attributes:
            csv_files - CSV (structured) files provided by user
            unstructured_files - Unstructured files (i.e. "txt", "pdf", "md", "docx", "html") provided by user
            user_goal - finalized/approved user's objective, initially empty/none but set by user intent loop

        """
        csv_files: List[CSVFile]
        unstructured_files: List[UnstructuredFile]
        user_goal: UserGoal = None 


    def __init__(self, csv_files: List[CSVFile], unstructured_files: List[UnstructuredFile]) -> None:
        
        # Callback for terminating user intent loop - based on if user has approved the proposed user goal 
        def user_goal_approved(step_outputs: List[StepOutput]):
            return step_outputs[-1].content.goal_approved
    
        self.workflow = Workflow(
            name='knowledge-graph-creation-workflow',
            session_state=self.State(csv_files=csv_files, unstructured_files=unstructured_files),
            steps=[
                Loop(
                    name='user-intent-loop',
                    steps=[
                        Step(name='propose-user-goal', executor=propose_user_goal),
                        Step(name='get-user-input', executor=get_user_input)

                    ],
                    end_condition=user_goal_approved,
                    max_iterations=10
                )
            ],
        )


    async def run(self, message: Message) -> None:
        response = await self.workflow.arun(input=message['content'])
