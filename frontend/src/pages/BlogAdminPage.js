import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PlusIcon, EyeIcon, PencilIcon, TrashIcon } from '@heroicons/react/24/outline';
import apiClient from '../services/unifiedApiClient';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import Button from '../design-system/components/Button';
import Card from '../design-system/components/Card';
import Input from '../design-system/components/Input';
import TextArea from '../design-system/components/TextArea';
import Modal from '../design-system/components/Modal';
import Select from '../design-system/components/Select';
import Badge from '../design-system/components/Badge';
import IconButton from '../design-system/components/IconButton';
import LoadingSpinner from '../design-system/components/LoadingSpinner';
import { Heading1, Text } from '../design-system/components/Typography';
import { tokens } from '../design-system/tokens';

const BlogAdminPage = () => {
  const [posts, setPosts] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('posts');
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedPost, setSelectedPost] = useState(null);
  const [formData, setFormData] = useState({
    title: '',
    slug: '',
    content: '',
    excerpt: '',
    featured_image: '',
    tags: [],
    status: 'draft',
    meta_description: '',
    meta_keywords: '',
  });
  const [newTag, setNewTag] = useState('');
  const [uploadingImage, setUploadingImage] = useState(false);
  
  const { showToast, ToastComponent } = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    if (user?.role !== 'admin') {
      navigate('/');
      return;
    }
    fetchPosts();
    fetchSubscriptions();
  }, [user, navigate]);

  const fetchPosts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/admin/blog/posts');
      setPosts(response.posts || []);
    } catch (error) {
      showToast('Failed to fetch blog posts', 'error');
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscriptions = async () => {
    try {
      const response = await apiClient.get('/admin/blog/subscriptions');
      setSubscriptions(response.subscriptions || []);
    } catch (error) {
      console.error('Failed to fetch subscriptions:', error);
    }
  };

  const handleCreatePost = () => {
    setSelectedPost(null);
    setFormData({
      title: '',
      slug: '',
      content: '',
      excerpt: '',
      featured_image: '',
      tags: [],
      status: 'draft',
      meta_description: '',
      meta_keywords: '',
    });
    setModalOpen(true);
  };

  const handleEditPost = async (postId) => {
    try {
      const post = await apiClient.get(`/admin/blog/posts/${postId}`);
      setSelectedPost(post);
      setFormData({
        title: post.title,
        slug: post.slug,
        content: post.content,
        excerpt: post.excerpt || '',
        featured_image: post.featured_image || '',
        tags: post.tags || [],
        status: post.status,
        meta_description: post.meta_description || '',
        meta_keywords: post.meta_keywords || '',
      });
      setModalOpen(true);
    } catch (error) {
      showToast('Failed to load post', 'error');
    }
  };

  const handleDeletePost = async (postId) => {
    if (window.confirm('Are you sure you want to delete this post?')) {
      try {
        await apiClient.delete(`/admin/blog/posts/${postId}`);
        showToast('Post deleted successfully', 'success');
        fetchPosts();
      } catch (error) {
        showToast('Failed to delete post', 'error');
      }
    }
  };

  const handleSavePost = async () => {
    try {
      // Clean up form data - remove empty optional fields
      const postData = { ...formData };
      
      // Remove empty slug - it will be auto-generated from title
      if (!postData.slug || postData.slug.trim() === '') {
        delete postData.slug;
      }
      
      // Remove other empty optional fields
      ['excerpt', 'featured_image', 'meta_description', 'meta_keywords'].forEach(field => {
        if (!postData[field] || postData[field].trim() === '') {
          delete postData[field];
        }
      });
      
      if (selectedPost) {
        await apiClient.patch(`/admin/blog/posts/${selectedPost.id}`, postData);
        showToast('Post updated successfully', 'success');
      } else {
        await apiClient.post('/admin/blog/posts', postData);
        showToast('Post created successfully', 'success');
      }
      setModalOpen(false);
      fetchPosts();
    } catch (error) {
      console.error('Blog post save error:', error.response?.data);
      showToast(error.response?.data?.detail || 'Failed to save post', 'error');
    }
  };

  const handleAddTag = () => {
    if (newTag && !formData.tags.includes(newTag)) {
      setFormData({ ...formData, tags: [...formData.tags, newTag] });
      setNewTag('');
    }
  };

  const handleRemoveTag = (tagToRemove) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter(tag => tag !== tagToRemove),
    });
  };

  const handleImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      showToast('Please upload a valid image file (JPEG, PNG, GIF, or WebP)', 'error');
      return;
    }

    // Validate file size (5MB max)
    if (file.size > 5 * 1024 * 1024) {
      showToast('Image size must be less than 5MB', 'error');
      return;
    }

    setUploadingImage(true);
    const formDataUpload = new FormData();
    formDataUpload.append('file', file);

    try {
      const response = await apiClient.post('/uploads/blog-image', formDataUpload, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setFormData({ ...formData, featured_image: response.url });
      showToast('Image uploaded successfully', 'success');
    } catch (error) {
      showToast('Failed to upload image', 'error');
    } finally {
      setUploadingImage(false);
    }
  };

  const handleDeleteSubscription = async (subId) => {
    if (window.confirm('Are you sure you want to delete this subscription?')) {
      try {
        await apiClient.delete(`/admin/blog/subscriptions/${subId}`);
        showToast('Subscription deleted successfully', 'success');
        fetchSubscriptions();
      } catch (error) {
        showToast('Failed to delete subscription', 'error');
      }
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'published':
        return 'success';
      case 'draft':
        return 'default';
      case 'archived':
        return 'danger';
      default:
        return 'default';
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

  return (
    <div style={{ 
      minHeight: '100vh',
      backgroundColor: tokens.colors.dark.bg,
      padding: tokens.spacing[6]
    }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto' }}>
        {/* Header */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: tokens.spacing[6]
        }}>
          <Heading1>Blog Admin</Heading1>
        </div>

        {/* Tabs */}
        <div style={{ 
          display: 'flex', 
          gap: tokens.spacing[2],
          marginBottom: tokens.spacing[6],
          borderBottom: `1px solid ${tokens.colors.dark.border}`,
          paddingBottom: tokens.spacing[2]
        }}>
          <Button
            variant={activeTab === 'posts' ? 'primary' : 'ghost'}
            onClick={() => setActiveTab('posts')}
          >
            Blog Posts
          </Button>
          <Button
            variant={activeTab === 'subscriptions' ? 'primary' : 'ghost'}
            onClick={() => setActiveTab('subscriptions')}
          >
            Subscriptions
          </Button>
        </div>

        {/* Posts Tab */}
        {activeTab === 'posts' && (
          <div>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'flex-end',
              marginBottom: tokens.spacing[4]
            }}>
              <Button onClick={handleCreatePost} icon={PlusIcon}>
                New Post
              </Button>
            </div>

            <Card>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: `1px solid ${tokens.colors.dark.border}` }}>
                      <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Title</th>
                      <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Author</th>
                      <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Status</th>
                      <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Created</th>
                      <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Views</th>
                      <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {posts.map(post => (
                      <tr key={post.id} style={{ borderBottom: `1px solid ${tokens.colors.dark.border}` }}>
                        <td style={{ padding: tokens.spacing[3] }}>{post.title}</td>
                        <td style={{ padding: tokens.spacing[3] }}>{post.author_name}</td>
                        <td style={{ padding: tokens.spacing[3] }}>
                          <Badge variant={getStatusColor(post.status)}>
                            {post.status}
                          </Badge>
                        </td>
                        <td style={{ padding: tokens.spacing[3] }}>
                          {new Date(post.created_at).toLocaleDateString()}
                        </td>
                        <td style={{ padding: tokens.spacing[3] }}>{post.view_count}</td>
                        <td style={{ padding: tokens.spacing[3] }}>
                          <div style={{ display: 'flex', gap: tokens.spacing[2] }}>
                            <IconButton
                              icon={EyeIcon}
                              onClick={() => navigate(`/blog/${post.slug}`)}
                              size="sm"
                            />
                            <IconButton
                              icon={PencilIcon}
                              onClick={() => handleEditPost(post.id)}
                              size="sm"
                            />
                            <IconButton
                              icon={TrashIcon}
                              onClick={() => handleDeletePost(post.id)}
                              variant="danger"
                              size="sm"
                            />
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}

        {/* Subscriptions Tab */}
        {activeTab === 'subscriptions' && (
          <Card>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: `1px solid ${tokens.colors.dark.border}` }}>
                    <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Email</th>
                    <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Status</th>
                    <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Frequency</th>
                    <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Created</th>
                    <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Last Notified</th>
                    <th style={{ padding: tokens.spacing[3], textAlign: 'left' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map(sub => (
                    <tr key={sub.id} style={{ borderBottom: `1px solid ${tokens.colors.dark.border}` }}>
                      <td style={{ padding: tokens.spacing[3] }}>{sub.email}</td>
                      <td style={{ padding: tokens.spacing[3] }}>
                        <Badge variant={sub.status === 'active' ? 'success' : 'default'}>
                          {sub.status}
                        </Badge>
                      </td>
                      <td style={{ padding: tokens.spacing[3] }}>{sub.frequency}</td>
                      <td style={{ padding: tokens.spacing[3] }}>
                        {new Date(sub.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ padding: tokens.spacing[3] }}>
                        {sub.last_notified_at
                          ? new Date(sub.last_notified_at).toLocaleDateString()
                          : 'Never'}
                      </td>
                      <td style={{ padding: tokens.spacing[3] }}>
                        <IconButton
                          icon={TrashIcon}
                          onClick={() => handleDeleteSubscription(sub.id)}
                          variant="danger"
                          size="sm"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>

      {/* Post Editor Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={selectedPost ? 'Edit Post' : 'Create New Post'}
        size="lg"
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: tokens.spacing[4] }}>
          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Title *
            </label>
            <Input
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="Enter post title"
            />
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Slug
            </label>
            <Input
              value={formData.slug}
              onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
              placeholder="URL-friendly slug (auto-generated if empty)"
            />
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Excerpt
            </label>
            <TextArea
              value={formData.excerpt}
              onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
              placeholder="Brief description of the post"
              rows={3}
            />
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Content *
            </label>
            <TextArea
              value={formData.content}
              onChange={(e) => setFormData({ ...formData, content: e.target.value })}
              placeholder="Post content (HTML supported)"
              rows={10}
            />
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Featured Image
            </label>
            <div style={{ display: 'flex', gap: tokens.spacing[2], alignItems: 'center' }}>
              <Input
                value={formData.featured_image}
                onChange={(e) => setFormData({ ...formData, featured_image: e.target.value })}
                placeholder="Image URL or upload below"
                style={{ flex: 1 }}
              />
              <label style={{
                display: 'inline-flex',
                alignItems: 'center',
                padding: `${tokens.spacing[2]} ${tokens.spacing[3]}`,
                backgroundColor: tokens.colors.dark.surface,
                color: tokens.colors.dark.text,
                borderRadius: tokens.borderRadius.md,
                border: `1px solid ${tokens.colors.dark.border}`,
                cursor: uploadingImage ? 'not-allowed' : 'pointer',
                fontSize: tokens.typography.fontSize.sm[0],
                fontWeight: tokens.typography.fontWeight.medium,
                opacity: uploadingImage ? 0.6 : 1,
              }}>
                <input
                  type="file"
                  accept="image/jpeg,image/png,image/gif,image/webp"
                  onChange={handleImageUpload}
                  disabled={uploadingImage}
                  style={{ display: 'none' }}
                />
                {uploadingImage ? 'Uploading...' : 'Upload Image'}
              </label>
            </div>
            {formData.featured_image && (
              <div style={{ marginTop: tokens.spacing[2] }}>
                <img
                  src={formData.featured_image}
                  alt="Featured"
                  style={{
                    maxWidth: '200px',
                    maxHeight: '150px',
                    borderRadius: tokens.borderRadius.md,
                    border: `1px solid ${tokens.colors.dark.border}`,
                  }}
                />
              </div>
            )}
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Tags
            </label>
            <div style={{ display: 'flex', gap: tokens.spacing[2], marginBottom: tokens.spacing[2] }}>
              <Input
                value={newTag}
                onChange={(e) => setNewTag(e.target.value)}
                placeholder="Add a tag"
                onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
              />
              <Button onClick={handleAddTag} variant="secondary">Add</Button>
            </div>
            <div style={{ display: 'flex', gap: tokens.spacing[2], flexWrap: 'wrap' }}>
              {formData.tags.map(tag => (
                <Badge key={tag} variant="info">
                  {tag}
                  <button
                    onClick={() => handleRemoveTag(tag)}
                    style={{
                      marginLeft: tokens.spacing[2],
                      background: 'none',
                      border: 'none',
                      color: 'inherit',
                      cursor: 'pointer',
                    }}
                  >
                    ×
                  </button>
                </Badge>
              ))}
            </div>
          </div>

          <div>
            <label style={{ 
              display: 'block', 
              marginBottom: tokens.spacing[2],
              fontSize: tokens.typography.fontSize.sm[0],
              fontWeight: tokens.typography.fontWeight.medium 
            }}>
              Status
            </label>
            <Select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value })}
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
              <option value="archived">Archived</option>
            </Select>
          </div>

          <div style={{ 
            display: 'flex', 
            justifyContent: 'flex-end',
            gap: tokens.spacing[3],
            marginTop: tokens.spacing[4],
            paddingTop: tokens.spacing[4],
            borderTop: `1px solid ${tokens.colors.dark.border}`,
            backgroundColor: tokens.colors.dark.bg,
            position: 'sticky',
            bottom: 0,
            marginLeft: `-${tokens.spacing[6]}`,
            marginRight: `-${tokens.spacing[6]}`,
            marginBottom: `-${tokens.spacing[6]}`,
            padding: tokens.spacing[4],
          }}>
            <Button variant="ghost" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSavePost} variant="primary">
              {selectedPost ? 'Update' : 'Create'} Post
            </Button>
          </div>
        </div>
      </Modal>
      
      <ToastComponent />
    </div>
  );
};

export default BlogAdminPage;