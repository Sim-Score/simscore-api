# SimScore API

An API for semantic similarity analysis and idea ranking.

Demo UI: https://simscore.xyz/
API URL: https://simscore-api.fly.dev

## Features

- Semantic similarity analysis for large sets of ideas
- Cluster analysis with automatic category naming
- Relationship graph generation
- Pairwise similarity matrix

## API Usage

### Basic Analysis

#### Guest Access
SimScore API can be used without authentication, allowing you to try out the basic features with a limited daily quota. Simply make requests without an Authorization header:

```bash
curl -X POST "{{api-url}}/v1/rank-ideas" \
-H "Content-Type: application/json" \
-d '{
  "ideas": [
    {"id": "1", "idea": "Implement AI chatbot support"},
    {"id": "2", "idea": "Add voice recognition features"},
    {"id": "3", "idea": "Create automated customer service"}
  ]
}'
```

(Example) Response:
```json
{
  "ranked_ideas": [
    {
      "id": "1",
      "idea": "Implement AI chatbot support",
      "similarity_score": 0.89,
      "cluster_id": 0
    },
    {
      "id": "3",
      "idea": "Create automated customer service",
      "similarity_score": 0.85,
      "cluster_id": 0
    },
    {
      "id": "2",
      "idea": "Add voice recognition features",
      "similarity_score": 0.72,
      "cluster_id": 1
    }
  ],
  "relationship_graph": null,
  "pairwise_similarity_matrix": null,
  "cluster_names": null
}
```

#### Registered Users
Get higher daily quotas by registering for an account. Registration is straightforward:

Create an account:
```bash
curl -X POST "{{api-url}}/v1/auth/signup" \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "password": "your_password"
}'
```

This will return your bearer token:

{
  "access_token": "your-bearer-token"
}

Once you have registered and need to access your token again, you can retrieve it with 
```bash
curl -X POST "{{api-url}}/v1/auth/login" \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "password": "your_password"
}'
```

Use your token in requests:
```bash
curl -X POST "{{api-url}}/v1/rank-ideas" \
-H "Authorization: Bearer {{your-bearer-token here}}" \
-H "Content-Type: application/json" \
-d '{"ideas": [...]}'
```

#### Enterprise Usage
Need higher limits? Contact the maintainer for custom quotas tailored to your needs.


### Advanced Analysis
```bash
curl -X POST "{{api-url}}/v1/rank-ideas" \
-H "Authorization: Bearer [your-bearer-token here]" \
-H "Content-Type: application/json" \
-d '{
  "ideas": [
    {"id": "1", "idea": "Implement AI chatbot support"},
    {"id": "2", "idea": "Add voice recognition features"}
  ],
  "advanced_features": {
    "relationship_graph": true,
    "cluster_names": true,
    "pairwise_similarity_matrix": true
  }
}'
```

(Example) Response:
```json
{
  "ranked_ideas": [
    {
      "id": "1",
      "idea": "Implement AI chatbot support",
      "similarity_score": 0.89,
      "cluster_id": 0
    },
    {
      "id": "2",
      "idea": "Add voice recognition features",
      "similarity_score": 0.72,
      "cluster_id": 1
    }
  ],
  "relationship_graph": {
    "nodes": [
      {
        "id": "1",
        "coordinates": {"x": 0.8, "y": 0.2}
      },
      {
        "id": "2",
        "coordinates": {"x": 0.3, "y": 0.7}
      },
      {
        "id": "Centroid",
        "coordinates": {"x": 0.5, "y": 0.5}
      }
    ],
    "edges": [
      {
        "from_id": "1",
        "to_id": "2",
        "similarity": 0.65
      },
      {
        "from_id": "1",
        "to_id": "Centroid",
        "similarity": 0.89
      },
      {
        "from_id": "2",
        "to_id": "Centroid",
        "similarity": 0.72
      }
    ]
  },
  "cluster_names": {
    "0": "AI Customer Support",
    "1": "Voice Technologies"
  },
  "pairwise_similarity_matrix": [
    [1.0, 0.65],
    [0.65, 1.0]
  ]
}
```

### Limits
* At least 4 ideas need to be submitted in order for the analysis to run successful
* A maxiumum of 10'000 ideas or 10mb of data (whichever is smaller) will be enforced. Should you require higher limits, please get in touch. 
