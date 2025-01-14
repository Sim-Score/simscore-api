from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from openai import OpenAI
import os
from dataclasses import dataclass, asdict

from app.core.config import settings
from app.services.types import ClusterName, RankedIdea
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter


async def summarize_clusters(ranked_ideas: List[RankedIdea]) -> List[ClusterName]:
    
    print("Summarizing clusters")
    embeddings = OpenAIEmbeddings()
    vectordb = Chroma(embedding_function=embeddings)
    
    # Add all ideas at once with metadata
    texts = [idea.idea for idea in ranked_ideas]
    metadatas = [{"cluster_id": idea.cluster_id} for idea in ranked_ideas]
    
    print("Adding ideas to vectordb")
    vectordb.add_texts(texts, metadatas=metadatas)
    
    # Query per cluster using metadata filtering
    relevant_chunks = {}
    unique_clusters = set(idea.cluster_id for idea in ranked_ideas)
    
    for cluster_id in unique_clusters:
        print(f"Processing cluster {cluster_id}")
        results = vectordb.similarity_search(
            "What are the key themes in this cluster?",
            k=5,
            filter={"cluster_id": cluster_id}
        )
        print("\nRelevant chunks:\n\n", results)
        relevant_chunks[cluster_id] = [doc.page_content for doc in results]    
    
    # Generate category names
    prompt = f"Create a concise category name (max 3 words) for each cluster of ideas based on these representative ideas:\n" + \
             "\n".join([f"Cluster {cluster_id}: {chunks}" for cluster_id, chunks in relevant_chunks.items()])    
    print("Prompt for AI: \n", prompt)
    return await get_category_names(prompt)
    
async def get_category_names(prompt: str) -> List[ClusterName]:
    api_key = settings.OPENAI_API_KEY
    client = OpenAI(api_key = api_key)

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
            {"role": "system", "content": "You are a helpful assistant that creates concise and descriptive category titles for clusters of ideas. Ensure each category is distinct from others."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500,
        response_format=CategoryResponse,
    )
    
    return response.choices[0].message.parsed.categories
