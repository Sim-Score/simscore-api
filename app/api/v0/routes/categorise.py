from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dataclasses import dataclass, asdict

router = APIRouter()

@dataclass
class EvaluatedIdea:
  id: Optional[str]
  idea: str
  similarity: float
  distance: float
  cluster: int

@router.post("/summarize_clusters")
async def summarize_clusters(evaluated_ideas: List[EvaluatedIdea]):
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI()
    client.api_key = api_key

    # Group ideas by cluster
    clusters = {}
    for idea in evaluated_ideas:
        if idea.cluster not in clusters:
            clusters[idea.cluster] = []
        clusters[idea.cluster].append(idea.idea)
    
    # First, prepare all clusters of ideas
    all_clusters = []
    for cluster, ideas in clusters.items():
        all_clusters.append(f"Cluster {cluster}:\n{'\n'.join(ideas)}")

    # Send all clusters to ChatGPT at once
    prompt = f"Create concise category names (max 3 words each) for the following clusters of ideas. Ensure each category is distinct from the others:\n\n{'\n\n'.join(all_clusters)}\n\nCategories:"

    class CategoryItem(BaseModel):
      cluster: int
      category_name: str

    class CategoryResponse(BaseModel):
      categories: List[CategoryItem] = Field(
          default_factory=list,
          example=[
              {"cluster": 0, "category_name": "Example Category 1"},
              {"cluster": 1, "category_name": "Example Category 2"}
          ]
      )

    response = client.beta.chat.completions.parse(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates concise and descriptive category titles for clusters of ideas. Ensure each category is distinct from the others."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        response_format=CategoryResponse,
    )

    # Extract the generated titles from the response
    category_response = response.choices[0].message.parsed

    # Make sure this list is ordered by cluster
    cats = category_response.categories
    cats.sort(key=lambda catItem: catItem.cluster)
    print("Sorted Categories:", cats)
    summaries = [cat.category_name for cat in cats]
    return summaries
