/**
 * Centralized error handling service for API operations
 */

/**
 * Standard error response format
 */
export const ErrorTypes = {
  NETWORK: 'NETWORK_ERROR',
  AUTHENTICATION: 'AUTH_ERROR', 
  AUTHORIZATION: 'PERMISSION_ERROR',
  VALIDATION: 'VALIDATION_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  SERVER: 'SERVER_ERROR',
  UNKNOWN: 'UNKNOWN_ERROR'
};

/**
 * Extract error information from API response
 */
export const parseApiError = (error) => {
  if (!error.response) {
    return {
      type: ErrorTypes.NETWORK,
      message: 'Network connection failed. Please check your internet connection.',
      details: error.message,
      status: null
    };
  }

  const { status, data } = error.response;
  let type = ErrorTypes.UNKNOWN;
  let message = 'An unexpected error occurred. Please try again.';

  switch (status) {
    case 400:
      type = ErrorTypes.VALIDATION;
      message = data?.detail || 'Invalid request. Please check your input.';
      break;
    case 401:
      type = ErrorTypes.AUTHENTICATION;
      message = 'Authentication required. Please log in again.';
      break;
    case 403:
      type = ErrorTypes.AUTHORIZATION;
      message = 'You do not have permission to perform this action.';
      break;
    case 404:
      type = ErrorTypes.NOT_FOUND;
      message = data?.detail || 'The requested resource was not found.';
      break;
    case 422:
      type = ErrorTypes.VALIDATION;
      message = data?.detail || 'Validation failed. Please check your input.';
      break;
    case 500:
      type = ErrorTypes.SERVER;
      message = 'Server error. Please try again later.';
      break;
    default:
      if (status >= 500) {
        type = ErrorTypes.SERVER;
        message = 'Server error. Please try again later.';
      }
  }

  return {
    type,
    message,
    details: data?.detail || data?.message,
    status,
    validationErrors: data?.errors || null
  };
};

/**
 * Display error to user based on error type
 */
export const handleApiError = (error, options = {}) => {
  const { 
    showAlert = true, 
    customMessages = {}, 
    onAuthError = null,
    onValidationError = null 
  } = options;

  const parsedError = parseApiError(error);
  const displayMessage = customMessages[parsedError.type] || parsedError.message;

  // Log error for debugging
  console.error('API Error:', {
    type: parsedError.type,
    status: parsedError.status,
    message: parsedError.message,
    details: parsedError.details,
    originalError: error
  });

  // Handle specific error types
  switch (parsedError.type) {
    case ErrorTypes.AUTHENTICATION:
      if (onAuthError) {
        onAuthError(parsedError);
      } else {
        // Clear local storage and redirect to login
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        // Use React Router for safe navigation
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
      break;

    case ErrorTypes.VALIDATION:
      if (onValidationError) {
        onValidationError(parsedError);
      }
      break;

    default:
      // No special handling for other error types
      break;
  }

  // Log error for debugging (alert removed - components should handle user notifications)
  if (showAlert && parsedError.type !== ErrorTypes.AUTHENTICATION) {
    console.error('User Error:', displayMessage);
    // Note: Components using withErrorHandling should implement their own toast notifications
    // for user-facing error display. This service focuses on error parsing and logging.
  }

  return parsedError;
};

/**
 * Wrapper for API calls with standardized error handling
 */
export const withErrorHandling = async (apiCall, options = {}) => {
  try {
    const response = await apiCall();
    return { data: response.data, error: null };
  } catch (error) {
    const parsedError = handleApiError(error, options);
    return { data: null, error: parsedError };
  }
};

/**
 * Format validation errors for display
 */
export const formatValidationErrors = (validationErrors) => {
  if (!validationErrors || !Array.isArray(validationErrors)) {
    return '';
  }

  return validationErrors
    .map(err => `${err.field}: ${err.message}`)
    .join('\n');
};