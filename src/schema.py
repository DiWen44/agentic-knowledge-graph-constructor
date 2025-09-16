from io import BytesIO
from dataclasses import dataclass
from typing import Literal, Dict
import pandas as pd
from markitdown import MarkItDown
from pydantic import BaseModel


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
    def from_bytesIO(cls, file: BytesIO) -> "CSVFile":
        """ Constructs from a BytesIO object, of which streamlit's UploadedFile is a subclass """
        return cls(name=file.name, content=pd.read_csv(file))


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
    def from_bytesIO(cls, file: BytesIO) -> "UnstructuredFile":
        """ Constructs from a BytesIO object, of which streamlit's UploadedFile is a subclass """
        md = MarkItDown()
        conversion = md.convert(file)
        return cls(name=file.name, doc_title=conversion.title, content=conversion.markdown)


@dataclass
class Message():
    """ 
    Represents a message sent by either the user or the top-level conversational agent
    (i.e. "the ai") in the streamlit application
    """
    role: Literal["human", "ai"]
    content: str

    def to_dict(self) -> Dict[str, str]:
        """ Returns the message as a dictionary that can be passed to langgraph graph invocations"""
        return {
            'role': self.role,
            'content': self.content
        }
    

class UserGoal(BaseModel):
    """ 
    A user goal ascertained by the user intent agent in the top-level knowledge graph workflow. 
    Attributes:
        kind_of_graph - a few words stating the purpose of the graph (e.g. USA freight logistics)
        description - a short description of the intention of the graph e.g. "A dynamic routing and delivery system for cargo."
    """
    kind_of_graph: str
    description: str
