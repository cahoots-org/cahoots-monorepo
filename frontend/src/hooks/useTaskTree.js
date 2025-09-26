import { useTaskTree as useTaskTreeQuery } from './api/useTasks';
import { logger } from '../utils/logger';

export const useTaskTree = (task, isOpen) => {
  // Use React Query hook for task tree
  const {
    data: localTaskTree,
    isLoading: isLoadingTaskTree,
    error: taskTreeError,
    refetch: loadTaskTree
  } = useTaskTreeQuery(task?.task_id, {
    enabled: isOpen && !!task?.task_id
  });
  
  // Simple update function for compatibility
  const updateTaskTree = () => {
    loadTaskTree();
  };

  // Determine if this is a root task (no parent_id) or a leaf task (no children or empty children array)
  // Check if the task has children
  const hasChildren = task && (
    (task.children && task.children.length > 0) || 
    task.children_count > 0 || 
    (localTaskTree && localTaskTree.children && localTaskTree.children.length > 0)
  );
  const isRootTask = task && !task.parent_id;
  // Check if task is atomic
  const isAtomic = task && task.is_atomic === true;
  // Show decomposition tree only for non-atomic tasks that have children
  // For atomic tasks, we should show implementation details instead
  const showDecompositionTree = !isAtomic && hasChildren;

  return {
    localTaskTree,
    isLoadingTaskTree,
    taskTreeError: taskTreeError?.message || null,
    hasChildren,
    isRootTask,
    showDecompositionTree,
    loadTaskTree,
    updateTaskTree,
    lastUpdated: Date.now()
  };
};