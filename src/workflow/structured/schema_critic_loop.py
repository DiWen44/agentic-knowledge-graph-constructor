from typing import List, Dict
from pydantic import BaseModel, Field
from textwrap import dedent
from agno.workflow import  Loop, Step, StepInput, StepOutput
from agno.agent import Agent
from agno.models.google.gemini import Gemini

from src.common import UserGoal
from src.common.structured import StructuredSchema


class SchemaCriticLoop():
    """
    Wrapper class for a nested schema critic loop within the schema proposal loop.
    Consists of 2 steps:
        1. propose-schema: has an agent derive a schema from the csv files.
        2. critique_schema: a 'critic' agent reviews the proposed schema.

    The loop continues until the critic agent approves the proposed schema, or max iterations reached. 
    If the former, the proposed schema is returned to the higher-level loop for user approval.
    If the latter, give a "don't know" message to the higher-level loop.

    ATTRIBUTES:
        loop - the underlying agno workflow Loop object
        proposal_agent - the schema proposal agent used in the propose-schema step
        critic_agent - the schema critic agent used in the critique-schema step
        last_iteration_output_content - stores the output content of the final step of the last iteration, so as to have state persist across iterations.
            NOTE: Agno does not pass the output of the last step as an input to the first step of the next iteration, so we have to do this manually by capturing it here.
    """

    loop: Loop
    proposal_agent: Agent
    critic_agent: Agent
    last_iteration_output_content: "SchemaCriticLoop.LoopState | None" = None

    
    class LoopState(BaseModel):
        """
        A state object that gets passed as input & output content of the steps in the loop.
        It's passed as input to both the proposal agent and the critic agent.
        This is internal to the schema proposal loop and thus separate from the overall workflow session state.
        """

        # STATIC FIELDS - not to change after being set
        file_samples: Dict[str, List[str]] = Field(description="The first 11 rows of the provided CSV files (1st row being column headers). Provided as a dict mapping the filename to a list of rows.")
        user_goal: UserGoal = Field(description="The user's objective in making a knowledge graph")

        # DYNAMIC FIELDS - to be updated by the steps in the loop
        proposed_schema: StructuredSchema | None = Field(default=None, description="The proposed schema from the proposal agent")
        critic_feedback: str = Field(default="", description="Feedback from the critic agent")


    def __init__(self, max_iterations: int = 10) -> None:

        self.proposal_agent = Agent(
            name="proposal-agent",
            model=Gemini(id="gemini-2.5-flash-lite"),
            input_schema=self.LoopState,
            output_schema=StructuredSchema,
            instructions=dedent(f"""
            You are an expert at knowledge graph schema design. Your task is to propose a schema for a knowledge graph that can fulfill a provided user goal. 
            The knowledge graph will be created from some CSV files. The first 11 rows of each file (the first row being column headings) will be provided to you. Use them to ascertain a schema that fulfills the user goal.
            You'll also be given feedback from a critic agent on a previous proposed schema. Use this to refine the schema.

            A knowledge graph schema consists of 2 lists:
            - a list of entity types (nodes) (e.g. Person, Company, Product)
            - a list of relationship types (edges). Each relationship type is a list of [SOURCE_ENTITY_TYPE, RELATIONSHIP_TYPE, DESTINATION_ENTITY_TYPE], 
                thus specifying the concerned entity types as well as the nature of the relationship itself.
                e.g. [Person, WORKS_AT, Company], [Product, MANUFACTURED_BY, Company]
                
            Note that you are not being asked to extract instances of entities (e.g Joe, Mark, Devin) or relationships (e.g. Joe likes Mark), just the high-level entity types and relationship types.

            # SCHEMA RULES & GUIDANCE
            Every file in the approved files list will become either a node or a relationship. Determining whether a file likely represents a node or a relationship is based on a hint from the filename
            (is it a single thing or two things) and the identifiers found within the file. Because unique identifiers are so important for determining the structure of the graph, 
            always verify the uniqueness of suspected unique identifiers by examining the file samples.

            The resulting schema should be a connected graph, with no isolated components.

            ## General guidance for identifying a node or a relationship
            - If the file name is singular and has only 1 unique identifier it is likely a node
            - If the file name is a combination of two things, it is likely a full relationship
            - If the file name sounds like a node, but there are multiple unique identifiers, that is likely a node with reference relationships

            ## Design rules for nodes
            - Nodes will have unique identifiers.
            - Nodes _may_ have identifiers that are used as reference relationships.
            
            ## Design rules for relationships
            Relationships appear in two ways: full relationships and reference relationships.

            ### Full relationships
            - Full relationships appear in dedicated relationship files, often having a filename that references two entities
            - Full relationships typically have references to a source and destination node.
            - Full relationships _do not have_ unique identifiers, but instead have references to the primary keys of the source and destination nodes.
            - The absence of a single, unique identifier is a strong indicator that a file is a full relationship.

            ### Reference relationships
            - Reference relationships appear as foreign key references in node files
            - Reference relationship foreign key column names often hint at the destination node and relationship type
            - References may be hierarchical container relationships, with terminology revealing parent-child, "has", "contains", membership, or similar relationship
            - References may be peer relationships, that is often a self-reference to a similar class of nodes. For example, "knows" or "see also"
            """),
            debug_mode=True,
        )

        self.critic_agent = Agent(
            name="critic-agent",
            model=Gemini(id="gemini-2.5-flash-lite"),
            input_schema=self.LoopState,
            instructions=dedent(f"""
            You are an expert at knowledge graph schema design. Your task is to critique the proposed knowledge graph schema put forth by a proposal agent.
            
            A knowledge graph schema consists of 2 lists:
                - a list of entity types (nodes) (e.g. Person, Company, Product)
                - a list of relationship types (edges). Each relationship type is a list of [SOURCE_ENTITY_TYPE, RELATIONSHIP_TYPE, DESTINATION_ENTITY_TYPE], 
                    thus specifying the concerned entity types as well as the nature of the relationship itself.
                    e.g. [Person, WORKS_AT, Company], [Product, MANUFACTURED_BY, Company]

            The proposed schema should be evaulated against the user goal (provided as an input) to determine it's alignment with the user's objective.
            The knowledge graph will be created from some CSV files. The first 11 rows of each file (the first row being column headings) will be provided to you, 
            so you can test the accuracy of the proposed schema.

            Based on the proposed entity types and relationship types, provide feedback on their relevance to the user's objective and their completeness.
            If you believe the proposed schema is (sufficiently) appropriate and complete, respond with only the word "APPROVED".

            When providing feedback, aim to be concise and specific: clearly mention any suggested changes, and do not provide generic feedback.
            Do not provide any positive/affirmative feedback - only suggest changes or state "APPROVED".
            """),
            debug_mode=True
        )

        self.loop = Loop(
            name='schema-critic-loop',
            max_iterations=max_iterations,
            steps = [
                Step(name='propose-schema', executor=self.propose_schema),
                Step(name='critique-schema', executor=self.critique_schema)
            ],
            end_condition=( lambda step_outputs: step_outputs[-1].critic_feedback == "APPROVED" ), # End loop if critic agent approves
        )

    async def propose_schema(self, step_input: StepInput, session_state) -> StepOutput:
        """ LOOP STEP 1: Proposes a schema based on the provided CSV files."""

        if self.last_iteration_output_content is None: # If this is the first iteration of loop - create LoopState de novo
            state = SchemaCriticLoop.LoopState(
                user_goal = session_state['user_goal'],
                file_samples = {filename: file.sample() for filename, file in session_state['files'].items()} # Get file samples from session state files 
            )
        else:
            # First step in loop, so input is output of last step of previous iteration
            state: SchemaCriticLoop.LoopState = self.last_iteration_output_content 

        response = await self.proposal_agent.arun(state)
        return StepOutput(
            content=self.LoopState(
                file_samples=state.file_samples,
                user_goal=state.user_goal,
                proposed_schema=response.content,
                # Reset critic feedback to default empty str
            )
        )
    
    async def critique_schema(self, step_input: StepInput) -> StepOutput:
        """ LOOP STEP 2: Critiques the proposed schema by the proposal agent."""
        state: SchemaCriticLoop.LoopState = step_input.get_step_output('propose-schema').content
        response = await self.critic_agent.arun(state)
        feedback: str = response.content

        output_state = self.LoopState(
            file_samples=state.file_samples,
            user_goal=state.user_goal,
            proposed_schema=state.proposed_schema,
            critic_feedback=feedback
        )
        self.last_iteration_output_content = output_state # Last step in loop, so store output content for next iteration
        return StepOutput(content=output_state)

    def get_loop(self) -> Loop:
        """ returns the underlying loop - for adding loop to a workflow """
        return self.loop
    