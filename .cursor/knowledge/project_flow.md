```mermaid
graph TD
    A[Client] -->|1. API Request| B[/api/v1/projects]
    
    subgraph Project Routes
        B -->|POST| C[Create Project]
        B -->|GET| D[List Projects]
        B -->|GET /{id}| E[Get Project]
        B -->|PUT /{id}| F[Update Project]
        B -->|DELETE /{id}| G[Delete Project]
    end
    
    subgraph Authentication & Authorization
        H[Current User]
        I[Permissions]
        J[API Key]
    end
    
    subgraph Service Layer
        K[Project Service]
        L[Database Operations]
        M[Cache Operations]
        N[Event Publishing]
    end
    
    subgraph Response Format
        O[Standard Response]
        P[Error Handling]
        Q[Pagination]
    end
    
    subgraph Data Models
        R[Project Create]
        S[Project Update]
        T[Project Response]
        U[Project List Response]
    end
    
    B --> H
    H --> I
    I --> K
    
    C --> R
    R --> K
    K --> L
    K --> M
    K --> N
    
    D --> Q
    Q --> U
    
    E --> T
    F --> S
    S --> K
    
    K -->|Success| O
    K -->|Error| P
    
    subgraph Error Categories
        V[Business Logic]
        W[Validation]
        X[Infrastructure]
    end
    
    P --> V
    P --> W
    P --> X
    
    subgraph Dependencies
        Y[Database]
        Z[Redis]
        AA[Event Bus]
    end
    
    L --> Y
    M --> Z
    N --> AA
``` 