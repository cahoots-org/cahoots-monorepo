// Redesigned Dashboard - Professional replacement using design system and React Query
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Card,
  Button,
  Heading1,
  Heading2,
  Text,
  Progress,
  PlusIcon,
  HomeIcon,
  tokens,
} from '../design-system';
import { useTasks, useTaskStats } from '../hooks/api/useTasks';
import { useApp } from '../contexts/AppContext';
import TaskCard from '../components/TaskCard';

const Dashboard = () => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(9); // 3x3 grid
  const [isMobileMain, setIsMobileMain] = useState(window.innerWidth < 768);
  const { showError } = useApp();

  useEffect(() => {
    const handleResize = () => setIsMobileMain(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Fetch data using React Query hooks
  const {
    data: tasksData,
    isLoading: tasksLoading,
    error: tasksError,
    isError: hasTasksError,
  } = useTasks({ page: currentPage, pageSize, topLevelOnly: true });

  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useTaskStats(true);

  // Handle pagination
  const handlePageChange = (newPage) => {
    setCurrentPage(newPage);
  };

  // Handle automatic navigation when current page becomes empty after deletion
  useEffect(() => {
    // Only act if we have valid task data and we're not on the first page
    if (tasksData && currentPage > 1) {
      // If current page is empty but there are still total tasks, navigate to previous page
      if (!tasksData.items?.length && tasksData.total > 0) {
        const newPage = Math.max(currentPage - 1, 1);
        setCurrentPage(newPage);
      }
    }
  }, [tasksData, currentPage]);

  // Compact Statistics Component for Dashboard
  const CompactStats = ({ stats }) => {
    const completionRate = stats?.total > 0 
      ? Math.round((stats.completed / stats.total) * 100) 
      : 0;

    const [isMobile, setIsMobile] = useState(false);

    useEffect(() => {
      // Set initial value
      setIsMobile(window.innerWidth < 768);
      
      const handleResize = () => setIsMobile(window.innerWidth < 768);
      window.addEventListener('resize', handleResize);
      return () => window.removeEventListener('resize', handleResize);
    }, []);

    return (
      <Card>
        <div 
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile 
              ? 'repeat(2, 1fr)'  // 2 columns on mobile
              : 'repeat(auto-fit, minmax(100px, 1fr))',
            gap: isMobile ? tokens.spacing[2] : tokens.spacing[3],
            padding: isMobile ? tokens.spacing[2] : tokens.spacing[3],
            marginBottom: isMobile ? tokens.spacing[2] : tokens.spacing[4],
          }}
          className="compact-stats"
        >
          {/* Total Tasks */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{
              fontSize: isMobile 
                ? (tokens?.typography?.fontSize?.sm?.[0] || '0.875rem')
                : (tokens?.typography?.fontSize?.lg?.[0] || '1.125rem'),
              fontWeight: tokens.typography.fontWeight.bold,
              color: tokens.colors.primary[500],
              margin: 0,
            }}>
              {stats?.total || 0}
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Total
            </Text>
          </div>

          {/* Completed */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.bold,
              color: tokens.colors.success[500],
              margin: 0,
            }}>
              {stats?.completed || 0}
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Done
            </Text>
          </div>

          {/* In Progress */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.bold,
              color: tokens.colors.warning[500],
              margin: 0,
            }}>
              {stats?.inProgress || 0}
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Active
            </Text>
          </div>

          {/* Pending */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.bold,
              color: tokens.colors.info[500],
              margin: 0,
            }}>
              {stats?.pending || 0}
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Pending
            </Text>
          </div>

          {/* Rejected */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.bold,
              color: tokens.colors.error[500],
              margin: 0,
            }}>
              {stats?.rejected || 0}
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Rejected
            </Text>
          </div>

          {/* Progress Percentage */}
          <div style={{ textAlign: 'center' }}>
            <Text style={{
              fontSize: tokens.typography.fontSize.lg[0],
              fontWeight: tokens.typography.fontWeight.bold,
              color: completionRate === 100 ? tokens.colors.success[500] : tokens.colors.primary[400],
              margin: 0,
            }}>
              {completionRate}%
            </Text>
            <Text style={{
              fontSize: tokens.typography.fontSize.xs[0],
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Complete
            </Text>
          </div>

          {/* Progress Bar - Spans full width */}
          <div style={{
            gridColumn: '1 / -1',
            marginTop: isMobile ? tokens.spacing[2] : tokens.spacing[1],
            padding: isMobile ? `0 ${tokens.spacing[1]}` : 0,
          }}>
            <Progress
              value={completionRate}
              variant={completionRate === 100 ? 'success' : 'primary'}
              style={{ height: isMobile ? '2px' : '3px' }}
            />
          </div>
        </div>
      </Card>
    );
  };

  // Loading state
  if (tasksLoading || statsLoading) {
    return (
      <div className="container" style={{ paddingTop: tokens.spacing[6] }}>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          minHeight: '50vh',
          flexDirection: 'column',
          gap: tokens.spacing[4],
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            border: `4px solid ${tokens.colors.dark.border}`,
            borderTop: `4px solid ${tokens.colors.primary[500]}`,
            borderRadius: tokens.borderRadius.full,
            animation: 'spin 1s linear infinite',
          }} />
          <Text style={{ color: tokens.colors.dark.muted }}>
            Loading dashboard...
          </Text>
        </div>
      </div>
    );
  }

  // Error state
  if (hasTasksError || statsError) {
    showError(tasksError?.message || statsError?.message || 'Failed to load dashboard');
  }

  // Empty state
  const isEmpty = !tasksData?.items?.length;

  return (
    <div className="container" style={{ paddingTop: tokens.spacing[6] }}>
      {/* Header */}
      <header style={{ marginBottom: isMobileMain ? tokens.spacing[6] : tokens.spacing[8] }}>
        <div style={{ 
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: tokens.spacing[2],
          flexWrap: 'wrap',
          gap: tokens.spacing[3],
        }}>
          <div>
            <Heading1 style={{ 
              margin: 0,
              fontSize: isMobileMain ? tokens.typography.fontSize['2xl'][0] : undefined,
              color: tokens.colors.primary[500],
            }}>
              Dashboard
            </Heading1>
            {!isMobileMain && (
              <Text style={{ 
                color: tokens.colors.dark.muted,
                marginTop: tokens.spacing[1],
                margin: 0,
              }}>
                Manage your AI-powered task decomposition projects
              </Text>
            )}
          </div>
          
          <Link to="/tasks/create">
            <Button 
              variant="primary" 
              size={isMobileMain ? "md" : "lg"} 
              icon={PlusIcon}
            >
              {isMobileMain ? 'New Task' : 'Create New Task'}
            </Button>
          </Link>
        </div>
      </header>

      {/* Compact Statistics */}
      <section style={{ marginBottom: tokens.spacing[8] }}>
        <CompactStats stats={stats} />
      </section>


      {/* Tasks Section */}
      <section>
        <div style={{ 
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: tokens.spacing[6],
        }}>
          <Heading2>Recent Tasks</Heading2>
          {!isEmpty && (
            <Text style={{ 
              color: tokens.colors.dark.muted,
              margin: 0,
            }}>
              Showing {tasksData.items.length} of {tasksData.total} tasks
            </Text>
          )}
        </div>

        {isEmpty ? (
          // Empty State
          <Card padding="lg" style={{ textAlign: 'center' }}>
            <div style={{ 
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: tokens.spacing[8],
            }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: tokens.borderRadius.full,
                backgroundColor: `${tokens.colors.primary[500]}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: tokens.spacing[4],
              }}>
                <HomeIcon size={32} style={{ color: tokens.colors.primary[500] }} />
              </div>
              
              <Heading2 style={{ marginBottom: tokens.spacing[2] }}>
                Welcome to Cahoots!
              </Heading2>
              
              <Text style={{ 
                color: tokens.colors.dark.muted,
                marginBottom: tokens.spacing[6],
                maxWidth: '400px',
              }}>
                Start your AI collaboration journey by creating your first task. 
                Our intelligent system will help decompose complex projects into manageable subtasks.
              </Text>
              
              <Link to="/tasks/create">
                <Button variant="primary" size="lg" icon={PlusIcon}>
                  Create Your First Task
                </Button>
              </Link>
            </div>
          </Card>
        ) : (
          // Tasks Grid
          <>
            <div style={{ 
              display: 'grid',
              gridTemplateColumns: isMobileMain 
                ? '1fr'  // Single column on mobile
                : 'repeat(auto-fill, minmax(350px, 1fr))',
              gap: isMobileMain ? tokens.spacing[4] : tokens.spacing[6],
              marginBottom: tokens.spacing[8],
            }}>
              {tasksData.items.map((task) => (
                <div key={task.task_id} className="fade-in">
                  <TaskCard 
                    task={task} 
                    navigateOnClick={true}
                    variant="elevated"
                  />
                </div>
              ))}
            </div>

            {/* Pagination */}
            {tasksData.totalPages > 1 && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: tokens.spacing[2],
                marginTop: tokens.spacing[8],
              }}>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage === 1}
                  onClick={() => handlePageChange(Math.max(currentPage - 1, 1))}
                >
                  Previous
                </Button>
                
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: tokens.spacing[1] 
                }}>
                  {Array.from({ length: Math.min(5, tasksData.totalPages) }, (_, i) => {
                    let pageNum;
                    if (tasksData.totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= tasksData.totalPages - 2) {
                      pageNum = tasksData.totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <Button
                        key={pageNum}
                        variant={currentPage === pageNum ? 'primary' : 'secondary'}
                        size="sm"
                        onClick={() => handlePageChange(pageNum)}
                        style={{ minWidth: '40px' }}
                      >
                        {pageNum}
                      </Button>
                    );
                  })}
                </div>
                
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={currentPage === tasksData.totalPages}
                  onClick={() => handlePageChange(Math.min(currentPage + 1, tasksData.totalPages))}
                >
                  Next
                </Button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
};

export default Dashboard;