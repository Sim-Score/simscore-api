from pydantic import BaseModel
from typing import List, Dict, Optional

class RankedIdea(BaseModel):
    id: int
    idea: str
    similarity_score: float
    cluster_id: int

class GraphNode(BaseModel):
    id: int
    label: str

class GraphEdge(BaseModel):
    from_id: int
    to: int
    weight: float

class RelationshipGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class AnalysisResponse(BaseModel):
    ranked_ideas: List[RankedIdea]
    relationship_graph: Optional[RelationshipGraph]
    pairwise_similarity_matrix: Optional[List[List[float]]]
