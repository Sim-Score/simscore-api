import asyncio
import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel, Field
import json

router = APIRouter()

@router.post("/validate")
async def validate_idea(request: dict):
    print(request)

    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI()
    client.api_key = api_key

    thread = client.beta.threads.create()
    print("Created thread: ", thread.id)

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=request["idea"],
    )

    class CriteriaRating(BaseModel):
      class Ratings(BaseModel):
        class Rating(BaseModel):
          quality: float = Field(description="The rating for how well the statement meets the criteria")
          message: str = Field(description="Short explanation to the rating")

        singlePointFocus: Rating = Field(default=None)
        sentimentError: Rating = Field(default=None)

      ratings: Ratings = Field(default_factory=Ratings)

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id="asst_Y9q7vWLJJUG24uWwnQNznZia",
        additional_instructions="Reply with following JSON format: rating: { singlePointFocus: IndividualRating, sentiment: IndividualRating } with  IndividualRating = { quality: [number between 0-9], message: string }",
        response_format={"type": "json_object"},
    )

    while run.status in ['queued', 'in_progress']:
        print("Waiting for OpenAI to finish processing")
        await asyncio.sleep(0.1)  # Wait for 100ms
    
    if run.status == 'completed':
      result = client.beta.threads.messages.list(
          thread_id=thread.id
      )
      result_json = json.dumps(json.loads(result.data[0].content[0].text.value), indent=2)
      print("Result: ", result_json)
      return JSONResponse(content=result_json)

    raise Exception("OpenAI finished with: ", run.status)    
