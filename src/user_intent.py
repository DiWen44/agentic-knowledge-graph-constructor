from typing import List
from pydantic import BaseModel, Field
from textwrap import dedent
import os
from agno.workflow import  Loop, Step, StepInput, StepOutput
from agno.agent import Agent
from agno.models.google.gemini import Gemini

from schema import UserGoal, Message
from message_handling import get_latest_user_message, write_agent_message_to_session


class UserIntentLoop():
    """
    Wrapper class for a user intent elicitation loop within a workflow.
    Loop runs until the user has approved a proposed user goal, or max iterations reached.
    Consists of 2 steps:
        1. get-user-input: retrieves user input from the flask app - this is either the initial user prompt to the workflow, or feedback on a proposed goal
        2. propose-user-goal: prompts a "user intent" agent to generate a proposed UserGoal based on the user's input, 

    If the user agrees with the goal proposal by inputting some message of approval, the agent in propose-user-goal marks the proposed goal as approved, 
    and the approved user goal is added to the top-level knowledge workflow's session state.
    
    Attributes:
        loop - the underlying agno workflow Loop object
        agent - the user intent agent used in the propose-user-goal step
        last_iteration_output_content - stores the output content of the final step of the last iteration, so as to have state persist across iterations.
            NOTE: Agno does not pass the output of the last step as an input to the first step of the next iteration, so we have to do this manually by capturing it here.
    """

    loop: Loop
    agent: Agent
    last_iteration_output_content: "UserIntentLoop.LoopState | None" = None  


    class AgentOutputSchema(BaseModel):
        """
        Schema for user intent agent's output

        Args:
            llm_message - Natural language text that the agent's LLM generates as part of it's response
            proposed_goal - the proposed user goal the agent has come up with
            goal_approved - if proposed goal has been approved by the user
        """
        llm_message: str = Field(description="Natural language text that the LLM generates as part of it's response")
        proposed_goal: UserGoal | None = Field(default=None, description="The proposed user goal")
        goal_approved: bool = Field(default=False, description="Whether the proposed goal has been approved by the user")


    class LoopState(BaseModel):
        """
        A state object that gets passed as input & output content of the steps in the loop
        This is internal to the user intent loop and thus separate from the overall workflow session state.
    
        Attributes:
            chat_history - The chat history so far between the user and the user intent agent, as a list of messages.
            proposed_goal - The proposed user goal the user intent agent has come up with
            goal_approved - if proposed goal has been approved by the user
        """
        chat_history: List[Message] = Field(default_factory=list, description="The chat history so far")
        proposed_goal: UserGoal | None = Field(default=None, description="The proposed user goal")
        goal_approved: bool = Field(default=False, description="Whether the proposed goal has been approved by the user")


    def __init__(self, max_iterations: int = 10) -> None:


        self.agent = Agent(
            name="user-intent-agent",
            model=Gemini(id="gemini-2.5-flash-lite"),
            input_schema=self.LoopState,
            output_schema=self.AgentOutputSchema,
            instructions=dedent("""
            You are an expert at knowledge graph use cases. Your objective is to ascertain the user's goal for the knowledge graph they wish to create.

            A user goal has 2 components:  
                - kind_of_graph: at most 3 words stating the graph's purpose, for example "social network" or "USA freight logistics"  
                - description: at most 3 short sentences about the intention of the graph, for example "A dynamic routing and delivery system for cargo." or "Analysis of product dependencies and supplier alternatives

            Ascertain the user's percieved goal from their previous messages (in the chat history) and the currently assumed user goal (if there is one), 
            then present the new perceived user goal to the user for confirmation, asking clarifying questions if you need to.
            If the user agrees with the proposed user goal: set goal_approved to True in your output
            If you can't derive a user goal from the user's message, leave the user goal as None. Do not allow the user to approve a user goal with value None.
            """),
            markdown=True,
            debug_mode=True
        )

        self.loop = Loop(
            name='user-intent-loop',
            steps=[
                Step(name='get-user-input', executor=self.get_user_input),
                Step(name='propose-user-goal', executor=self.propose_user_goal)
            ],
            end_condition= ( lambda step_outputs: step_outputs[-1].content.goal_approved ), # End loop if goal is marked approved
            max_iterations=max_iterations
        )


    async def get_user_input(self, step_input: StepInput) -> StepOutput:
        """
        LOOP STEP 1: retrieving user input from the flask app. 
        If this is the the loop's first iteration, we just get the user's initial input message and pass it to the next step.
        If not, we wait for the user to send a message in the flask app, and pass that on.
        """

        state = self.last_iteration_output_content # First step in loop, so input is output of last step of last iteration
        if state is None: # If loop's first iteration - pass initial user input straight to next step
            return StepOutput(
                content=self.LoopState(
                    chat_history=[Message( # Add initial user message as start of chat history
                        sender='user', 
                        content=step_input.input 
                    )]
                )
            )

        user_msg: Message = await get_latest_user_message()
        return StepOutput(
            content=self.LoopState(
                chat_history=state.chat_history+[user_msg], # Add latest user message to chat history
                proposed_goal=state.proposed_goal, 
            )
        )


    async def propose_user_goal(self, step_input: StepInput, session_state) -> StepOutput:
        """
        LOOP STEP 2: prompts a "user intent" agent to generate a proposed UserGoal from a user's input, 
        which is then outputted to the flask app as an agent message, along with any natural language text the llm generates.

        The user's input is in the output of the get-user-input step; the agent will try to create a new goal, 
        or refine the previously proposed goal if there was one, based on the user's feedback.

        If the user agrees with the goal proposal, the approved user goal is added to the workflow's session state.
        """

        state : "UserIntentLoop.LoopState" = step_input.get_step_output('get-user-input').content
        response : "UserIntentLoop.AgentOutputSchema" = await self.agent.arun(state)

        # Write agent's output - deterministically format proposed user goal
        agent_message = response.content.llm_message
        if response.content.proposed_goal:
            agent_message += "\n\n" + f"""
            **{"Finalized" if response.content.goal_approved else "Proposed"} User Goal: **\n
            \tkind of graph: {response.content.proposed_goal.kind_of_graph}\n
            \tdescription: {response.content.proposed_goal.description}
            """
        write_agent_message_to_session(agent_message)

        # If goal approved, Update workflow session state with approved goal
        if response.content.goal_approved:
            session_state["user_goal"] = UserGoal(kind_of_graph=response.content.proposed_goal.kind_of_graph, description=response.content.proposed_goal.description)

        # This is last step in iteration, so capture step output for next iteration
        output = self.LoopState(
            chat_history=state.chat_history + [Message(sender='agent', content=agent_message)],
            proposed_goal=response.content.proposed_goal,
            goal_approved=response.content.goal_approved
        )
        self.last_iteration_output_content = output  

        return StepOutput(content=output)
    

    def get_loop(self) -> Loop:
        """ returns the underlying loop - for adding loop to a workflow """
        return self.loop
