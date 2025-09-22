from io import BytesIO
from markitdown import MarkItDown
from dataclasses import dataclass


@dataclass
class UnstructuredFile():
    """
    An unstructured text-based file provided by the user. Can be of formats "txt", "pdf", "md", "docx", "html".
    For later convenience, the file content is converted to markdown here.
    Attributes:
        name - filename, including file extension (e.g. .txt, .pdf, .md, .docx, .html)
        doc_title - Title of the document ascertained from text, if any
        content - Markdown formatted doc content
    """
    name: str
    doc_title: str | None
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
