from typing import List, TypedDict, Tuple

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
