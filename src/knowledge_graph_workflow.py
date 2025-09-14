from typing import TypedDict, List, Annotated
from schema import CSVFile, UnstructuredFile, Message
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.runtime import get_runtime


class State(TypedDict):
    """
    State object schema for the langGraph graph.
    """
    messages: Annotated[list, add_messages]


class Context(TypedDict):
    """
    Context object schema for the langGraph graph. 
    Holds persistent immutable static context data 
    """
    csv_files: List[CSVFile]
    unstructured_files: List[UnstructuredFile]


def output_context(state: State):
    ctx = get_runtime(Context).context
    print(ctx['csv_files'])


class KnowledgeGraphCreationWorkflow():
    """
    Wrapper class for the top-level langgraph workflow.
    """

    context: Context
    graph: StateGraph

    def __init__(self, 
        csv_files: List[CSVFile], 
        unstructured_files: List[UnstructuredFile]
    ) -> None:
        
        self.graph = StateGraph(state_schema=State, context_schema=Context)
        self.context = Context(csv_files=csv_files, unstructured_files=unstructured_files)

        self.graph.add_node("output_state", output_context)
        self.graph.add_edge(START, "output_state")
        self.graph.add_edge("output_state", END)
    

    def run(self, message: Message) -> None:
        """ Invoke the graph on an initial user-provided message """
        compiled_graph = self.graph.compile()
        compiled_graph.invoke({"messages": [message.to_dict()]}, context=self.context)

    
    


    
