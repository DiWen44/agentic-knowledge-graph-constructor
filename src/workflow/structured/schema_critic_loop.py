from typing import List, Any
from pydantic import BaseModel, Field
from textwrap import dedent
from agno.workflow import  Loop, Step, StepInput, StepOutput
from agno.agent import Agent
from agno.models.google.gemini import Gemini

from src.common.schema import CSVFile, UserGoal


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


    class SchemaProposal(BaseModel):
        """
        Schema for proposal agent's output

        Args:
            entity_types - the proposed list of entity types the agent has come up with
            relationship_types - the proposed list of relationship types the agent has come up with
        """
        entity_types: List[str] = Field(default_factory=list, description="The proposed list of entity types the agent has come up with")
        relationship_types: List[str] = Field(default_factory=list, description="The proposed list of relationship types the agent has come up with")

    
    class LoopState(BaseModel):
        """
        A state object that gets passed as input & output content of the steps in the loop
        This is internal to the schema proposal loop and thus separate from the overall workflow session state.

        Attributes:
            filenames - The names of the provided CSV files
            entity_types - The proposed list of entity types the schema proposal agent has come up with
            relationship_types - The proposed list of relationship types the schema proposal agent has come up with
            critic_feedback - Feedback from the critic agent
        """
        filenames: List[str] = Field(default_factory=list, description="The names of the provided CSV files")
        entity_types: List[str] = Field(default_factory=list, description="The proposed list of entity types the agent has come up with")
        relationship_types: List[str] = Field(default_factory=list, description="The proposed list of relationship types the agent has come up with")
        critic_feedback: str = Field(default="", description="Feedback from the critic agent")


    def __init__(self, 
        files: List[CSVFile],
        user_goal: UserGoal,
        max_iterations: int = 10) -> None:

        self.proposal_agent = Agent(
            name="proposal-agent",
            model=Gemini(id="gemini-2.5-flash-lite"),
            input_schema=self.LoopState,
            output_schema=self.SchemaProposal,
            instructions=dedent(f"""
            You are an expert at knowledge graph schema design. Your task is to propose a schema for a knowledge graph, based on the content of provided CSV file documents.
                                
            A knowledge graph schema consists of 2 lists:
            - a list of entity types (nodes) (e.g. Person, Company, Product)
            - a list of relationship types (edges). (e.g. WORKS_AT, PURCHASED)

            Note that you are not being asked to extract instances of entities or relationships, just the high-level entity types and relationship types.

            The user's objective is to construct a graph that is defined as follows:
                Kind of graph: {user_goal.kind_of_graph}
                Description: {user_goal.description}
            Based on this, as well as:
            - The provided CSV files
            - feedback from a critic agent (if any) on the proposed entity types and relationship types.
            produce a schema that would be relevant to this graph.

            Use the peek_file tool to inspect a part of the content of the provided CSV files, to help you determine appropriate entity types and relationship types.

            # SCHEMA RULES & GUIDANCE
            Every file in the approved files list will become either a node or a relationship. Determining whether a file likely represents a node or a relationship is based on a hint from the filename
            (is it a single thing or two things) and the identifiers found within the file. Because unique identifiers are so important for determining the structure of the graph, 
            always verify the uniqueness of suspected unique identifiers using the 'search_file' tool.

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
            tools=[self.peek_file],
            debug_mode=True
        )

        self.critic_agent = Agent(
            name="critic-agent",
            model=Gemini(id="gemini-2.5-flash-lite"),
            input_schema=self.LoopState,
            instructions=dedent(f"""
            You are an expert at knowledge graph schema design. Your task is to critique the proposed schema put forth by the proposal agent.
            Based on the proposed entity types and relationship types, provide feedback on their relevance to the user's objective and their completeness.
                                
            The user's objective is to construct a graph that is defined as follows: 
                Kind of graph: {user_goal.kind_of_graph}
                Description: {user_goal.description}

            Use the peek_file tool to inspect a part of the content of the provided CSV files, to help you determine whether the proposed entity types and relationship types are appropriate.

            If you believe the proposed schema is (sufficiently) appropriate and complete, respond with only the word "APPROVED".
            """),
            tools=[self.peek_file],
            debug_mode=True
        )

        self.loop = Loop(
            name='schema-critic-loop',
            max_iterations=max_iterations,
            steps = [
                Step(name='propose-schema', agent=self.proposal_agent),
                Step(name='critique-schema', agent=self.critic_agent)
            ],
            end_condition=( lambda step_outputs: step_outputs[-1].critic_feedback == "APPROVED" ), # End loop if critic agent approves
        )


    async def propose_schema(self, session_state, step_input: StepInput) -> StepOutput:
        """ LOOP STEP 1: Proposes a schema based on the provided CSV files."""

        if self.last_iteration_output_content is None: # If this is the first iteration of loop - give empty state
            state = SchemaCriticLoop.LoopState(
                filenames=[filename for filename in session_state['files'].keys()], # Get filenames from workflow session state
                critic_feedback=""
            )
        else:
            state: SchemaCriticLoop.LoopState = self.last_iteration_output_content # First step in loop, so input is output of last step of previous iteration

        proposal: SchemaCriticLoop.SchemaProposal = await self.proposal_agent.arun(state).content
        return StepOutput(
            content=self.LoopState(
                filenames=state.filenames,
                entity_types=proposal.entity_types,
                relationship_types=proposal.relationship_types,
                critic_feedback="" # Reset critic feedback 
            )
        )
    

    async def critique_schema(self, step_input: StepInput) -> StepOutput:
        """ LOOP STEP 2: Critiques the proposed schema by the proposal agent."""
        state: SchemaCriticLoop.LoopState = step_input.content
        feedback: str = await self.critic_agent.arun(state)

        output = self.LoopState(
            filenames=state.filenames,
            entity_types=state.entity_types,
            relationship_types=state.relationship_types,
            critic_feedback=feedback
        )
        self.last_iteration_output_content = output # Last step in loop, so store output content for next iteration
        return StepOutput(content=output)
    

    def peek_file(self, session_state, filename: str) -> Any:
        """
        Tool: Returns the first 10 lines of a csv file

        Args:
            filename (str): The name of the csv file to peek at.

        Returns:
            If successful:
                list[str]: The first 11 lines of the csv file: The first line has the column headers, subsequent 10 lines have the data
            If error:
                str: Error message
        """

        # Get CSV file from workflow session state
        try:
            csv_file: CSVFile = session_state['files'][filename]
        except KeyError:
            return f"ERROR: No file with name {filename} found."

        column_names = csv_file.column_names
        rows = csv_file.rows
        return [', '.join(column_names)] + [', '.join(row) for row in rows[:11]]


    def get_loop(self) -> Loop:
        """ returns the underlying loop - for adding loop to a workflow """
        return self.loop