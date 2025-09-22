from pydantic import BaseModel, Field


class UserGoal(BaseModel):
    """ 
    A user goal ascertained by the user intent agent in the top-level knowledge graph workflow. 
    Attributes:
        kind_of_graph - a few words stating the purpose of the graph (e.g. USA freight logistics)
        description - a short description of the intention of the graph e.g. "A dynamic routing and delivery system for cargo."
    """
    kind_of_graph: str = Field(description="A few words stating the purpose of the graph")
    description: str = Field(description="A short description of the intention of the graph")
