from pydantic import BaseModel
from typing import List, Dict, Optional

from app.services.types import ClusterName, RankedIdea

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
    cluster_names: Optional[List[ClusterName]] = None
