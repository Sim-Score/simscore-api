from pydantic import BaseModel
from typing import List, Dict, Optional

class RankedIdea(BaseModel):
    id: int | str
    author_id: Optional[int | str] = None
    idea: str
    similarity_score: float
    cluster_id: int
    cluster_name: str

class Coordinates(BaseModel):
  x: float
  y: float  
  
class GraphNode(BaseModel):
  id: int | str
  coordinates: Coordinates
  
class GraphEdge(BaseModel):
    from_id: int | str
    to_id: int | str
    similarity: float

class RelationshipGraph(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]

class AnalysisResponse(BaseModel):
    ranked_ideas: List[RankedIdea]
    relationship_graph: Optional[RelationshipGraph] = None
    pairwise_similarity_matrix: Optional[List[List[float]]] = None
