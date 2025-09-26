import React from 'react';
import { Helmet } from 'react-helmet-async';
import { useLocation } from 'react-router-dom';

const SEO = ({ 
  title, 
  description, 
  image, 
  article = false,
  author,
  publishedTime,
  tags = []
}) => {
  const location = useLocation();
  const siteUrl = 'https://cahoots.cc';
  const currentUrl = `${siteUrl}${location.pathname}`;
  
  // Default values
  const defaultTitle = 'Cahoots Project Manager';
  const defaultDescription = 'Transform complex software projects into manageable tasks with AI-powered decomposition. Cahoots helps teams break down requirements into atomic, actionable work items.';
  const defaultImage = `${siteUrl}/text-logo.png`;
  
  const seoTitle = title ? `${title} | ${defaultTitle}` : defaultTitle;
  const seoDescription = description || defaultDescription;
  const seoImage = image || defaultImage;
  
  // Structured data for articles
  const articleStructuredData = article ? {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: title,
    description: seoDescription,
    image: seoImage,
    author: {
      '@type': 'Person',
      name: author || 'Cahoots Team'
    },
    publisher: {
      '@type': 'Organization',
      name: 'Cahoots',
      logo: {
        '@type': 'ImageObject',
        url: defaultImage
      }
    },
    datePublished: publishedTime,
    keywords: tags.join(', '),
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': currentUrl
    }
  } : null;
  
  // Organization structured data
  const organizationStructuredData = {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Cahoots',
    url: siteUrl,
    logo: defaultImage,
    sameAs: [
      'https://github.com/cahoots-org'
    ]
  };
  
  return (
    <Helmet>
      {/* Primary Meta Tags */}
      <title>{seoTitle}</title>
      <meta name="title" content={seoTitle} />
      <meta name="description" content={seoDescription} />
      <link rel="canonical" href={currentUrl} />
      
      {/* Open Graph / Facebook */}
      <meta property="og:type" content={article ? 'article' : 'website'} />
      <meta property="og:url" content={currentUrl} />
      <meta property="og:title" content={seoTitle} />
      <meta property="og:description" content={seoDescription} />
      <meta property="og:image" content={seoImage} />
      <meta property="og:site_name" content="Cahoots" />
      
      {/* Twitter */}
      <meta property="twitter:card" content="summary_large_image" />
      <meta property="twitter:url" content={currentUrl} />
      <meta property="twitter:title" content={seoTitle} />
      <meta property="twitter:description" content={seoDescription} />
      <meta property="twitter:image" content={seoImage} />
      
      {/* Article specific tags */}
      {article && author && (
        <meta property="article:author" content={author} />
      )}
      {article && publishedTime && (
        <meta property="article:published_time" content={publishedTime} />
      )}
      {article && tags.length > 0 && tags.map((tag, index) => (
        <meta key={index} property="article:tag" content={tag} />
      ))}
      
      {/* Structured Data */}
      {articleStructuredData && (
        <script type="application/ld+json">
          {JSON.stringify(articleStructuredData)}
        </script>
      )}
      {!article && location.pathname === '/' && (
        <script type="application/ld+json">
          {JSON.stringify(organizationStructuredData)}
        </script>
      )}
    </Helmet>
  );
};

export default SEO;