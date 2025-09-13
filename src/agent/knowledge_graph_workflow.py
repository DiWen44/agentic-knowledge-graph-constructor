from langgraph.graph import StateGraph, START, END
from .schema import AgentsState

graph_builder = StateGraph(AgentsState)
graph_builder.add_node("get_files", get_files)
graph_builder.add_edge(START, "get-files")
graph_builder.add_edge("get-files", END)


"""
graph_builder.add_node("get_files", get_files)
graph_builder.add_node("structured-handler", handle_structured_data)
graph_builder.add_node("unstructured-handler", handle_unstructured_data)
graph_builder.add_edge(START, "get-files")
graph_builder.add_edge("get-files", "structured-handler")
graph_builder.add_edge("structured-handler", "unstructured-handler")
graph_builder.add_edge("unstructured-handler", END)
"""
