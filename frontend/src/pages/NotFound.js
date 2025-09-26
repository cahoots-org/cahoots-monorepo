import React from 'react';
import { Link } from 'react-router-dom';

const NotFound = () => {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <h1 className="text-6xl font-bold text-primary-600">404</h1>
      <h2 className="mt-2 text-2xl font-semibold text-secondary-800">Page Not Found</h2>
      <p className="mt-4 text-secondary-600 text-center max-w-md">
        The page you are looking for might have been removed, had its name changed, or is temporarily unavailable.
      </p>
      <Link to="/" className="mt-8 btn btn-primary">
        Return to Dashboard
      </Link>
    </div>
  );
};

export default NotFound; 