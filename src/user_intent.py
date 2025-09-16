from pydantic import BaseModel
from textwrap import dedent
import os
from agno.workflow import StepInput, StepOutput
from agno.agent import Agent
from agno.models.google.gemini import Gemini

from schema import UserGoal, Message
from streamlit_utils import write_to_streamlit, get_latest_user_message


class UserIntentAgentOutputSchema(BaseModel):
    """
    Schema for user intent agent's output

    Args:
        llm_message - Natural language text that the agent's LLM generates as part of it's response
        proposed_goal - the proposed user goal the agent has come up with
        goal_approved - if proposed goal has been approved by the user
    """
    llm_message: str
    proposed_goal: UserGoal | None = None
    goal_approved: bool = False


class UserIntentLoopState(BaseModel):
    """
    A state object that gets passed as input & output content of the steps in the loop

    Attributes:
        proposed_goal - The proposed user goal the user intent agent has come up with
        user_input - At first the initial user prompt to the whole workflow, then user feedback on the proposed goal when the agent generates a goal proposal
        goal_approved - if proposed goal has been approved by the user
    """
    proposed_goal: UserGoal | None = None
    user_input: str
    goal_approved: bool = False


async def propose_user_goal(step_input: StepInput, session_state) -> StepOutput:
    """
    User intent loop step 1: prompts a "user intent" agent to generate a proposed UserGoal from a user's input, 
    which is then outputted to the streamlit app as an agent message, along with any natural language text the llm generates.

    If this is the first run of the loop, the original knowledge graph workflow input is treated as the user's input, and the agent attempts to come up with an initial goal proposal.
    Otherwise, the user's input is in the output of the get-user-input step; the agent will try to refine the previously proposed goal based on the user's feedback.

    If the user agrees with the goal proposal, the approved user goal is added to the workflow's session state.
    """

    agent = Agent(
        name="user-intent-agent",
        model=Gemini(id="gemini-2.5-flash-lite", api_key=os.getenv("GOOGLE_API_KEY")),
        input_schema=UserIntentLoopState,
        output_schema=UserIntentAgentOutputSchema,
        instructions=dedent("""
        You are an expert at knowledge graph use cases. Your objective is to ascertain the user's goal for the knowledge graph they wish to create.

        A user goal has 2 components:  
            - kind_of_graph: at most 3 words stating the graph's purpose, for example "social network" or "USA freight logistics"  
            - description: at most 3 short sentences about the intention of the graph, for example "A dynamic routing and delivery system for cargo." or "Analysis of product dependencies and supplier alternatives

        Ascertain the user's percieved goal from their input & previous messages and the currently assumed user goal (if there is one), then present the new perceived user goal to the user for confirmation,
        asking clarifying questions if you need to.
        If the user agrees with the proposed user goal: set goal_approved to True in your output
        If you can't derive a user goal from the user's message, leave the user goal as None. Do not allow the user to approve a user goal with value None.
        """),
        markdown=True,
        debug_mode=True
    )

    # If this is the first step, no previous step content, so pass the user's initial input to the agent (inside a loop state object)
    # Otherwise, pass the loop state outputted by the previous step
    if step_input.previous_step_outputs:
        state: UserIntentLoopState = step_input.get_step_output('get-user-input').content
        llm_input = state
    else:
        llm_input = UserIntentLoopState(user_input=step_input.input)
    response: UserIntentAgentOutputSchema = await agent.arun(llm_input)

    
    # Write agent's output to streamlit - deterministically format proposed user goal
    streamlit_message = response.content.llm_message
    if response.content.proposed_goal:
        streamlit_message += "\n\n" + f"""
        **{"Finalized" if response.content.goal_approved else "Proposed"} User Goal: **\n
        \tkind of graph: {response.content.proposed_goal.kind_of_graph}\n
        \tdescription: {response.content.proposed_goal.description}
        """
    write_to_streamlit(streamlit_message)

    # Update workflow session state with approved goal
    if response.content.goal_approved:
        session_state["user_goal"] = UserGoal(kind_of_graph=response.content.proposed_goal.kind_of_graph, description=response.content.proposed_goal.description)

    return StepOutput(
        content=UserIntentLoopState(
            proposed_goal=response.content.proposed_goal, 
            user_input="", # Clear previous user input
            goal_approved=response.content.goal_approved
        )
    )


async def get_user_input(step_input: StepInput) -> StepOutput:
    """
    User intent loop step 2: retrieving user input from streamlit.
    """

    state : UserIntentLoopState = step_input.get_step_output('propose-user-goal').content

    # Skip over this step & relay previous step's state if agent approved the user goal,
    # as loop will terminate after this step
    if state.goal_approved:
        return StepOutput(content=state)
    
    user_input: Message = await get_latest_user_message()
    return StepOutput(
        content=UserIntentLoopState(
            proposed_goal=state.proposed_goal, 
            user_input=user_input.content,
            goal_approved=False
        )
    )
    




