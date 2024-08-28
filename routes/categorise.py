from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from openai import OpenAI
import os

router = APIRouter()

class EvaluatedIdea (BaseModel):
  idea: str
  similarity: float
  distance: float
  cluster: int

@router.post("/summarize_clusters")
async def summarize_clusters(evaluated_ideas: List[EvaluatedIdea]):
    print("Received ideas for evaluation:", evaluated_ideas)
    
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI()
    client.api_key = api_key


    # Group ideas by cluster
    clusters = {}
    for idea in evaluated_ideas:
        if idea.cluster not in clusters:
            clusters[idea.cluster] = []
        clusters[idea.cluster].append(idea.idea)
    
    #Send each cluster to ChatGPT and get summaries
    summaries = {}
    for cluster, ideas in clusters.items():
      # Create a prompt for ChatGPT to generate a title for the cluster
      prompt = f"Create a concise category name (max 3 words) for the following cluster of ideas:\n\n{'\n '.join(ideas)}\n\nCategory:"

      # Call the ChatGPT API to generate a title
      response = client.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
              {"role": "system", "content": "You are a helpful assistant that creates concise and descriptive category titles for clusters of ideas."},
              {"role": "user", "content": prompt}
          ],
          max_tokens=20
      )

      # Extract the generated title from the response
      title = response.choices[0].message.content.strip()

      # Store the title in the summaries dictionary
      summaries[cluster] = title    
    return summaries
