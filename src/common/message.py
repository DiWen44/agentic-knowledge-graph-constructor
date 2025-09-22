from flask import session
from typing_extensions import Literal, TypedDict


class Message(TypedDict):
    """ 
    Represents a message sent by either the user, an agent in the system, or a system notification.
    """
    sender: Literal['user', 'agent', 'system']
    content: str


async def get_latest_user_message() -> Message:
    """
    Async function that waits until the user has sent a message, then returns the latest message.
    """
    """
    await USER_SENT_MESSAGE.wait()
    msg = session['messages'][-1]  # Message is stored as basic dict in session
    """

    # PLACEHOLDER: GET USER INPUT FROM COMMAND LINE
    # TODO: Replace with actual async message retrieval from Flask session
    msg = input("> ")
    return Message(sender='user', content=msg)


def write_agent_message_to_session(msg: str) -> None:
    """
    For agents/workflows to send messages.
    Writes a message with sender type 'agent' to the flask session messages list.
    """
    session['messages'].append(Message(sender='agent', content=msg))
        