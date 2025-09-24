from io import BytesIO
from typing_extensions import List
from dataclasses import dataclass
from pydantic import BaseModel, Field
import pandas as pd

@dataclass
class CSVFile():
    """ 
    A structured CSV file provided by the user.
    Attributes:
        name - filename, including file extension (i.e. .csv)
        content - The CSV file loaded as a pandas DataFrame
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
        file.seek(0) # Move file pointer to start of file
        content = pd.read_csv(file)
        return cls(name=name, content=content)

    def sample(self) -> List[str]:
        """
        Returns the first 11 lines of the csv file.
        This is useful for providing context to agents about the content of the file.
        Returns:
            list[str]: The first 11 lines of the csv file: The first line has the column headers, subsequent 10 lines have the data.
                Each line is a single comma-separated string.
        """
        columns = ",".join(self.content.columns.values.tolist())
        rows = self.content.iloc[:10].apply(lambda x: ",".join(x.astype(str)), axis=1).tolist()
        return [columns] + rows 


class EntityType(BaseModel):
    """ 
    A proposed entity (node) type in the knowledge graph. 
    """
    label: str = Field(description="Name/label of the type of the entity (e.g. PERSON, COMPANY, PRODUCT) as an all-caps string with underscores")
    fields: List[str] = Field(description="List of fields/attribute names that instances of this entity type can have (e.g. for PERSON, fields could be name, age, address), as a list of snake_case strings")


class RelationshipType(BaseModel):
    """ A proposed relationship (edge) type in the knowledge graph. """
    label: str = Field(description="Name/label of the type of the relationship (e.g. WORKS_AT, PURCHASED) as an all-caps string with underscores")
    source: str = Field(description="Name of source entity type")
    target: str = Field(description="Name of target entity type")


class StructuredSchema(BaseModel):
    """ 
    A schema for the structured part of the knowledge graph consisting of entity types and relationship types.
    """
    entity_types: List[EntityType] = Field(description="List of proposed entity types")
    relationship_types: List[RelationshipType] = Field(description="List of proposed relationship types")
    