# SimScore API Specifications

To keep the core API sleek while providing advanced features like the relationship graph and pairwise similarity matrix, we can add an optional **query parameter** to enable these advanced features. This way, users can request these extra outputs without cluttering the basic functionality.

Here’s an updated version of the API specification with advanced options:

---

### **SimScore API Specification (with Advanced Features)**

### **Base URL**

`https://api.simscore.com`

### **Endpoints**

1. **POST /rank-ideas**
    
    This endpoint will accept a list of subjective opinions (ideas), calculate similarity scores, assign clusters, and optionally include advanced outputs such as the relationship graph and pairwise similarity matrix.
    

---

### **Request Body** (Input)

```json
{
  "ideas": [
    {"id": 1, "idea": "Idea 1 description"},
    {"id": 2, "idea": "Idea 2 description"},
    {"id": 3, "idea": "Idea 3 description"},
    ...
  ],
  "advanced_features": {
    "relationship_graph": false,
    "pairwise_similarity_matrix": false
  }
}

```

- **ideas**: An array of objects, each representing an idea.
    - **id**: A unique identifier for the idea (integer).
    - **idea**: The textual description of the idea (string).
- **advanced_features**: An optional object for requesting advanced outputs.
    - **relationship_graph**: Boolean value (default `false`). If `true`, the response will include the relationship graph.
    - **pairwise_similarity_matrix**: Boolean value (default `false`). If `true`, the response will include the pairwise similarity matrix.
    - **cluster names:  Note:  not included in the gpt script>>>**Provides cluster names for each cluster determined in the SimScore Analysis.

---

### **Response Body** (Output)

```json
{
  "ranked_ideas": [
    {"id": 1, "idea": "Idea 1 description", "similarity_score": 0.85, "cluster_id": 1},
    {"id": 2, "idea": "Idea 2 description", "similarity_score": 0.78, "cluster_id": 2},
    {"id": 3, "idea": "Idea 3 description", "similarity_score": 0.72, "cluster_id": 1},
    ...
  ],
  "relationship_graph": {
    "nodes": [
      {"id": 1, "label": "Idea 1"},
      {"id": 2, "label": "Idea 2"},
      {"id": 3, "label": "Idea 3"}
    ],
    "edges": [
      {"from": 1, "to": 2, "weight": 0.85},
      {"from": 1, "to": 3, "weight": 0.75}
    ]
  },
  "pairwise_similarity_matrix": [
    [1.0, 0.85, 0.72],
    [0.85, 1.0, 0.78],
    [0.72, 0.78, 1.0]
  ]
}

```

- **ranked_ideas**: An array of ideas with their similarity score and assigned cluster ID.
    - **id**: The unique identifier for the idea (integer).
    - **idea**: The textual description of the idea (string).
    - **similarity_score**: The calculated similarity score (float between 0 and 1).
    - **cluster_id**: The ID of the cluster to which the idea has been assigned (integer).
- **relationship_graph**: The relationship graph, returned only if `advanced_features.relationship_graph` is set to `true`.
    - **nodes**: An array of node objects representing the ideas.
        - **id**: The unique identifier for each idea (integer).
        - **label**: The textual description of the idea (string).
    - **edges**: An array of edge objects representing the relationships between ideas, where each edge is a connection between two ideas.
        - **from**: The ID of the idea at the start of the edge (integer).
        - **to**: The ID of the idea at the end of the edge (integer).
        - **weight**: The similarity score (float) between the two ideas represented by the edge.
- **pairwise_similarity_matrix**: The pairwise similarity matrix, returned only if `advanced_features.pairwise_similarity_matrix` is set to `true`.
    - A 2D matrix (array of arrays), where each value `matrix[i][j]` represents the similarity score between idea `i` and idea `j`.

---

### **Example Request**

### Request URL

`POST https://api.simscore.com/rank-ideas`

### Request Body

```json
{
  "ideas": [
    {"id": 1, "idea": "Create a new mobile app for task management."},
    {"id": 2, "idea": "Build a mobile app for time tracking."},
    {"id": 3, "idea": "Develop a collaborative task management tool."}
  ],
  "advanced_features": {
    "relationship_graph": true,
    "pairwise_similarity_matrix": true
  }
}

```

---

### **Example Response**

### Response Body

```json
{
  "ranked_ideas": [
    {"id": 1, "idea": "Create a new mobile app for task management.", "similarity_score": 0.92, "cluster_id": 1},
    {"id": 3, "idea": "Develop a collaborative task management tool.", "similarity_score": 0.85, "cluster_id": 1},
    {"id": 2, "idea": "Build a mobile app for time tracking.", "similarity_score": 0.79, "cluster_id": 2}
  ],
  "relationship_graph": {
    "nodes": [
      {"id": 1, "label": "Create a new mobile app for task management."},
      {"id": 2, "label": "Build a mobile app for time tracking."},
      {"id": 3, "label": "Develop a collaborative task management tool."}
    ],
    "edges": [
      {"from": 1, "to": 2, "weight": 0.92},
      {"from": 1, "to": 3, "weight": 0.85},
      {"from": 2, "to": 3, "weight": 0.79}
    ]
  },
  "pairwise_similarity_matrix": [
    [1.0, 0.92, 0.85],
    [0.92, 1.0, 0.79],
    [0.85, 0.79, 1.0]
  ]
}

```

---

### **Authentication**

If authentication is required:

- Include a `Bearer token` in the header:

```
Authorization: Bearer <your-api-token>

```

---

### **Error Responses**

- **400 Bad Request**: If the request body is malformed or missing required data.
    
    ```json
    {
      "error": "Invalid input data. Please ensure the 'ideas' array is correctly formatted."
    }
    
    ```
    
- **500 Internal Server Error**: If an unexpected error occurs on the server side.
    
    ```json
    {
      "error": "An unexpected error occurred. Please try again later."
    }
    
    ```
    

---

### **Rate Limiting**

- Max requests: 1000 requests per minute.
- Max requests per user: 10 requests per minute. (Batch-processing)
- If the rate limit is exceeded, a `429 Too Many Requests` error will be returned:

```json
{
  "error": "Rate limit exceeded. Please try again later."
}

```

---

### **Advanced Features Overview**

- **Relationship Graph**: Provides a visual structure of how ideas relate to one another based on similarity scores. Useful for understanding the interconnections between different ideas.
- **Pairwise Similarity Matrix**: A matrix that shows the similarity between each pair of ideas. This is particularly useful for further analysis of idea clusters and relationships.
- **Cluster Names:**  Provides cluster names for each cluster determined in the SimScore Analysis.

---

This specification keeps the core functionality simple, while offering the relationship graph and pairwise similarity matrix as optional advanced features when required. The user can toggle them via the `advanced_features` parameter.

## Implementation Plan

- Create test suite and follow TDD for accurate and reliable results
- Create documentation for all API endpoints (tests will help with that)
- Improve endpoints & return values for easier public consumption
- Create postman collection for API (investigate); possibly use that for tests & documentation
- Investigate auto-documentation features
- Create `dev` and `prod` environments ~~(possibly also `staging` and/or `testing`, but likely not necessary)~~
- See https://community.fly.io/t/managing-multiple-environments/107/31 how to do that with fly.io
- ~~Create `dev` and `prod` databases (if required)~~
- CI/CD integration
    - Run tests on every push
    - Run tests on timed intervals (daily)
- User limitations
    - ~~Authentication?~~
    - Rate limiting (max 1000 reqs/minute; max 10 req/min/user)
- ~~Setup Auto-scaling?~~
    - ~~Make sure that more servers spin up when request is high~~
- Set up Error messaging & fault limits
    - Automatically message a sysadmin when there are errors
    - ~~Message when requests go above a specified limit, i.e. costs would go very high or similar~~
- Make sure others can be onboarded easily:
    - Good code documentation
    - Easy pipelines / good pipeline documentation (i.e. how to run tests, how to update code, how to maintain databases, etc)

- From Sonnet:
    1. API Documentation & OpenAPI Specification
        1. Add comprehensive API documentation using FastAPI's built-in Swagger/OpenAPI support
        2. Document all endpoints, request/response models, and error scenarios
        3. Include usage examples and authentication requirements
    2. Authentication & Security
        1. Implement proper API authentication (e.g., API keys or JWT tokens)
        2. Add rate limiting to prevent abuse
        3. Set up CORS policies properly
        4. Add input validation and sanitization
    3. Error Handling & Logging
        1. Create consistent error response formats
        2. Implement proper exception handling across all endpoints
        3. Add structured logging for better monitoring and debugging
        4. Set up error tracking (e.g., Sentry)
    4. Performance & Scalability
        1. Cache NLTK resources more efficiently
        2. Implement connection pooling for MongoDB
        3. Add caching layer for frequently accessed data
        4. Optimize the similarity calculations for larger datasets
    5. Code Structure
        1. Separate business logic from route handlers
        2. Create proper service layers
        3. Add middleware for common operations
        4. Implement proper dependency injection
    6. Testing & Quality
        1. Add unit tests for core functionality
        2. Implement integration tests for API endpoints
        3. Add load testing scenarios
        4. Set up CI/CD pipelines
    7. Monitoring & Observability
        1. Add health check endpoints
        2. Implement metrics collection
        3. Set up monitoring for API performance
        4. Add request tracing
    8. API Versioning
        1. Implement proper API versioning strategy
        2. Add backwards compatibility handling
        3. Document breaking changes policy