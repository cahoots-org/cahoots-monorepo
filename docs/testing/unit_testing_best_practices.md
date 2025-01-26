# Unit Testing Best Practices Guide

## Core Principles

1. **Test Behavior, Not Implementation**
   - Focus on testing what the code does, not how it does it
   - Write tests that remain valid even if the implementation changes
   - Test public interfaces rather than private methods

2. **Keep Tests FIRST**
   - **F**ast: Tests should run quickly
   - **I**solated: Tests should not depend on each other
   - **R**epeatable: Tests should be deterministic
   - **S**elf-validating: Tests should have a boolean output
   - **T**imely: Tests should be written before or with the code

3. **One Assert Per Test**
   - Each test should verify one specific behavior
   - Multiple assertions are acceptable if they're testing the same concept
   - Use descriptive test names that indicate what's being tested

## Test Structure

### AAA Pattern (Arrange-Act-Assert)
```python
@pytest.mark.asyncio
async def test_example():
    # Arrange
    service = Service(mock_dependency)
    input_data = {"key": "value"}
    
    # Act
    result = await service.process(input_data)
    
    # Assert
    assert result.status == "success"
```

### Naming Convention
- Use descriptive names that indicate:
  1. What is being tested
  2. Under what conditions
  3. Expected outcome
```python
def test_process_valid_input_returns_success():
def test_process_invalid_input_raises_validation_error():
def test_process_empty_input_returns_default_value():
```

## Mocking Guidelines

### What to Mock
1. **External Services**
   - APIs
   - Databases
   - File systems
   - Message queues

2. **Non-deterministic Operations**
   - Time-dependent functions
   - Random number generators
   - UUID generators

3. **Expensive Operations**
   - Network calls
   - Heavy computations
   - Operations with side effects

### What Not to Mock
1. **The System Under Test**
   - Never mock the class/module you're testing

2. **Value Objects**
   - DTOs
   - Data structures
   - Configuration objects

3. **Simple Pure Functions**
   - Utility functions
   - Transformations
   - Calculations

### Mocking Best Practices
1. **Use Dependency Injection**
```python
# Good
class Service:
    def __init__(self, client):
        self.client = client

# Avoid
class Service:
    def __init__(self):
        self.client = RealClient()
```

2. **Mock at Boundaries**
```python
# Good - Mock at service boundary
mock_db = AsyncMock()
service = Service(db_client=mock_db)

# Avoid - Mock internal implementation
service = Service(real_db)
service._internal_method = Mock()
```

3. **Use Appropriate Mock Types**
```python
# For async functions
client = AsyncMock()
client.fetch.return_value = {"data": "value"}

# For synchronous functions
client = MagicMock()
client.process.return_value = "result"

# For context managers
mock_file = mock_open(read_data="data")
```

## Testing Async Code

1. **Use Proper Decorators**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await function()
    assert result is not None
```

2. **Mock Async Operations Correctly**
```python
mock_client = AsyncMock()
mock_client.fetch.return_value = {"status": "success"}
```

3. **Handle Coroutines Properly**
```python
# Good
mock_result = AsyncMock()
mock_result.scalar.return_value = expected_value
mock_db.execute.return_value = mock_result

# Avoid
mock_db.execute.return_value = expected_value  # Will cause coroutine errors
```

## Common Patterns

### Testing Exceptions
```python
@pytest.mark.asyncio
async def test_invalid_input_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        await service.process(invalid_input)
    assert str(exc_info.value) == "Expected error message"
```

### Testing Collections
```python
def test_list_processing():
    result = process_list([1, 2, 3])
    assert len(result) == 3
    assert all(isinstance(x, int) for x in result)
    assert result == [2, 4, 6]
```

### Testing Side Effects
```python
@pytest.mark.asyncio
async def test_operation_with_side_effects():
    # Arrange
    mock_db = AsyncMock()
    service = Service(mock_db)
    
    # Act
    await service.process()
    
    # Assert
    mock_db.save.assert_called_once_with(expected_data)
    mock_db.commit.assert_called_once()
```

## Anti-patterns to Avoid

1. **Test Implementation Details**
```python
# Bad - Testing private methods
test_service._private_method()

# Good - Test public interface
test_service.public_method()
```

2. **Non-Isolated Tests**
```python
# Bad - Tests depend on each other
def test_first():
    global shared_data
    shared_data = process()

def test_second():
    assert shared_data is not None

# Good - Each test is self-contained
def test_first():
    result = process()
    assert result is not None

def test_second():
    result = process()
    assert result.valid
```

3. **Overcomplicated Setup**
```python
# Bad - Complex setup
def test_with_complex_setup():
    mock1 = create_complex_mock()
    mock2 = create_another_mock()
    service = Service(mock1, mock2)
    data = create_complex_data()
    
    result = service.process(data)
    
    assert result.success

# Good - Use fixtures and helper functions
@pytest.fixture
def service():
    return create_test_service()

def test_with_clean_setup(service):
    result = service.process(sample_data())
    assert result.success
```

## Testing Database Operations

1. **Use Transactions**
```python
@pytest.mark.asyncio
async def test_db_operation():
    async with AsyncTestTransaction():
        result = await service.save(data)
        assert result.id is not None
```

2. **Mock DB Responses**
```python
mock_db = AsyncMock()
mock_db.execute.return_value.scalar_one_or_none.return_value = mock_record
```

## SQLAlchemy Testing Best Practices

1. **Avoid Real Models in Unit Tests**
```python
# Bad - Using real SQLAlchemy models in tests
from models import User
test_user = User(id=1, name="test")

# Good - Using simple mocks with required attributes
test_user = MagicMock(
    id=1, 
    name="test",
    # Add only attributes needed for test
)
```

2. **Mock Database Results**
```python
# Bad - Creating actual model instances
mock_db.query.return_value = [User(id=1), User(id=2)]

# Good - Return simple mock objects
mock_db.execute.return_value.scalars.return_value = [
    MagicMock(id=1, name="user1"),
    MagicMock(id=2, name="user2")
]
```

3. **Focus on Service Logic**
```python
# Bad - Testing SQLAlchemy features
def test_user_relationship():
    user = User(id=1)
    assert user.posts.count() == 0  # Testing SQLAlchemy relationship

# Good - Testing service behavior
async def test_get_user_posts():
    mock_user = MagicMock(id=1)
    mock_db.execute.return_value.scalar_one_or_none.return_value = mock_user
    result = await service.get_user_posts(1)
    assert result == []  # Testing service logic
```

4. **Handle Async Operations**
```python
# Good - Proper async mock setup
mock_db = AsyncMock()
mock_result = MagicMock()
mock_db.execute.return_value.scalar_one_or_none.return_value = mock_result

# Also Good - Mocking specific async methods
mock_db = MagicMock()
mock_db.execute = AsyncMock(return_value=mock_result)
```

5. **Test Data Access Patterns**
```python
# Good - Testing service's data access logic
@pytest.mark.asyncio
async def test_get_user_by_id():
    # Arrange
    expected_user = MagicMock(id=1, name="test")
    mock_db.execute.return_value.scalar_one_or_none.return_value = expected_user
    
    # Act
    result = await service.get_user(1)
    
    # Assert
    assert result.id == expected_user.id
    assert result.name == expected_user.name
    mock_db.execute.assert_called_once()  # Verify query was made
```

Remember:
- Unit tests should not initialize SQLAlchemy mappers
- Focus on testing service logic, not SQLAlchemy features
- Use simple mocks that only include attributes needed for tests
- Keep database interaction mocks at the execute/scalar level
- Test the service's data access patterns, not the ORM behavior

## Testing External APIs

1. **Mock Network Calls**
```python
@patch('aiohttp.ClientSession.get')
async def test_api_call(mock_get):
    mock_get.return_value.__aenter__.return_value.json.return_value = {'data': 'value'}
    result = await service.fetch_data()
    assert result['data'] == 'value'
```

2. **Use Response Factories**
```python
def create_mock_response(status=200, data=None):
    mock_response = AsyncMock()
    mock_response.status = status
    mock_response.json.return_value = data
    return mock_response
```

## Maintainable Tests

1. **Use Constants for Test Data**
```python
TEST_USER_ID = "test-user-123"
SAMPLE_PAYLOAD = {"key": "value"}

def test_with_constants():
    result = service.process(SAMPLE_PAYLOAD)
    assert result.user_id == TEST_USER_ID
```

2. **Create Helper Functions**
```python
def create_test_user(**kwargs):
    defaults = {
        "id": "test-id",
        "name": "Test User",
        "email": "test@example.com"
    }
    return {**defaults, **kwargs}
```

3. **Group Related Tests**
```python
class TestUserService:
    """Group all user-related tests."""
    
    async def test_create_user(self):
        pass
        
    async def test_update_user(self):
        pass
```

## Documentation

1. **Write Clear Test Descriptions**
```python
async def test_process_valid_input():
    """
    Test that process() correctly handles valid input by:
    1. Validating the input
    2. Transforming the data
    3. Returning success response
    """
```

2. **Document Test Requirements**
```python
"""
Requirements:
- Database must be empty before test
- Redis cache must be available
- API key must be set in environment
"""
```

## Continuous Integration

1. **Run Tests in CI Pipeline**
```yaml
test:
  script:
    - pytest --cov=app tests/
    - coverage report
```

2. **Maintain Test Coverage**
```python
# pytest.ini
[pytest]
minversion = 6.0
addopts = --cov=app --cov-report=term-missing
testpaths = tests
```

## Resources

1. **Testing Frameworks**
   - pytest
   - unittest
   - nose2

2. **Mocking Libraries**
   - unittest.mock
   - pytest-mock
   - asynctest

3. **Coverage Tools**
   - pytest-cov
   - coverage.py

## Final Tips

1. **Keep Tests Simple**
   - If a test is hard to write, the code might need refactoring
   - Break down complex tests into smaller, focused tests
   - Use helper functions and fixtures to reduce duplication

2. **Test Edge Cases**
   - Null/None values
   - Empty collections
   - Boundary conditions
   - Error conditions

3. **Maintain Tests**
   - Update tests when requirements change
   - Remove obsolete tests
   - Refactor tests when they become hard to maintain
``` 