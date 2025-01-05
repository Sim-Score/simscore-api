from pydantic import BaseModel
from typing import List, Dict, Optional

class IdeaInput(BaseModel):
    id: Optional[int | str] = None
    author_id: Optional[int | str] = None
    idea: str

class AdvancedFeatures(BaseModel):
    relationship_graph: bool = False
    pairwise_similarity_matrix: bool = False
    cluster_names: bool = False

class IdeaRequest(BaseModel):
    ideas: List[IdeaInput]
    advanced_features: Optional[AdvancedFeatures] = None
