import { useState, useEffect, useRef } from 'react';

// Toast configuration constants
const TOAST_DURATION_MS = 5000;

export const useToast = () => {
  const [toastMessage, setToastMessage] = useState('');
  const [isToastVisible, setIsToastVisible] = useState(false);
  const [toastStatus, setToastStatus] = useState('success'); // 'success', 'error', 'warning', 'info'
  const timeoutRef = useRef(null);
  const isMountedRef = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Helper function to show toast messages
  const showToast = (message, status = 'success') => {
    if (!isMountedRef.current) return;
    
    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    
    setToastMessage(message);
    setToastStatus(status);
    setIsToastVisible(true);
    
    // Set new timeout with cleanup
    timeoutRef.current = setTimeout(() => {
      if (isMountedRef.current) {
        setIsToastVisible(false);
      }
    }, TOAST_DURATION_MS);
  };

  // Toast JSX component with dark theme styling
  const ToastComponent = () => (
    isToastVisible && (
      <div 
        style={{
          position: 'fixed',
          bottom: '1rem',
          right: '1rem',
          padding: '1rem',
          borderRadius: '0.5rem',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          zIndex: 1000,
          color: '#ffffff',
          fontSize: '0.875rem',
          minWidth: '200px',
          maxWidth: '400px',
          border: '1px solid',
          backgroundColor: 
            toastStatus === 'success' ? '#064E3B' : 
            toastStatus === 'error' ? '#7F1D1D' : 
            toastStatus === 'warning' ? '#92400E' : '#1E3A8A',
          borderColor:
            toastStatus === 'success' ? '#059669' : 
            toastStatus === 'error' ? '#B91C1C' : 
            toastStatus === 'warning' ? '#D97706' : '#2563EB',
        }}
      >
        {toastMessage}
      </div>
    )
  );

  return {
    showToast,
    ToastComponent
  };
};