import React from 'react';

const CottageIcon = ({ size = 'text-3xl', className = '' }) => {
  // Convert Tailwind text sizes to pixel values for the image
  const sizeMap = {
    'text-2xl': '32px',
    'text-3xl': '48px', 
    'text-6xl': '96px'
  };
  
  const pixelSize = sizeMap[size] || '48px';
  
  return (
    <img 
      src="/icons/cottage.png" 
      alt="Cahoots Cottage" 
      style={{ width: pixelSize, height: pixelSize }}
      className={`mx-auto ${className}`}
    />
  );
};

export default CottageIcon;
