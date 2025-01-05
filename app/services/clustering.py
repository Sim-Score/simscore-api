from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dataclasses import dataclass, asdict

from app.services.types import ClusterName, RankedIdea

async def summarize_clusters(ranked_ideas: List[RankedIdea]) -> List[ClusterName]:
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI()
    client.api_key = api_key

    # Group ideas by cluster
    clusters = {}
    for idea in ranked_ideas:
        if idea.cluster_id not in clusters:
            clusters[idea.cluster_id] = []
        clusters[idea.cluster_id].append(idea.idea)
    
    # First, prepare all clusters of ideas
    all_clusters = []
    for cluster, ideas in clusters.items():
        all_clusters.append(f"Cluster {cluster}:\n{'\n'.join(ideas)}")

    # Send all clusters to ChatGPT at once
    prompt = f"Create concise cluster names (max 3 words each) for the following clusters of ideas. Ensure each category is distinct from the others:\n\n{'\n\n'.join(all_clusters)}\n\nClusters:"

    class CategoryResponse(BaseModel):
      categories: List[ClusterName] = Field(
          default_factory=list,
          example=[
              {"id": 0, "name": "Example Cluster Name 1"},
              {"id": 1, "name": "Example Category 2"}
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
    print("Categories:", category_response)
    return category_response.categories