from io import BytesIO
from typing_extensions import Literal, TypedDict, List
from markitdown import MarkItDown
from dataclasses import dataclass
from pydantic import BaseModel, Field


@dataclass
class CSVFile():
    """ A structured CSV file provided by the user """
    name: str = Field(description="Filename, including file extension (i.e. .csv)")
    column_names: str = Field(description="The column names of the CSV file i.e. the first row of the file, as a single comma-separated string")
    rows: List[str] = Field(description="The rows of the CSV file, each row as a single comma-separated string of cell values")

    @classmethod
    def from_bytesIO(cls, name: str, file: BytesIO) -> "CSVFile":
        """
        Constructs from a bytesIO stream object 
        Args:
            name: name of the file, including extension
            file: a bytesIO object
        """
        content = file.readlines()
        column_names = content[0].decode('utf-8').strip()
        rows = [line.decode('utf-8').strip() for line in content[1:]]
        return cls(name=name, column_names=column_names, rows=rows)


@dataclass
class UnstructuredFile():
    """
    An unstructured text-based file provided by the user.
    Can be of formats "txt", "pdf", "md", "docx", "html".
    For later convenience, the file content is converted to markdown here.
    """
    name: str = Field(description="Filename, including file extension (e.g. .txt, .pdf, .md, .docx, .html)")
    doc_title: str | None = Field(default=None,description="Title of the document ascertained from text, if any")
    content: str = Field(description="Markdown formatted doc content")

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
    Represents a message sent by either the user, an agent in the system, or a system notification.
    """
    sender: Literal['user', 'agent', 'system']
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
