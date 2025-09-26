// Date utility functions for consistent formatting across components

/**
 * Format a date string for display, showing time for today's dates
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date string
 */
export const formatTaskDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffInDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  
  if (diffInDays === 0) {
    // For today's tasks, show time to distinguish them
    const timeString = date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
    return `Today ${timeString}`;
  }
  
  if (diffInDays === 1) return 'Yesterday';
  if (diffInDays < 7) return `${diffInDays} days ago`;
  
  return date.toLocaleDateString();
};

/**
 * Format a date string for display in detailed views
 * @param {string} dateString - ISO date string
 * @returns {string} Formatted date and time string
 */
export const formatDetailedDate = (dateString) => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffInDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));
  
  if (diffInDays === 0) {
    const timeString = date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
    return `Today at ${timeString}`;
  }
  
  if (diffInDays === 1) {
    const timeString = date.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
    return `Yesterday at ${timeString}`;
  }
  
  // For older dates, show both date and time
  return date.toLocaleDateString() + ' at ' + date.toLocaleTimeString([], { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
};