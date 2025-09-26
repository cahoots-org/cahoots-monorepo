# Cahoots Project Manager - Monolith Refactor

## Executive Summary

This refactor transforms the Cahoots Project Manager from a complex microservices architecture (7+ services) into an optimized monolith with 50-60% fewer LLM calls while maintaining the same task decomposition quality. The key innovation is combining multiple analysis steps into single LLM calls and implementing intelligent caching strategies.

## Current Architecture Problems

### 1. Excessive LLM Usage
- **Current State**: 8-12 LLM calls per complex task
- **Redundancies**:
  - Complexity scorer checks atomicity → Decomposer checks atomicity again
  - Separate calls for: complexity, atomicity, specificity, decomposition, implementation details
  - Gap analysis runs unnecessarily at all depths
  - Every atomic subtask gets separate implementation details call

### 2. Over-Engineering
- **7 separate services** for what is essentially a linear pipeline
- **Redis streams** for communication adds latency without benefit
- **Multiple databases**: Redis for tasks, Redis for streams, Elasticsearch for search
- **Complex deployment**: Kubernetes manifests, multiple Docker containers, service mesh

### 3. Performance Issues
- **Service hops**: Each task goes through 5-7 services
- **Network latency**: Inter-service communication overhead
- **Duplicate processing**: Same analysis done multiple times
- **Cache underutilization**: Only caching subtask generation, not analysis

## Optimized Monolith Architecture

### Core Components

```
/refactor/
├── app/
│   ├── analyzer/          # Unified task analysis (1 LLM call)
│   ├── processor/         # Single-pass processing pipeline
│   ├── cache/            # Multi-layer intelligent caching
│   ├── api/              # Single unified API
│   └── storage/          # Simple Redis storage
├── frontend/             # Unchanged React frontend
└── docker-compose.yml    # Simple 2-container setup
```

### Key Optimizations

#### 1. Unified Task Analyzer
**Before**: 3-4 separate LLM calls
```
- Complexity scoring (1 call)
- Atomicity check (1 call)
- Specificity check (1 call)
- Implementation details (1 call if atomic)
```

**After**: 1 unified LLM call
```json
{
  "complexity_score": 0.7,
  "is_atomic": false,
  "is_specific": true,
  "confidence": 0.85,
  "suggested_approach": "decompose",
  "implementation_hints": null,
  "estimated_story_points": 5
}
```

#### 2. Smart Decomposition
**Before**: Separate decomposition + implementation details for each atomic subtask
**After**: Single call returns everything
```json
{
  "subtasks": [
    {
      "description": "Create user authentication API",
      "is_atomic": true,
      "implementation_details": "Use JWT with refresh tokens...",
      "story_points": 3
    },
    {
      "description": "Build user interface",
      "is_atomic": false,
      "subtasks": null  // Will be decomposed recursively
    }
  ]
}
```

#### 3. Intelligent Caching
**Three-tier cache system**:
1. **Exact Match Cache** (Redis): Direct task description matches
2. **Semantic Cache** (Embeddings): Similar tasks (>85% similarity)
3. **Template Cache**: Common patterns (CRUD, auth, etc.)

**Expected cache hit rates**:
- Simple tasks: 60-70% (templates)
- Medium tasks: 35-45% (semantic similarity)
- Complex tasks: 20-30% (partial matches)

#### 4. Conditional Processing Rules
```python
RULES = {
    "skip_gap_analysis": depth > 0,           # Only root tasks
    "skip_root_processing": complexity < 0.3,  # Simple tasks
    "use_template": matches_common_pattern,    # CRUD, auth, etc.
    "force_atomic": depth >= 5,                # Depth limit
    "batch_siblings": sibling_count > 3        # Batch processing
}
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
- [x] Create directory structure
- [ ] Implement unified analyzer with single LLM call
- [ ] Set up basic FastAPI application
- [ ] Create Pydantic models for all data types
- [ ] Implement Redis storage layer

### Phase 2: Core Processing (Week 2)
- [ ] Build single-pass task processor
- [ ] Implement smart decomposer with inline atomic handling
- [ ] Create conditional processing rules engine
- [ ] Add batch processing for siblings
- [ ] Integrate multi-layer caching

### Phase 3: API & Integration (Week 3)
- [ ] Merge all API endpoints into single service
- [ ] Implement WebSocket for real-time updates
- [ ] Connect frontend to new API
- [ ] Add authentication and authorization
- [ ] Create metrics and monitoring

### Phase 4: Testing & Deployment (Week 4)
- [ ] Write comprehensive test suite
- [ ] Performance benchmarking
- [ ] Create Docker containers
- [ ] Write deployment documentation
- [ ] Gradual rollout strategy

## Performance Targets

### LLM Call Reduction
| Task Type | Current Calls | Target Calls | Reduction |
|-----------|--------------|--------------|-----------|
| Simple (atomic) | 3-4 | 1 | 70% |
| Medium (1 level) | 6-8 | 2-3 | 60% |
| Complex (multi-level) | 10-15 | 4-6 | 55% |

### Processing Speed
- **Current**: 5-10 seconds per task (with network hops)
- **Target**: 2-4 seconds per task
- **Improvement**: 50-60% faster

### Infrastructure Simplification
- **Services**: 7 → 1
- **Containers**: 8+ → 2 (app + redis)
- **Configuration files**: 20+ → 5
- **Lines of code**: ~15,000 → ~5,000

## Technical Specifications

### Environment Variables
```bash
# Required
LAMBDA_API_KEY=            # Primary LLM provider
REDIS_URL=redis://redis:6379

# Optional
GROQ_API_KEY=              # Backup LLM provider
CACHE_TTL=3600            # Cache time-to-live
MAX_DEPTH=5               # Maximum decomposition depth
BATCH_SIZE=5              # Sibling batch size
USE_SEMANTIC_CACHE=true   # Enable embedding cache
```

### API Endpoints
```
POST   /api/tasks          # Create and process task
GET    /api/tasks/{id}     # Get task details
GET    /api/tasks/{id}/tree # Get full task tree
WS     /ws                 # WebSocket for updates
GET    /health            # Health check
GET    /metrics           # Performance metrics
```

### Data Models

#### Task
```python
class Task:
    id: str
    description: str
    status: TaskStatus
    depth: int
    parent_id: Optional[str]
    is_atomic: bool
    complexity_score: float
    implementation_details: Optional[str]
    story_points: Optional[int]
    subtasks: List[str]  # Just IDs, not full objects
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
```

#### TaskAnalysis
```python
class TaskAnalysis:
    complexity_score: float
    is_atomic: bool
    is_specific: bool
    confidence: float
    reasoning: str
    suggested_approach: ApproachType
    implementation_hints: Optional[str]
    estimated_story_points: Optional[int]
    requires_human_review: bool
    similar_patterns: List[str]
```

## Migration Strategy

### 1. Parallel Running (Week 1-2)
- Deploy monolith alongside microservices
- Route 10% traffic to monolith
- Monitor performance and quality

### 2. Gradual Rollout (Week 3)
- Increase traffic to 50%
- A/B test quality metrics
- Gather user feedback

### 3. Full Migration (Week 4)
- Move 100% traffic to monolith
- Keep microservices as backup
- Decommission after 1 week stable

## Success Metrics

### Must Have
- ✅ 50%+ reduction in LLM calls
- ✅ Maintained task quality (user satisfaction)
- ✅ 40%+ faster processing time
- ✅ Simplified deployment (2 containers max)

### Nice to Have
- 35%+ cache hit rate
- 60%+ reduction in infrastructure costs
- 70%+ reduction in codebase size
- Sub-second response for cached tasks

## Risk Mitigation

### Risk: Quality Degradation
**Mitigation**:
- Extensive testing with real tasks
- A/B testing during rollout
- Keep microservices as fallback

### Risk: Cache Invalidation Issues
**Mitigation**:
- Time-based expiration
- Manual invalidation API
- Version-based cache keys

### Risk: Single Point of Failure
**Mitigation**:
- Horizontal scaling capability
- Redis persistence
- Health checks and auto-restart

## Development Workflow

### Local Development
```bash
# Start services
docker-compose up -d

# Run tests
pytest tests/

# Check metrics
curl localhost:8000/metrics
```

### Testing Strategy
1. **Unit Tests**: Each component isolated
2. **Integration Tests**: Full pipeline
3. **Load Tests**: 100+ concurrent tasks
4. **Quality Tests**: Compare with microservices output

## Frequently Used Commands

### Development
```bash
# Run locally
uvicorn app.main:app --reload --port 8000

# Run tests
pytest tests/ -v --cov=app

# Check code quality
black app/ --check
pylint app/
mypy app/
```

### Docker
```bash
# Build and run
docker-compose up -d --build

# View logs
docker-compose logs -f app

# Access Redis CLI
docker-compose exec redis redis-cli

# Clean restart
docker-compose down -v && docker-compose up -d --build
```

### Monitoring
```bash
# Check health
curl localhost:8000/health

# View metrics
curl localhost:8000/metrics | jq

# Watch LLM calls
tail -f logs/llm_calls.log | grep -E "calls_per_minute|cache_hit"
```

## Next Steps

1. **Immediate**: Start implementing unified analyzer
2. **This Week**: Complete Phase 1 foundation
3. **Next Week**: Begin Phase 2 core processing
4. **Month End**: Full deployment ready

## Notes for Future Development

### Potential Optimizations
- **Streaming decomposition**: Return subtasks as generated
- **Predictive caching**: Pre-cache likely next tasks
- **Model fine-tuning**: Train smaller model on task patterns
- **Edge caching**: CDN for common templates

### Lessons Learned
- Microservices added complexity without benefit for this use case
- Caching is more valuable than service separation
- Unified LLM calls reduce cost and latency
- Simple architectures are often better

## Contact & Support

For questions about this refactor:
- Review this document first
- Check test files for examples
- Run metrics endpoint for performance data
- Git history has detailed commit messages

---

*Last Updated: 2025-09-23*
*Refactor Version: 1.0.0*
*Original Architecture Version: 0.8.x*