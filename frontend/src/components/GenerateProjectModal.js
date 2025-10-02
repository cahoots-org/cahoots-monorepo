import React, { useState } from 'react';
import { Button } from '../design-system';
import { useSettings } from '../contexts/SettingsContext';

const GenerateProjectModal = ({
  task,
  onShowToast
}) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const { settings } = useSettings();

  const hasGithubIntegration = settings?.githubIntegration?.accessToken;

  const handleDownloadZip = async () => {
    if (!task) return;

    setIsGenerating(true);
    setIsDropdownOpen(false);

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/tasks/${task.task_id}/generate-project`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          format: 'zip'
        })
      });

      if (!response.ok) {
        throw new Error('Failed to generate project');
      }

      // Get the blob from the response
      const blob = await response.blob();

      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${task.description.split('\n')[0].substring(0, 30).replace(/[^a-zA-Z0-9]/g, '-')}-project.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      onShowToast?.('Project generated and downloaded successfully!', 'success');
    } catch (error) {
      console.error('Error generating project:', error);
      onShowToast?.('Failed to generate project. Please try again.', 'error');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleGithubRepository = () => {
    setIsDropdownOpen(false);
    onShowToast?.('GitHub repository creation will be available soon!', 'info');
  };

  return (
    <div className="relative inline-block text-left">
      <div>
        <Button
          variant="outline"
          size="sm"
          onClick={(e) => {
            e.preventDefault();
            setIsDropdownOpen(!isDropdownOpen);
          }}
          disabled={isGenerating}
          aria-expanded={isDropdownOpen}
          aria-haspopup="true"
        >
          {isGenerating ? 'Generating...' : 'Generate Project'}
        </Button>
      </div>
      {isDropdownOpen && (
        <div
          className="origin-top-right absolute right-0 mt-2 w-64 rounded-md shadow-lg bg-white dark:bg-gray-700 ring-1 ring-black ring-opacity-5 focus:outline-none z-50"
          role="menu"
          aria-orientation="vertical"
          tabIndex="-1"
        >
          <div className="py-1" role="none">
            <button
              className="text-gray-700 dark:text-gray-200 block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600"
              role="menuitem"
              tabIndex="-1"
              onClick={handleDownloadZip}
            >
              📦 Download ZIP
            </button>
            <button
              className={`${!hasGithubIntegration ? 'opacity-50 cursor-not-allowed' : ''} text-gray-700 dark:text-gray-200 block w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600`}
              role="menuitem"
              tabIndex="-1"
              onClick={() => {
                if (hasGithubIntegration) {
                  handleGithubRepository();
                }
              }}
              title={!hasGithubIntegration ? "Requires GitHub integration setup in Settings" : "Coming Soon"}
            >
              🐙 GitHub Repository {!hasGithubIntegration && '(Setup Required)'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default GenerateProjectModal;
