from typing import List
from pydantic import BaseModel, Field
from agno.workflow import  Loop, Step, StepInput, StepOutput

from src.common import UserGoal
from src.common.structured import CSVFile
from src.common.message import Message, get_latest_user_message

from .schema_critic_loop import SchemaCriticLoop


class SchemaProposalLoop():
    """
    Wrapper class for a schema proposal loop within a workflow.
    Proposes a list of types of entities & relationships, based on provided csv files.
    Loop runs until the user has approved a proposed schema, or max iterations reached.
    Consists of 2 top-level steps:
        1. get-user-input: retrieves user input from the flask app - this is either the initial user prompt to the workflow, or feedback on a proposed schema
        2. critic-loop: A nested loop consisting of 2 steps:
            a. propose-schema: has an agent derive a schema from the csv files.
            b. critique_schema: a 'critic' agent reviews the proposed schema.
            The loop continues until the critic agent approves the proposed schema, or max iterations reached. 
            If the former, the proposed schema is returned to the top-level loop for user approval.
            If the latter, the top-level loop continues and we go back to the user with a "don't know" message.

    If the user agrees with the proposed schema by inputting some message of approval, the agent in propose-schema marks the proposed schema as approved, 
    and the approved schema is added to the structured workflow's session state.
    
    Attributes:
        loop - the underlying agno workflow Loop object
        last_iteration_output_content - stores the output content of the final step of the last iteration, so as to have state persist across iterations.
            NOTE: Agno does not pass the output of the last step as an input to the first step of the next iteration, so we have to do this manually by capturing it here.
    """

    loop: Loop
    last_iteration_output_content: "SchemaProposalLoop.LoopState | None" = None  


    class AgentOutputSchema(BaseModel):
        """
        Schema for schema proposal agent's output

        Args:
            llm_message - Natural language text that the agent's LLM generates as part of it's response
            entity_types - the proposed list of entity types the agent has come up with
            relationship_types - the proposed list of relationship types the agent has come up with
            approved - if proposed schema has been approved by the user
        """
        llm_message: str = Field(description="Natural language text that the LLM generates as part of it's response")
        entity_types: List[str] = Field(default_factory=list, description="The proposed list of entity types the agent has come up with")
        relationship_types: List[str] = Field(default_factory=list, description="The proposed list of relationship types the agent has come up with")
        approved: bool = Field(default=False, description="Whether the proposed schema has been approved by the user")
    

    class LoopState(BaseModel):
        """
        A state object that gets passed as input & output content of the steps in the loop
        This is internal to the schema proposal loop and thus separate from the overall workflow session state.

        Attributes:
            chat_history - The chat history so far between the user and the schema proposal agent, as a list of messages.
            entity_types - The proposed list of entity types the schema proposal agent has come up with
            relationship_types - The proposed list of relationship types the schema proposal agent has come up with
            approved - if proposed schema has been approved by the user
        """
        chat_history: List[Message] = Field(default_factory=list, description="The chat history so far")
        entity_types: List[str] = Field(default_factory=list, description="The proposed list of entity types the agent has come up with")
        relationship_types: List[str] = Field(default_factory=list, description="The proposed list of relationship types the agent has come up with")
        approved: bool = Field(default=False, description="Whether the proposed schema has been approved by the user")

    
    def __init__(self, 
        files: List[CSVFile],
        user_goal: UserGoal,
        max_iterations: int = 10) -> None:

        self.loop = Loop(
            name='schema-proposal-loop',
            max_iterations=max_iterations,
            steps=[
                Step(name='get-user-input', executor=self.get_user_input),
                SchemaCriticLoop().get_loop()
            ],
            end_condition= ( lambda step_outputs: step_outputs[-1].content.approved ), # End loop if schema is marked approved
        )


    async def get_user_input(self, step_input: StepInput) -> StepOutput:
        """
        Step to get user input from the flask app.
        If this is the first iteration of the loop, the step_input.input will be the initial user prompt to the workflow.
        In subsequent iterations, it will be the latest user message from the flask app - either approval or feedback on proposed schema.

        Args:
            step_input - the input to this step, containing the overall loop state and the latest user message
        """
        state: SchemaProposalLoop.LoopState = step_input.content

        if self.last_iteration_output_content is None:
            # First iteration of the loop - initialize chat history with initial user message
            return StepOutput(
                content=self.LoopState(
                    chat_history=[Message( # Add initial user message as start of chat history
                        sender='user', 
                        content=step_input.input 
                    )],
                )
            )

        # Subsequent iterations - get latest user message from flask app
        user_msg: Message = await get_latest_user_message()
        return StepOutput(
            content=self.LoopState(
                chat_history=state.chat_history+[user_msg], # Add latest user message to chat history
                entity_types=state.entity_types,
                relationship_types=state.relationship_types,
            )
        )


    def get_loop(self) -> Loop:
        """ returns the underlying loop - for adding loop to a workflow """
        return self.loop