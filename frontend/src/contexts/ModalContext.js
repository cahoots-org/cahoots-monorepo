import React, { createContext, useState, useContext } from 'react';

// Create a context for managing modal stacks
const ModalContext = createContext();

export const ModalProvider = ({ children }) => {
  // Stack of tasks for modals
  const [modalStack, setModalStack] = useState([]);

  // Push a new task to the modal stack
  const pushModal = (task) => {
    setModalStack(prevStack => [...prevStack, task]);
  };

  // Pop the top task from the modal stack
  const popModal = () => {
    setModalStack(prevStack => prevStack.slice(0, -1));
  };

  // Clear the entire modal stack
  const clearModalStack = () => {
    setModalStack([]);
  };

  // Get the current task (top of the stack)
  const getCurrentTask = () => {
    return modalStack.length > 0 ? modalStack[modalStack.length - 1] : null;
  };

  // Check if the modal stack is empty
  const isModalStackEmpty = () => {
    return modalStack.length === 0;
  };

  return (
    <ModalContext.Provider value={{
      modalStack,
      pushModal,
      popModal,
      clearModalStack,
      getCurrentTask,
      isModalStackEmpty
    }}>
      {children}
    </ModalContext.Provider>
  );
};

// Custom hook to use the modal context
export const useModalStack = () => {
  const context = useContext(ModalContext);
  if (!context) {
    throw new Error('useModalStack must be used within a ModalProvider');
  }
  return context;
};
