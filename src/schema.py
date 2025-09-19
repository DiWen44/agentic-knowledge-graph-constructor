from io import BytesIO
from dataclasses import dataclass
from typing_extensions import Literal, TypedDict
import pandas as pd
from markitdown import MarkItDown
from pydantic import BaseModel, Field


@dataclass
class CSVFile():
    """
    A structured CSV file provided by the user - The content is stored as a pandas dataframe.

    ATTRIBUTES:
        name: filename, including file extension (i.e. ".csv")
        content: CSV contents as a pandas dataframe
    """
    name: str
    content: pd.DataFrame

    @classmethod
    def from_bytesIO(cls, name: str, file: BytesIO) -> "CSVFile":
        """
        Constructs from a bytesIO stream object 
        Args:
            name: name of the file, including extension
            file: a bytesIO object
        """
        return cls(name=name, content=pd.read_csv(file))


@dataclass
class UnstructuredFile():
    """
    An unstructured text-based file provided by the user.
    Can be of formats "txt", "pdf", "md", "docx", "html".
    For later convenience, the file content is converted to markdown here.

    ATTRIBUTES:
        name: filename, including file extension
        doc_title: Title of the document ascertained from text, if any
        content: Markdown formatted doc content
    """
    name: str
    doc_title: str
    content: str

    @classmethod
    def from_bytesIO(cls, name: str, file: BytesIO) -> "UnstructuredFile":
        """
        Constructs from a bytesIO stream object 
        Args:
            name: name of the file, including extension
            file: a bytesIO object
        """
        md = MarkItDown()
        conversion = md.convert(file)
        return cls(name=name, doc_title=conversion.title, content=conversion.markdown)


class Message(TypedDict):
    """ 
    Represents a message sent by either the user or the top-level conversational agent in the flask app.
    """
    sender: Literal['user', 'agent']
    content: str
    

class UserGoal(BaseModel):
    """ 
    A user goal ascertained by the user intent agent in the top-level knowledge graph workflow. 
    Attributes:
        kind_of_graph - a few words stating the purpose of the graph (e.g. USA freight logistics)
        description - a short description of the intention of the graph e.g. "A dynamic routing and delivery system for cargo."
    """
    kind_of_graph: str = Field(description="A few words stating the purpose of the graph")
    description: str = Field(description="A short description of the intention of the graph")
