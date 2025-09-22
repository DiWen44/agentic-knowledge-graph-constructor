from io import BytesIO
from typing_extensions import List
from dataclasses import dataclass
from pydantic import BaseModel, Field

@dataclass
class CSVFile():
    """ 
    A structured CSV file provided by the user.
    Attributes:
        name - filename, including file extension (i.e. .csv)
        column_names - the column names of the CSV file i.e. the first row of the file, as a single comma-separated string
        rows - the rows of the CSV file, each row as a single comma-separated string of cell values
    """
    name: str
    column_names: str
    rows: List[str]

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

    def sample(self) -> List[str]:
        """
        Returns the first 11 lines of the csv file.
        This is useful for providing context to agents about the content of the file.
        Returns:
            list[str]: The first 11 lines of the csv file: The first line has the column headers, subsequent 10 lines have the data.
                Each line is a single comma-separated string.
        """
        return [self.column_names] + self.rows[:10]
    

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
    