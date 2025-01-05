from typing import List, Optional, TypedDict, Tuple

from pydantic import BaseModel

class KMeansData(TypedDict):
    data: List[List[float]]
    centers: List[List[float]]
    cluster: List[int]

class PlotData(TypedDict):
    scatter_points: List[List[float]]
    marker_sizes: List[float]
    ideas: List[str]
    pairwise_similarity: List[List[float]]
    kmeans_data: KMeansData

class Results(TypedDict):
    ideas: List[str]
    similarity: List[float]
    distance: List[float]

CentroidAnalysisResult = Tuple[Results, PlotData]

class ClusterName(BaseModel):
    id: int
    name: str

class RankedIdea(BaseModel):
    id: int | str
    author_id: Optional[int | str] = None
    idea: str
    similarity_score: float
    cluster_id: int