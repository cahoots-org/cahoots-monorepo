/**
 * Utility for debouncing query invalidations to prevent request flooding
 * during bulk operations like deleting tasks with many subtasks.
 */

class QueryDebouncer {
  constructor(queryClient, delay = 300) {
    this.queryClient = queryClient;
    this.delay = delay;
    this.pendingInvalidations = new Map();
    this.timers = new Map();
  }

  /**
   * Schedule a query invalidation with debouncing.
   * Multiple calls with the same key within the delay period will be batched.
   */
  invalidate(queryKey, invalidateFn) {
    const key = JSON.stringify(queryKey);
    
    // Clear existing timer for this key
    if (this.timers.has(key)) {
      clearTimeout(this.timers.get(key));
    }
    
    // Store the invalidation function
    this.pendingInvalidations.set(key, invalidateFn);
    
    // Set a new timer
    const timer = setTimeout(() => {
      const fn = this.pendingInvalidations.get(key);
      if (fn) {
        fn();
        this.pendingInvalidations.delete(key);
      }
      this.timers.delete(key);
    }, this.delay);
    
    this.timers.set(key, timer);
  }

  /**
   * Immediately execute all pending invalidations and clear timers.
   */
  flush() {
    // Clear all timers
    this.timers.forEach(timer => clearTimeout(timer));
    this.timers.clear();
    
    // Execute all pending invalidations
    this.pendingInvalidations.forEach(fn => fn());
    this.pendingInvalidations.clear();
  }

  /**
   * Cancel all pending invalidations without executing them.
   */
  cancel() {
    this.timers.forEach(timer => clearTimeout(timer));
    this.timers.clear();
    this.pendingInvalidations.clear();
  }

  /**
   * Check if there are pending invalidations.
   */
  hasPending() {
    return this.pendingInvalidations.size > 0;
  }
}

// Create a singleton instance that can be shared across the app
let debouncerInstance = null;

export function getQueryDebouncer(queryClient, delay = 300) {
  if (!debouncerInstance) {
    debouncerInstance = new QueryDebouncer(queryClient, delay);
  }
  return debouncerInstance;
}

export function resetQueryDebouncer() {
  if (debouncerInstance) {
    debouncerInstance.cancel();
    debouncerInstance = null;
  }
}

export default QueryDebouncer;