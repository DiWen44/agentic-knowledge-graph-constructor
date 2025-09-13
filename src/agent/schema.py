from io import BytesIO
from typing import Annotated, TypedDict, List
from dataclasses import dataclass

from langgraph.graph.message import add_messages
import pandas as pd
from markitdown import MarkItDown


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


class AgentsState(TypedDict):
    """
    State object for the langGraph graph.
    """
    messages: Annotated[list, add_messages]
    csv_files: List[CSVFile]
    unstructured_files: List[UnstructuredFile]
