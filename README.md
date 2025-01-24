# SimScore API

An API for semantic similarity analysis and idea ranking.

Demo UI: https://simscore.xyz/

API URL: https://simscore-api-dev.fly.dev

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
curl -X POST "{{api-url}}/v1/rank_ideas" \
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
curl -X POST "{{api-url}}/v1/auth/sign_up" \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "password": "your_password"
}'
```
This will send a verification email with a registration link and a one-time code.
Click the link, or to use the code call 
```bash
curl -X POST "{{api-url}}/v1/auth/verify_email" \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "code": "123456"
}'
```

Last step is to create an API key:
```bash
curl -X POST "{{api-url}}/v1/auth/create_api_key" \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "password": "your_password"
}'
```

This will return your API key, which you can use as 'bearer token' for future API calls:

```json
{
  "api_key": "your-api-key"
}
```

Once you have registered and need to access your tokens again, you can retrieve it with 
```bash
curl -X POST "{{api-url}}/v1/auth/api_keys" \
-H "Content-Type: application/json" \
-d '{
  "email": "your@email.com",
  "password": "your_password"
}'
```

And to revoke keys:
```bash
curl -X DELETE "{{api-url}}/v1/auth/revoke_api_key/{your-api-key}" \
-H "Authorization: Bearer {{your-bearer-token}}"
```

Use your token in requests:
```bash
curl -X POST "{{api-url}}/v1/rank_ideas" \
-H "Authorization: Bearer {{your API Key here}}" \
-H "Content-Type: application/json" \
-d '{"ideas": [...]}'
```

#### Enterprise Usage
Need higher limits? Contact the maintainer for custom quotas tailored to your needs.


### Advanced Analysis
```bash
curl -X POST "{{api-url}}/v1/rank_ideas" \
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


## Limits
The quality & amount of API calls you can make depends on multiple factors:
* Hard limits
* Credits (Daily Quota)
* Fair usage

### Hard Limits
These are limits for the type of data you can submit. 
Anything outside of these parameters will be rejected:

* At least 4 ideas need to be submitted in order for the analysis to run successful
* A maxiumum of 10'000 ideas or 10mb of data (whichever is smaller) will be enforced. Should you require higher limits, please get in touch. 

### Credits
Every API call will use up a certain amount of credits, depending on how much compute it uses.
both the credits used as well as the daily amount of free credits remain subject to change based on availability & demand. 
You can get a daily amount of credits without registering, or a higher amount after registering as a user.
To see the remaining amount of credits:

```bash
curl -X GET "{{api-url}}/v1/auth/credits" \
-H "Authorization: Bearer {{your-bearer-token}}"
```

### Fair usage
To ensure fair access for all users, the following rate limits apply:

* Guest users:
  * 10 credits per day
  * Maximum of 100 total credits
  * 20 requests per minute

* Registered users:
  * 100 credits per day  
  * Maximum of 1000 total credits
  * 20 requests per minute

* Global limit of 1000 requests per minute across all users

Exceeding these limits will result in HTTP 429 (Too Many Requests) responses. If you need higher limits, please contact us to discuss enterprise options.


## Local Development

1. Install dependencies:

`poetry install --no-root`


2. Add new dependencies as needed:

`poetry add <package-name>`


3. Start local Supabase:

`supabase start`


4. Run fastapi:

`fastapi dev`


5. For local email verification:
   - Run `supabase status` to see the Inbucket URL
   - Open Inbucket in your browser to view sent emails
   - Default URL is usually: http://localhost:54324