import asyncio
from flask import session
from schema import Message


USER_SENT_MESSAGE = asyncio.Event()

async def get_latest_user_message() -> Message:
    """
    Async function that waits until the user has sent a message, then returns the latest message.
    """
    await USER_SENT_MESSAGE.wait()
    msg = session['messages'][-1]  # Message is stored as basic dict in session
    USER_SENT_MESSAGE.clear()
    return Message(sender=msg['sender'], content=msg['content'])


def write_agent_message_to_session(content: str) -> None:
    """
    For agents/workflows to send messages.
    Writes a message with role 'agent' to the flask session messages list.
    """
    session['messages'].append(Message(sender='agent', content=content))
    session.modified = True
        
