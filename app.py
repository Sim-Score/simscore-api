import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from Analyzer import CountVectorizer, Analyzer

app = FastAPI()

ACCESS_CONTROL_ALLOW_CREDENTIALS = os.environ.get(
    'ACCESS_CONTROL_ALLOW_CREDENTIALS', 
    True)
ACCESS_CONTROL_ALLOW_ORIGIN = os.environ.get(
    'ACCESS_CONTROL_ALLOW_ORIGIN', 
    "*").split(",")
ACCESS_CONTROL_ALLOW_METHODS = os.environ.get(
    'ACCESS_CONTROL_ALLOW_METHODS', 
    "GET,OPTIONS,PATCH,DELETE,POST,PUT").split(",")
ACCESS_CONTROL_ALLOW_HEADERS = os.environ.get(
    'ACCESS_CONTROL_ALLOW_HEADERS', 
    "X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version").split(",")

app.add_middleware(CORSMiddleware, 
                   allow_origins=ACCESS_CONTROL_ALLOW_ORIGIN,
                   allow_credentials=ACCESS_CONTROL_ALLOW_CREDENTIALS,
                   allow_methods=ACCESS_CONTROL_ALLOW_METHODS,
                   allow_headers=ACCESS_CONTROL_ALLOW_HEADERS
                   )

@app.post("/process")
async def process_item(ideas: list[str]):
    (results, plot_data) = centroid_analysis(ideas)
    return JSONResponse(content={"results": results, "plot_data": plot_data})

def centroid_analysis(ideas: list):
    # Initialize CountVectorizer to convert text into numerical vectors
    count_vectorizer = CountVectorizer()
    analyzer = Analyzer(ideas, count_vectorizer)
    coords, marker_sizes = analyzer.process_get_data()

    results = {
        "ideas": analyzer.ideas, 
        "similarity": analyzer.cos_similarity.tolist(), 
        "distance": analyzer.distance_to_centroid.tolist()
    }
    data = {
        "scatter_points": coords.tolist(),
        "marker_sizes": marker_sizes.tolist(),
        "ideas": analyzer.ideas,
        "pairwise_similarity": analyzer.pairwise_similarity.tolist(),
    }
    return (results, data)


@app.get("/")
def index():
    return {"message": "Hello There! To process ideas, send a list of strings to the /process endpoint."}