import React from 'react';

const TaskEditForm = ({ 
  task, 
  showDecompositionTree,
  implementationDetails,
  setImplementationDetails,
  projectStandards,
  techStack,
  storyPoints,
  setStoryPoints,
  onShowToast 
}) => {

  if (!task) return null;

  return (
    <>
      {(task.is_atomic || implementationDetails) && (
        <div className="mb-6">
          <h4 className="font-medium mb-2">
            Implementation Details
            {task.is_atomic && <span className="text-xs ml-1 px-2 py-1 bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 rounded">Atomic Task</span>}
          </h4>
          <textarea
            value={implementationDetails}
            onChange={(e) => setImplementationDetails(e.target.value)}
            placeholder={task.is_atomic 
              ? "Add technical implementation details for this atomic task..." 
              : "Implementation details (auto-generated during task processing)..."
            }
            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
            style={{
              height: '160px',
              resize: 'vertical',
              minHeight: '120px',
              maxHeight: '300px'
            }}
            readOnly={!task.is_atomic && implementationDetails && implementationDetails.startsWith("Task excluded:")}
          />
          {!task.is_atomic && implementationDetails && (
            <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
              These details were auto-generated during task analysis. They will become editable when the task is marked as atomic.
            </div>
          )}
        </div>
      )}
      
      {!showDecompositionTree && (
        <>
          <div className="mb-6">
            <h4 className="font-medium mb-2">Story Points</h4>
            <div className="flex flex-col">
              <div className="flex items-center">
                <input
                  type="number"
                  min="1"
                  max="13"
                  value={storyPoints}
                  onChange={(e) => {
                    const value = parseInt(e.target.value) || 1;
                    const validValue = Math.max(1, Math.min(13, value));
                    setStoryPoints(validValue);
                  }}
                  className="w-20 p-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200"
                />
                <div className="ml-3 text-sm text-gray-500 dark:text-gray-400">
                  Fibonacci: 1, 2, 3, 5, 8, 13
                </div>
              </div>
              <div className="mt-2 flex items-center space-x-2">
                {[1, 2, 3, 5, 8, 13].map(point => (
                  <button
                    key={point}
                    type="button"
                    onClick={() => setStoryPoints(point)}
                    className={`px-2 py-1 text-xs rounded ${storyPoints === point 
                      ? 'bg-brand-vibrant-orange text-white' 
                      : 'bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-gray-300'}`}
                  >
                    {point}
                  </button>
                ))}
              </div>
              <div className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                {storyPoints !== 1 && storyPoints !== 2 && storyPoints !== 3 && 
                 storyPoints !== 5 && storyPoints !== 8 && storyPoints !== 13 && 
                 "Note: Value will be adjusted to nearest Fibonacci number when saved."}
              </div>
            </div>
          </div>
        </>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <h4 className="font-medium mb-2">Project Standards</h4>
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg max-h-60 overflow-y-auto">
            {Object.keys(projectStandards).length > 0 ? (
              <div className="text-sm">
                {Object.entries(projectStandards).map(([key, value]) => (
                  <div key={key} className="mb-2">
                    <div className="font-medium text-brand-vibrant-orange">{key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                    {typeof value === 'string' ? (
                      <div className="ml-2">{value}</div>
                    ) : Array.isArray(value) ? (
                      <ul className="ml-2 list-disc list-inside">
                        {value.map((item, index) => (
                          <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
                        ))}
                      </ul>
                    ) : typeof value === 'object' && value !== null ? (
                      <ul className="ml-2">
                        {Object.entries(value).map(([subKey, subValue]) => (
                          <li key={subKey} className="mb-1">
                            <span className="font-medium">{subKey.replace(/_/g, ' ')}:</span> {typeof subValue === 'string' ? subValue : JSON.stringify(subValue)}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div className="ml-2">{String(value)}</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400 py-2">
                No project standards defined for this task yet.
              </div>
            )}
          </div>
        </div>
        
        <div>
          <h4 className="font-medium mb-2">Tech Stack</h4>
          <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-lg max-h-60 overflow-y-auto">
            {Object.keys(techStack).length > 0 ? (
              <div className="text-sm">
                {Object.entries(techStack).map(([category, technologies]) => (
                  <div key={category} className="mb-3">
                    <div className="font-medium text-brand-vibrant-blue mb-1">{category.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                    {typeof technologies === 'object' && technologies !== null ? (
                      <div className="ml-2">
                        {Object.entries(technologies).map(([techName, techDetails]) => (
                          <div key={techName} className="mb-2">
                            <div className="font-medium">{techName}</div>
                            {typeof techDetails === 'string' ? (
                              <div className="ml-2 text-xs">{techDetails}</div>
                            ) : typeof techDetails === 'object' && techDetails !== null ? (
                              <ul className="ml-2 text-xs list-disc list-inside">
                                {Object.entries(techDetails).map(([detailKey, detailValue]) => (
                                  <li key={detailKey}>
                                    <span className="font-medium">{detailKey.replace(/_/g, ' ')}:</span> {typeof detailValue === 'string' ? detailValue : JSON.stringify(detailValue)}
                                  </li>
                                ))}
                              </ul>
                            ) : Array.isArray(techDetails) ? (
                              <ul className="ml-2 text-xs list-disc list-inside">
                                {techDetails.map((item, index) => (
                                  <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
                                ))}
                              </ul>
                            ) : (
                              <div className="ml-2 text-xs">{String(techDetails)}</div>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : Array.isArray(technologies) ? (
                      <ul className="ml-2 list-disc list-inside">
                        {technologies.map((tech, index) => (
                          <li key={index}>{typeof tech === 'string' ? tech : JSON.stringify(tech)}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className="ml-2">{String(technologies)}</div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500 dark:text-gray-400 py-2">
                No tech stack defined for this task yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
};

export default TaskEditForm;