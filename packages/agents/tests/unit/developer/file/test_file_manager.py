"""Unit tests for file manager."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import os
import tempfile
import shutil

from .....src.cahoots_agents.developer.file.file_manager import FileManager

@pytest.fixture
def mock_agent():
    """Create mock developer agent."""
    agent = Mock()
    agent.generate_response = AsyncMock()
    return agent

@pytest.fixture
def temp_workspace():
    """Create temporary workspace."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def file_manager(mock_agent, temp_workspace):
    """Create file manager with mocked agent and temp workspace."""
    return FileManager(mock_agent, workspace_dir=temp_workspace)

def test_init_workspace(file_manager, temp_workspace):
    """Test workspace initialization."""
    assert file_manager.workspace_dir == temp_workspace
    assert os.path.exists(temp_workspace)

def test_create_file(file_manager, temp_workspace):
    """Test file creation."""
    file_path = "test.py"
    content = "def test(): pass"
    
    file_manager.create_file(file_path, content)
    
    full_path = os.path.join(temp_workspace, file_path)
    assert os.path.exists(full_path)
    with open(full_path) as f:
        assert f.read() == content

def test_create_file_in_subdirectory(file_manager, temp_workspace):
    """Test file creation in subdirectory."""
    file_path = "subdir/test.py"
    content = "def test(): pass"
    
    file_manager.create_file(file_path, content)
    
    full_path = os.path.join(temp_workspace, file_path)
    assert os.path.exists(full_path)
    assert os.path.isdir(os.path.dirname(full_path))

def test_read_file(file_manager, temp_workspace):
    """Test file reading."""
    file_path = "test.py"
    content = "def test(): pass"
    full_path = os.path.join(temp_workspace, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    
    read_content = file_manager.read_file(file_path)
    
    assert read_content == content

def test_read_file_not_found(file_manager):
    """Test reading non-existent file."""
    with pytest.raises(FileNotFoundError):
        file_manager.read_file("nonexistent.py")

def test_update_file(file_manager, temp_workspace):
    """Test file updating."""
    file_path = "test.py"
    original_content = "def test(): pass"
    new_content = "def updated_test(): pass"
    full_path = os.path.join(temp_workspace, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(original_content)
    
    file_manager.update_file(file_path, new_content)
    
    with open(full_path) as f:
        assert f.read() == new_content

def test_delete_file(file_manager, temp_workspace):
    """Test file deletion."""
    file_path = "test.py"
    content = "def test(): pass"
    full_path = os.path.join(temp_workspace, file_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)
    
    file_manager.delete_file(file_path)
    
    assert not os.path.exists(full_path)

def test_delete_file_not_found(file_manager):
    """Test deleting non-existent file."""
    with pytest.raises(FileNotFoundError):
        file_manager.delete_file("nonexistent.py")

def test_list_files(file_manager, temp_workspace):
    """Test listing files."""
    files = {
        "test1.py": "def test1(): pass",
        "subdir/test2.py": "def test2(): pass",
        "subdir/test3.py": "def test3(): pass"
    }
    for path, content in files.items():
        full_path = os.path.join(temp_workspace, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    
    file_list = file_manager.list_files()
    
    assert len(file_list) == 3
    assert all(f in file_list for f in files.keys())

def test_list_files_with_pattern(file_manager, temp_workspace):
    """Test listing files with pattern matching."""
    files = {
        "test1.py": "def test1(): pass",
        "test2.js": "function test2() {}",
        "subdir/test3.py": "def test3(): pass"
    }
    for path, content in files.items():
        full_path = os.path.join(temp_workspace, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
    
    python_files = file_manager.list_files(pattern="*.py")
    
    assert len(python_files) == 2
    assert all(f.endswith(".py") for f in python_files)

def test_create_directory(file_manager, temp_workspace):
    """Test directory creation."""
    dir_path = "testdir"
    
    file_manager.create_directory(dir_path)
    
    full_path = os.path.join(temp_workspace, dir_path)
    assert os.path.exists(full_path)
    assert os.path.isdir(full_path)

def test_create_nested_directory(file_manager, temp_workspace):
    """Test nested directory creation."""
    dir_path = "parent/child/grandchild"
    
    file_manager.create_directory(dir_path)
    
    full_path = os.path.join(temp_workspace, dir_path)
    assert os.path.exists(full_path)
    assert os.path.isdir(full_path)

def test_delete_directory(file_manager, temp_workspace):
    """Test directory deletion."""
    dir_path = "testdir"
    full_path = os.path.join(temp_workspace, dir_path)
    os.makedirs(full_path)
    
    file_manager.delete_directory(dir_path)
    
    assert not os.path.exists(full_path)

def test_delete_directory_with_contents(file_manager, temp_workspace):
    """Test deletion of directory with contents."""
    dir_path = "testdir"
    file_path = os.path.join(dir_path, "test.py")
    full_dir_path = os.path.join(temp_workspace, dir_path)
    os.makedirs(full_dir_path)
    with open(os.path.join(temp_workspace, file_path), "w") as f:
        f.write("def test(): pass")
    
    file_manager.delete_directory(dir_path)
    
    assert not os.path.exists(full_dir_path) 