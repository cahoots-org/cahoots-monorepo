// Professional Tree Visualization - Interactive task tree using design system
import React, { useState, useMemo, useEffect } from 'react';
import {
  Card,
  Button,
  IconButton,
  Text,
  Badge,
  ChevronDownIcon,
  ChevronRightIcon,
  CheckIcon,
  PlayIcon,
  ClockIcon,
  DocumentIcon,
  PlusIcon,
  XCircleIcon,
  tokens,
} from '../design-system';
import AddTaskModal from './AddTaskModal';

const TreeVisualization = ({ taskTree, onTaskSelect, onRefreshTree, onDeleteSubtask }) => {
  // Track if user has manually collapsed/expanded nodes
  const [hasUserInteracted, setHasUserInteracted] = useState(false);
  
  // Initialize expanded nodes to include all nodes by default
  const [expandedNodes, setExpandedNodes] = useState(() => {
    if (!taskTree) return new Set();
    
    const allNodeIds = new Set();
    const collectNodeIds = (node) => {
      allNodeIds.add(node.task_id);
      if (node.children) {
        node.children.forEach(collectNodeIds);
      }
    };
    collectNodeIds(taskTree);
    return allNodeIds;
  });
  const [selectedNode, setSelectedNode] = useState(null);
  const [showAddTaskModal, setShowAddTaskModal] = useState(false);
  const [selectedTaskForAdd, setSelectedTaskForAdd] = useState(null);

  // Helper function to handle task selection
  const handleTaskSelect = (taskId) => {
    setSelectedNode(taskId);
    if (onTaskSelect) {
      // Find the task data for the selected task ID
      const findTask = (node) => {
        if (node.task_id === taskId) return node;
        if (node.children) {
          for (const child of node.children) {
            const found = findTask(child);
            if (found) return found;
          }
        }
        return null;
      };
      const selectedTask = taskId ? findTask(taskTree) : null;
      onTaskSelect(selectedTask);
    }
  };

  // Update expanded nodes when taskTree changes (only if user hasn't interacted)
  useEffect(() => {
    if (taskTree && !hasUserInteracted) {
      const allNodeIds = new Set();
      const collectNodeIds = (node) => {
        allNodeIds.add(node.task_id);
        if (node.children) {
          node.children.forEach(collectNodeIds);
        }
      };
      collectNodeIds(taskTree);
      setExpandedNodes(allNodeIds);
    }
  }, [taskTree, hasUserInteracted]);

  // Toggle node expansion
  const toggleNode = (nodeId) => {
    setHasUserInteracted(true);  // Mark that user has manually interacted
    const newExpanded = new Set(expandedNodes);
    if (newExpanded.has(nodeId)) {
      newExpanded.delete(nodeId);
    } else {
      newExpanded.add(nodeId);
    }
    setExpandedNodes(newExpanded);
  };

  // Expand all nodes
  const expandAll = () => {
    setHasUserInteracted(true);  // Mark that user has manually interacted
    const allNodeIds = new Set();
    const collectNodeIds = (node) => {
      allNodeIds.add(node.task_id);
      if (node.children) {
        node.children.forEach(collectNodeIds);
      }
    };
    if (taskTree) {
      collectNodeIds(taskTree);
    }
    setExpandedNodes(allNodeIds);
  };

  // Collapse all nodes
  const collapseAll = () => {
    setHasUserInteracted(true);  // Mark that user has manually interacted
    setExpandedNodes(new Set());
  };

  // Handle opening add task modal
  const handleAddTask = (targetTask) => {
    setSelectedTaskForAdd(targetTask);
    setShowAddTaskModal(true);
  };

  // Handle submitting new task
  const handleSubmitAddTask = async (taskData) => {
    try {
      const response = await fetch(`/api/tasks/${taskData.target_task_id}/add-task`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token') || 'dev-bypass-token'}`,
        },
        body: JSON.stringify({
          description: taskData.description,
          target_task_id: taskData.target_task_id,
          position: taskData.position,
          auto_decompose: taskData.auto_decompose,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to add task');
      }

      const result = await response.json();
      console.log('Task added successfully:', result);

      // Refresh the tree to show the new task
      if (onRefreshTree) {
        await onRefreshTree();
      }
      
      return result;
    } catch (error) {
      console.error('Error adding task:', error);
      throw error;
    }
  };

  // Calculate tree statistics
  const treeStats = useMemo(() => {
    if (!taskTree) return { total: 0, completed: 0, pending: 0, inProgress: 0, rejected: 0 };

    const calculateStats = (node, stats = { total: 0, completed: 0, pending: 0, inProgress: 0, rejected: 0 }) => {
      stats.total++;
      switch (node.status) {
        case 'completed':
          stats.completed++;
          break;
        case 'in_progress':
        case 'processing':
          stats.inProgress++;
          break;
        case 'rejected':
          stats.rejected++;
          break;
        default:
          stats.pending++;
      }

      if (node.children) {
        node.children.forEach(child => calculateStats(child, stats));
      }

      return stats;
    };

    return calculateStats(taskTree);
  }, [taskTree]);

  if (!taskTree) {
    return (
      <Card>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: tokens.spacing[12],
          textAlign: 'center',
        }}>
          <div>
            <DocumentIcon 
              size={48} 
              style={{ 
                color: tokens.colors.dark.border,
                marginBottom: tokens.spacing[4],
              }} 
            />
            <Text style={{
              color: tokens.colors.dark.muted,
              fontSize: tokens.typography.fontSize.lg[0],
            }}>
              No task tree available
            </Text>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: tokens.spacing[4],
    }}>
      {/* Tree Controls */}
      <Card>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: tokens.spacing[4],
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: tokens.spacing[4],
          }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.semibold,
              color: tokens.colors.dark.text,
              margin: 0,
            }}>
              Task Tree
            </Text>
            
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: tokens.spacing[2],
            }}>
              <Badge variant="secondary" size="sm">
                {treeStats.total} tasks
              </Badge>
              
              {treeStats.completed > 0 && (
                <Badge variant="success" size="sm">
                  {treeStats.completed} completed
                </Badge>
              )}
              
              {treeStats.inProgress > 0 && (
                <Badge variant="info" size="sm">
                  {treeStats.inProgress} in progress
                </Badge>
              )}
              
              {treeStats.pending > 0 && (
                <Badge variant="warning" size="sm">
                  {treeStats.pending} pending
                </Badge>
              )}
              
              {treeStats.rejected > 0 && (
                <Badge variant="error" size="sm">
                  {treeStats.rejected} rejected
                </Badge>
              )}
            </div>
          </div>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: tokens.spacing[2],
          }}>
            <Button
              variant="ghost"
              size="sm"
              onClick={expandAll}
            >
              Expand All
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={collapseAll}
            >
              Collapse All
            </Button>
          </div>
        </div>
      </Card>

      {/* Tree View */}
      <Card>
        <div style={{ 
          padding: tokens.spacing[2],
          overflow: 'hidden',
          width: '100%',
        }}>
          <TreeNode
            node={taskTree}
            level={0}
            expanded={expandedNodes.has(taskTree.task_id)}
            onToggle={() => toggleNode(taskTree.task_id)}
            selectedNode={selectedNode}
            onSelect={handleTaskSelect}
            expandedNodes={expandedNodes}
            toggleNode={toggleNode}
            onAddTask={handleAddTask}
            onDeleteSubtask={onDeleteSubtask}
          />
        </div>
      </Card>

      {/* Add Task Modal */}
      <AddTaskModal
        isOpen={showAddTaskModal}
        onClose={() => {
          setShowAddTaskModal(false);
          setSelectedTaskForAdd(null);
        }}
        targetTask={selectedTaskForAdd}
        onAddTask={handleSubmitAddTask}
      />
    </div>
  );
};

// Individual Tree Node Component
const TreeNode = ({ 
  node, 
  level, 
  expanded, 
  onToggle, 
  selectedNode,
  onSelect,
  expandedNodes,
  toggleNode,
  onAddTask,
  onDeleteSubtask
}) => {
  const hasChildren = node.children && node.children.length > 0;
  const isSelected = selectedNode === node.task_id;
  
  // Status is managed automatically by the system - no manual updates needed

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return CheckIcon;
      case 'in_progress':
      case 'processing':
        return PlayIcon;
      case 'rejected':
        return XCircleIcon;
      default:
        return ClockIcon;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return tokens.colors.success[500];
      case 'in_progress':
      case 'processing':
        return tokens.colors.info[500];
      case 'error':
      case 'failed':
      case 'rejected':
        return tokens.colors.error[500];
      default:
        return tokens.colors.warning[500];
    }
  };

  const getStatusVariant = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'in_progress':
      case 'processing':
        return 'info';
      case 'error':
      case 'failed':
      case 'rejected':
        return 'error';
      default:
        return 'warning';
    }
  };

  const StatusIcon = getStatusIcon(node.status);

  return (
    <div style={{ 
      marginLeft: level > 0 ? `${level * 24}px` : 0,
      width: level > 0 ? `calc(100% - ${level * 24}px)` : '100%',
      overflow: 'hidden',
    }}>
      {/* Node Content */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          padding: `${tokens.spacing[3]} ${tokens.spacing[3]}`,
          borderRadius: tokens.borderRadius.md,
          backgroundColor: isSelected ? `${tokens.colors.primary[500]}15` : 'transparent',
          border: isSelected ? `1px solid ${tokens.colors.primary[500]}30` : '1px solid transparent',
          marginBottom: tokens.spacing[1],
          cursor: 'pointer',
          transition: tokens.transitions.colors,
          minHeight: 'auto',
          width: '100%',
          '&:hover': {
            backgroundColor: `${tokens.colors.dark.surface}80`,
          },
        }}
        onClick={() => onSelect(isSelected ? null : node.task_id)}
      >
        {/* Expand/Collapse Button */}
        <div style={{ 
          width: '20px', 
          display: 'flex', 
          alignItems: 'flex-start', 
          justifyContent: 'center',
          paddingTop: tokens.spacing[1],
          flexShrink: 0,
        }}>
          {hasChildren ? (
            <IconButton
              icon={expanded ? ChevronDownIcon : ChevronRightIcon}
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                onToggle();
              }}
              title={expanded ? "Collapse subtasks" : "Expand subtasks"}
            />
          ) : (
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: tokens.borderRadius.full,
              backgroundColor: getStatusColor(node.status),
            }} />
          )}
        </div>

        {/* Status Icon */}
        <div style={{ 
          marginLeft: tokens.spacing[2], 
          marginRight: tokens.spacing[3],
          display: 'flex',
          alignItems: 'flex-start',
          paddingTop: tokens.spacing[1],
          flexShrink: 0,
        }}>
          <StatusIcon 
            size={16} 
            style={{ color: getStatusColor(node.status) }} 
          />
        </div>

        {/* Task Content */}
        <div style={{ 
          flex: 1, 
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: tokens.spacing[1],
        }}>
          <Text style={{
            fontSize: tokens.typography.fontSize.sm[0],
            fontWeight: tokens.typography.fontWeight.medium,
            color: tokens.colors.dark.text,
            margin: 0,
            wordWrap: 'break-word',
            overflowWrap: 'break-word',
            hyphens: 'auto',
            lineHeight: tokens.typography.lineHeight.normal,
          }}>
            {node.description}
          </Text>

          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: tokens.spacing[2],
            marginTop: tokens.spacing[1],
          }}>
            <Badge variant={getStatusVariant(node.status)} size="sm">
              {node.status.replace('_', ' ')}
            </Badge>

            {hasChildren && (
              <Badge variant="secondary" size="sm">
                {node.children.length} subtask{node.children.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>

        {/* Action buttons */}
        {level > 0 && onDeleteSubtask && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: tokens.spacing[2],
            marginLeft: tokens.spacing[3],
          }}>
            <IconButton
              icon={XCircleIcon}
              size="sm"
              variant="ghost"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(`Delete "${node.description}" and all its subtasks?`)) {
                  onDeleteSubtask(node.task_id);
                }
              }}
              title="Delete this subtask"
              style={{
                color: tokens.colors.error[500],
                '&:hover': {
                  backgroundColor: `${tokens.colors.error[500]}20`,
                },
              }}
            />
          </div>
        )}
      </div>

      {/* Task Details (when selected) */}
      {isSelected && (
        <div style={{
          marginLeft: tokens.spacing[6],
          marginBottom: tokens.spacing[3],
          padding: tokens.spacing[4],
          backgroundColor: tokens.colors.dark.surface,
          borderRadius: tokens.borderRadius.md,
          border: `1px solid ${tokens.colors.dark.border}`,
        }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: tokens.spacing[4],
          }}>
            <div>
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: tokens.colors.dark.muted,
                textTransform: 'uppercase',
                letterSpacing: tokens.typography.letterSpacing.wide,
                margin: 0,
                marginBottom: tokens.spacing[1],
              }}>
                Task ID
              </Text>
              <Text style={{
                fontSize: tokens.typography.fontSize.sm[0],
                fontFamily: tokens.typography.fontFamily.mono.join(', '),
                color: tokens.colors.dark.text,
                margin: 0,
              }}>
                {node.task_id}
              </Text>
            </div>

            {node.created_at && (
              <div>
                <Text style={{
                  fontSize: tokens.typography.fontSize.xs[0],
                  color: tokens.colors.dark.muted,
                  textTransform: 'uppercase',
                  letterSpacing: tokens.typography.letterSpacing.wide,
                  margin: 0,
                  marginBottom: tokens.spacing[1],
                }}>
                  Created
                </Text>
                <Text style={{
                  fontSize: tokens.typography.fontSize.sm[0],
                  color: tokens.colors.dark.text,
                  margin: 0,
                }}>
                  {new Date(node.created_at).toLocaleDateString()}
                </Text>
              </div>
            )}

            {node.complexity !== undefined && (
              <div>
                <Text style={{
                  fontSize: tokens.typography.fontSize.xs[0],
                  color: tokens.colors.dark.muted,
                  textTransform: 'uppercase',
                  letterSpacing: tokens.typography.letterSpacing.wide,
                  margin: 0,
                  marginBottom: tokens.spacing[1],
                }}>
                  Complexity
                </Text>
                <Text style={{
                  fontSize: tokens.typography.fontSize.sm[0],
                  color: tokens.colors.dark.text,
                  margin: 0,
                }}>
                  {node.complexity}/10
                </Text>
              </div>
            )}
          </div>

          {/* Tech Stack Information */}
          {node.context?.tech_stack && (
            <div style={{ marginTop: tokens.spacing[4] }}>
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: tokens.colors.dark.muted,
                textTransform: 'uppercase',
                letterSpacing: tokens.typography.letterSpacing.wide,
                margin: 0,
                marginBottom: tokens.spacing[2],
              }}>
                Tech Stack
              </Text>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: tokens.spacing[2],
                marginBottom: tokens.spacing[3],
              }}>
                {node.context.tech_stack.frontend && (
                  <Badge variant="info" size="sm">
                    Frontend: {typeof node.context.tech_stack.frontend === 'object' 
                      ? node.context.tech_stack.frontend.framework || JSON.stringify(node.context.tech_stack.frontend)
                      : node.context.tech_stack.frontend}
                  </Badge>
                )}
                {node.context.tech_stack.backend && (
                  <Badge variant="info" size="sm">
                    Backend: {typeof node.context.tech_stack.backend === 'object' 
                      ? node.context.tech_stack.backend.framework || node.context.tech_stack.backend.language || JSON.stringify(node.context.tech_stack.backend)
                      : node.context.tech_stack.backend}
                  </Badge>
                )}
                {node.context.tech_stack.database && (
                  <Badge variant="info" size="sm">
                    Database: {typeof node.context.tech_stack.database === 'object'
                      ? JSON.stringify(node.context.tech_stack.database)
                      : node.context.tech_stack.database}
                  </Badge>
                )}
                {node.context.tech_stack.deployment && (
                  <Badge variant="info" size="sm">
                    Deploy: {typeof node.context.tech_stack.deployment === 'object'
                      ? JSON.stringify(node.context.tech_stack.deployment)
                      : node.context.tech_stack.deployment}
                  </Badge>
                )}
              </div>
              {node.context.tech_stack.description && (
                <Text style={{
                  fontSize: tokens.typography.fontSize.sm[0],
                  color: tokens.colors.dark.muted,
                  lineHeight: tokens.typography.lineHeight.relaxed,
                  margin: 0,
                }}>
                  {node.context.tech_stack.description}
                </Text>
              )}
            </div>
          )}

          {/* Best Practices */}
          {node.context?.best_practices && node.context.best_practices.length > 0 && (
            <div style={{ marginTop: tokens.spacing[4] }}>
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: tokens.colors.dark.muted,
                textTransform: 'uppercase',
                letterSpacing: tokens.typography.letterSpacing.wide,
                margin: 0,
                marginBottom: tokens.spacing[2],
              }}>
                Best Practices
              </Text>
              <ul style={{
                margin: 0,
                paddingLeft: tokens.spacing[4],
                fontSize: tokens.typography.fontSize.sm[0],
                color: tokens.colors.dark.muted,
                lineHeight: tokens.typography.lineHeight.relaxed,
              }}>
                {node.context.best_practices.map((practice, index) => (
                  <li key={index} style={{ marginBottom: tokens.spacing[1] }}>
                    {practice}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {node.additional_context && (
            <div style={{ marginTop: tokens.spacing[4] }}>
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: tokens.colors.dark.muted,
                textTransform: 'uppercase',
                letterSpacing: tokens.typography.letterSpacing.wide,
                margin: 0,
                marginBottom: tokens.spacing[2],
              }}>
                Additional Context
              </Text>
              <Text style={{
                fontSize: tokens.typography.fontSize.sm[0],
                color: tokens.colors.dark.muted,
                lineHeight: tokens.typography.lineHeight.relaxed,
                margin: 0,
              }}>
                {node.additional_context}
              </Text>
            </div>
          )}

          {/* Task Actions */}
          {onAddTask && (
            <div style={{ 
              marginTop: tokens.spacing[4],
              paddingTop: tokens.spacing[4],
              borderTop: `1px solid ${tokens.colors.dark.border}`,
            }}>
              <Text style={{
                fontSize: tokens.typography.fontSize.xs[0],
                color: tokens.colors.dark.muted,
                textTransform: 'uppercase',
                letterSpacing: tokens.typography.letterSpacing.wide,
                margin: 0,
                marginBottom: tokens.spacing[3],
              }}>
                Actions
              </Text>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: tokens.spacing[2],
              }}>
                <Button
                  variant="ghost"
                  size="sm"
                  icon={PlusIcon}
                  onClick={(e) => {
                    e.stopPropagation();
                    onAddTask(node);
                  }}
                >
                  Add Task
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Child Nodes */}
      {hasChildren && expanded && (
        <div style={{ marginTop: tokens.spacing[1] }}>
          {node.children.map((child) => (
            <TreeNode
              key={child.task_id}
              node={child}
              level={level + 1}
              expanded={expandedNodes?.has(child.task_id) || false}
              onToggle={() => toggleNode ? toggleNode(child.task_id) : () => {}}
              selectedNode={selectedNode}
              onSelect={onSelect}
              expandedNodes={expandedNodes}
              toggleNode={toggleNode}
              onAddTask={onAddTask}
              onDeleteSubtask={onDeleteSubtask}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default TreeVisualization;