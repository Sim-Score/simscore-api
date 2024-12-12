from pydantic import BaseModel
from typing import List, Dict, Optional

class IdeaInput(BaseModel):
    id: int
    idea: str

class AdvancedFeatures(BaseModel):
    relationship_graph: bool = False
    pairwise_similarity_matrix: bool = False

class IdeaRequest(BaseModel):
    ideas: List[IdeaInput]
    advanced_features: Optional[AdvancedFeatures] = None
