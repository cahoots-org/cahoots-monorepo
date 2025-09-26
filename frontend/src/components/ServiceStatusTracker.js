import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import {
  Card,
  Text,
  Badge,
  LoadingSpinner,
  CheckIcon,
  ExclamationCircleIcon,
  tokens,
} from '../design-system';

const ServiceStatusTracker = ({ taskId, onStatusUpdate }) => {
  const [statusMessages, setStatusMessages] = useState([]);
  const { connected, subscribe } = useWebSocket();
  const messagesEndRef = useRef(null);

  const stageLabels = {
    source: 'Source',
    context_fetch: 'Context',
    complexity_scorer: 'Analysis',
    root_processor: 'Planning',
    decomposer: 'Decomposition',
    composer: 'Composition'
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [statusMessages]);

  useEffect(() => {
    if (!connected || !taskId) return;

    const handleServiceStatus = (event) => {
      if (event.type === 'service.status' && event.task_id === taskId) {
        const { stage, status, message, details, timestamp } = event;
        
        const newMessage = {
          id: `${taskId}-${stage}-${status}-${Date.now()}`,
          stage,
          status,
          message,
          details: details || {},
          timestamp: timestamp || new Date().toISOString(),
          receivedAt: Date.now()
        };

        setStatusMessages(prev => [...prev, newMessage]);

        // Notify parent component
        if (onStatusUpdate) {
          onStatusUpdate(stage, status, message);
        }
      }
    };

    const unsubscribe = subscribe(handleServiceStatus);
    return unsubscribe;
  }, [connected, taskId, subscribe, onStatusUpdate]);

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckIcon size={14} style={{ color: tokens.colors.success[500] }} />;
      case 'error':
        return <ExclamationCircleIcon size={14} style={{ color: tokens.colors.error[500] }} />;
      case 'started':
      case 'processing':
        return <LoadingSpinner size="xs" />;
      default:
        return null;
    }
  };

  const getStatusVariant = (status) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'error':
        return 'danger';
      case 'started':
      case 'processing':
        return 'info';
      default:
        return 'secondary';
    }
  };

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit'
    });
  };

  if (statusMessages.length === 0) {
    return (
      <Card title="Processing Status" style={{ marginBottom: tokens.spacing[6] }}>
        <Text style={{
          color: tokens.colors.dark.muted,
          fontStyle: 'italic',
          textAlign: 'center',
          margin: 0,
          padding: tokens.spacing[4]
        }}>
          Waiting for processing to begin...
        </Text>
      </Card>
    );
  }

  return (
    <Card title="Processing Status" style={{ marginBottom: tokens.spacing[6] }}>
      <div style={{
        maxHeight: '300px',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: tokens.spacing[2],
        padding: tokens.spacing[2],
      }}>
        {statusMessages.map((msg) => (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: tokens.spacing[3],
              padding: tokens.spacing[3],
              borderRadius: tokens.borderRadius.md,
              backgroundColor: tokens.colors.dark.surface,
              border: `1px solid ${tokens.colors.dark.border}`,
              transition: tokens.transitions.all,
            }}
          >
            {/* Status icon */}
            <div style={{ 
              minWidth: '14px',
              marginTop: '2px'
            }}>
              {getStatusIcon(msg.status)}
            </div>

            {/* Message content */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: tokens.spacing[2],
                marginBottom: tokens.spacing[1],
                flexWrap: 'wrap'
              }}>
                <Badge variant={getStatusVariant(msg.status)} size="sm">
                  {stageLabels[msg.stage] || msg.stage}
                </Badge>
                
                <Text style={{
                  fontSize: tokens.typography.fontSize.xs[0],
                  color: tokens.colors.dark.muted,
                  margin: 0,
                }}>
                  {formatTimestamp(msg.timestamp)}
                </Text>
              </div>

              <Text style={{
                fontSize: tokens.typography.fontSize.sm[0],
                color: tokens.colors.dark.text,
                margin: 0,
                lineHeight: tokens.typography.lineHeight.relaxed,
              }}>
                {msg.message}
              </Text>
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
    </Card>
  );
};

export default ServiceStatusTracker;