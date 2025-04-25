from pydantic import BaseModel, BeforeValidator, Field
from typing import Annotated, List, Dict, Optional, Union, Any

# Define a validator function to convert any idea value to string
def ensure_string(v: Any) -> str:
    if v is None:
        return ""
    return str(v)

class IdeaInput(BaseModel):
    id: Optional[int | str] = None
    author_id: Optional[int | str] = None
    idea: Annotated[str, BeforeValidator(ensure_string)]

class AdvancedFeatures(BaseModel):
    relationship_graph: bool = False
    pairwise_similarity_matrix: bool = False
    cluster_names: bool = False

class IdeaRequest(BaseModel):
    ideas: List[IdeaInput]
    advanced_features: Optional[AdvancedFeatures] = None
