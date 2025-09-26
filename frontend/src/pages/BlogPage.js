import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { BellIcon } from '@heroicons/react/24/solid';
import apiClient from '../services/unifiedApiClient';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import Button from '../design-system/components/Button';
import Card from '../design-system/components/Card';
import Input from '../design-system/components/Input';
import Badge from '../design-system/components/Badge';
import LoadingSpinner from '../design-system/components/LoadingSpinner';
import EmptyState from '../design-system/components/EmptyState';
import { Heading1, Heading3, Text, TextSmall, TextLarge } from '../design-system/components/Typography';
import { tokens } from '../design-system/tokens';
import DOMPurify from 'dompurify';
import SEO from '../components/SEO';
import BlogSubscription from '../components/BlogSubscription';
import '../styles/BlogContent.css';

const BlogPostCard = ({ post, onClick }) => (
  <Card 
    onClick={onClick}
    style={{ cursor: 'pointer', marginBottom: tokens.spacing[4] }}
  >
    {post.featured_image && (
      <img
        src={post.featured_image}
        alt={post.title}
        style={{
          width: '100%',
          height: '200px',
          objectFit: 'cover',
          marginBottom: tokens.spacing[4],
          borderRadius: tokens.borderRadius.md,
        }}
      />
    )}
    <Heading3 style={{ marginBottom: tokens.spacing[2] }}>
      {post.title}
    </Heading3>
    <div style={{ 
      display: 'flex', 
      gap: tokens.spacing[2], 
      marginBottom: tokens.spacing[3],
      color: tokens.colors.dark.textMuted 
    }}>
      <TextSmall>By {post.author_name}</TextSmall>
      <TextSmall>•</TextSmall>
      <TextSmall>
        {new Date(post.published_at || post.created_at).toLocaleDateString()}
      </TextSmall>
    </div>
    <Text style={{ marginBottom: tokens.spacing[3] }}>
      {post.excerpt || post.content.replace(/<[^>]*>/g, '').substring(0, 150)}...
    </Text>
    {post.tags && post.tags.length > 0 && (
      <div style={{ display: 'flex', gap: tokens.spacing[2], flexWrap: 'wrap' }}>
        {post.tags.slice(0, 3).map(tag => (
          <Badge key={tag} variant="info">{tag}</Badge>
        ))}
      </div>
    )}
  </Card>
);

const BlogPostDetail = ({ post, onBack }) => (
  <div style={{ maxWidth: '800px', margin: '0 auto', padding: tokens.spacing[6] }}>
    <SEO 
      title={post.title}
      description={post.excerpt || post.content.replace(/<[^>]*>/g, '').substring(0, 160)}
      image={post.featured_image}
      article={true}
      author={post.author_name}
      publishedTime={post.published_at || post.created_at}
      tags={post.tags || []}
    />
    <Button onClick={onBack} variant="ghost" style={{ marginBottom: tokens.spacing[6] }}>
      ← Back to Blog
    </Button>
    
    <Card>
      {post.featured_image && (
        <img
          src={post.featured_image}
          alt={post.title}
          style={{
            width: '100%',
            maxHeight: '400px',
            objectFit: 'cover',
            marginBottom: tokens.spacing[6],
            borderRadius: tokens.borderRadius.md,
          }}
        />
      )}
      
      <Heading1 style={{ marginBottom: tokens.spacing[4] }}>
        {post.title}
      </Heading1>
      
      <div style={{ 
        display: 'flex', 
        gap: tokens.spacing[3], 
        marginBottom: tokens.spacing[4],
        color: tokens.colors.dark.textMuted 
      }}>
        <Text>By {post.author_name}</Text>
        <Text>•</Text>
        <Text>
          {new Date(post.published_at || post.created_at).toLocaleDateString()}
        </Text>
        <Text>•</Text>
        <Text>{post.view_count} views</Text>
      </div>
      
      {post.tags && post.tags.length > 0 && (
        <div style={{ 
          display: 'flex', 
          gap: tokens.spacing[2], 
          flexWrap: 'wrap',
          marginBottom: tokens.spacing[6]
        }}>
          {post.tags.map(tag => (
            <Badge key={tag} variant="info">{tag}</Badge>
          ))}
        </div>
      )}
      
      <div
        className="blog-content"
        dangerouslySetInnerHTML={{
          __html: DOMPurify.sanitize(post.content)
        }}
        style={{
          fontSize: tokens.typography.fontSize.base[0],
          lineHeight: '1.8',
          color: tokens.colors.dark.text,
        }}
      />
      
      {/* Blog Subscription Component */}
      <BlogSubscription 
        title="Enjoyed this article?"
        variant="inline"
      />
    </Card>
  </div>
);

const BlogPage = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedPost, setSelectedPost] = useState(null);
  const [mySubscription, setMySubscription] = useState(null);
  
  const { showToast, ToastComponent } = useToast();
  const navigate = useNavigate();
  const { slug } = useParams();
  const { user } = useAuth();

  useEffect(() => {
    if (slug) {
      fetchPostBySlug(slug);
    } else {
      fetchPosts();
    }
    
    if (user) {
      fetchMySubscription();
    }
  }, [slug, user]);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      const params = {};
      if (search) params.search = search;
      
      const response = await apiClient.get('/blog/posts', { params });
      setPosts(response.posts || []);
    } catch (error) {
      showToast('Failed to fetch blog posts', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchPostBySlug = async (postSlug) => {
    try {
      setLoading(true);
      const post = await apiClient.get(`/blog/posts/${postSlug}`);
      setSelectedPost(post);
    } catch (error) {
      showToast('Failed to fetch blog post', 'error');
      navigate('/blog');
    } finally {
      setLoading(false);
    }
  };

  const fetchMySubscription = async () => {
    try {
      const subscription = await apiClient.get('/blog/my-subscription');
      setMySubscription(subscription);
    } catch (error) {
      // User doesn't have a subscription
    }
  };

  const handleSearch = () => {
    fetchPosts();
  };

  const handlePostClick = (post) => {
    navigate(`/blog/${post.slug}`);
  };

  const handleBackToBlog = () => {
    navigate('/blog');
    setSelectedPost(null);
  };

  const handleToggleSubscription = async () => {
    if (!user) {
      showToast('Please sign in to subscribe', 'info');
      return;
    }
    
    try {
      if (mySubscription) {
        // Unsubscribe
        if (window.confirm('Are you sure you want to unsubscribe from blog notifications?')) {
          await apiClient.delete('/blog/my-subscription');
          showToast('Successfully unsubscribed', 'success');
          setMySubscription(null);
        }
      } else {
        // Subscribe with default settings
        const data = {
          email: user.email,
          frequency: 'weekly',  // Default to weekly
          categories: [],
        };
        
        await apiClient.post('/blog/subscribe', data);
        showToast('Successfully subscribed! You\'ll receive weekly updates.', 'success');
        fetchMySubscription();
      }
    } catch (error) {
      showToast(error.response?.data?.detail || 'Failed to update subscription', 'error');
    }
  };


  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        minHeight: '100vh' 
      }}>
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (selectedPost) {
    return <BlogPostDetail post={selectedPost} onBack={handleBackToBlog} />;
  }

  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: tokens.colors.dark.bg,
      padding: tokens.spacing[6]
    }}>
      <SEO 
        title="Blog"
        description="Read the latest insights, updates, and tutorials from the Cahoots team about AI-powered project management and task decomposition."
      />
      <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ textAlign: 'center', marginBottom: tokens.spacing[8] }}>
          <Heading1 style={{ marginBottom: tokens.spacing[3] }}>
            Blog
          </Heading1>
          <TextLarge style={{ color: tokens.colors.dark.textMuted }}>
            Insights, updates, and tutorials from the Cahoots team
          </TextLarge>
        </div>

        {/* Search and Subscribe */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          marginBottom: tokens.spacing[8],
          flexWrap: 'wrap',
          gap: tokens.spacing[4]
        }}>
          <div style={{ display: 'flex', gap: tokens.spacing[2], flex: 1, maxWidth: '400px' }}>
            <Input
              placeholder="Search posts..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            />
            <Button onClick={handleSearch} variant="secondary">
              Search
            </Button>
          </div>
          
          <Button
            onClick={handleToggleSubscription}
            icon={BellIcon}
            variant={mySubscription ? 'secondary' : 'primary'}
          >
            {mySubscription ? 'Subscribed' : 'Subscribe'}
          </Button>
        </div>

        {/* Blog Posts Grid */}
        {posts.length === 0 ? (
          <EmptyState
            title="No blog posts found"
            description="Check back later for new content"
          />
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
            gap: tokens.spacing[6]
          }}>
            {posts.map(post => (
              <BlogPostCard
                key={post.id}
                post={post}
                onClick={() => handlePostClick(post)}
              />
            ))}
          </div>
        )}
      </div>

      
      <ToastComponent />
    </div>
  );
};

export default BlogPage;