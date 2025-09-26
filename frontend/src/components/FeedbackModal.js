import React, { useState } from 'react';

const FeedbackModal = ({ modalObject, onClose }) => {
  const [rating, setRating] = useState(0.5);
  const [comments, setComments] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const decisionType = modalObject?.decision_type || 'atomicity';
  const prediction = modalObject?.prediction || {};

  const handleSubmit = async () => {
    if (!modalObject?.onSubmit) return;
    
    setIsSubmitting(true);
    try {
      await modalObject.onSubmit({
        rating: rating,
        comments: comments,
        decision_type: decisionType
      });
      onClose(false);
    } catch (error) {
      console.error('Error submitting feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold">Provide Feedback</h2>
        <button 
          onClick={() => onClose(false)} 
          className="text-gray-500 hover:text-gray-700"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      
      <div className="mb-4">
        <h3 className="font-medium mb-2">Task: {modalObject?.description?.substring(0, 100)}...</h3>
      </div>
      
      {/* Display prediction information */}
      <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-md">
        <h4 className="font-medium mb-2">AI Prediction</h4>
        <div className="text-sm">
          <p><span className="font-medium">Decision Type:</span> {decisionType}</p>
          <p><span className="font-medium">Predicted Value:</span> {prediction.predicted_value !== undefined ? 
            (typeof prediction.predicted_value === 'boolean' ? 
              (prediction.predicted_value ? 'True' : 'False') : 
              JSON.stringify(prediction.predicted_value)
            ) : 'N/A'}
          </p>
          <p><span className="font-medium">Confidence:</span> {prediction.confidence_score !== undefined ? 
            `${(prediction.confidence_score * 100).toFixed(1)}%` : 'N/A'}
          </p>
          <p className="text-xs text-gray-500 mt-2">Your feedback helps improve our AI task decomposition system</p>
        </div>
      </div>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            How would you rate this decomposition? (0 = Poor, 1 = Excellent)
          </label>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={rating}
            onChange={(e) => setRating(parseFloat(e.target.value))}
            className="w-full"
          />
          <div className="text-center text-sm text-gray-600 dark:text-gray-400 mt-1">
            {rating.toFixed(1)}
          </div>
        </div>
        
        <div>
          <label className="block text-sm font-medium mb-2">Comments (optional)</label>
          <textarea
            value={comments}
            onChange={(e) => setComments(e.target.value)}
            className="w-full p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-white rounded-md"
            rows="3"
            placeholder="Any specific feedback on the task decomposition..."
          />
        </div>
        
        <div className="flex justify-end space-x-2">
          <button 
            onClick={() => onClose(false)}
            className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
          >
            Cancel
          </button>
          <button 
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Feedback'}
          </button>
        </div>
      </div>
    </>
  );
};

export default FeedbackModal;