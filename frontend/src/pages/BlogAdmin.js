import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  IconButton,
  Badge,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Input,
  Textarea,
  Select,
  VStack,
  HStack,
  Text,
  Tag,
  TagLabel,
  TagCloseButton,
  useDisclosure,
  Tabs,
  TabList,
  TabPanels,
  Tab,
  TabPanel,
} from '@chakra-ui/react';
import { EditIcon, DeleteIcon, ViewIcon, AddIcon } from '@chakra-ui/icons';
import { useNavigate } from 'react-router-dom';
import apiClient from '../services/unifiedApiClient';
import { useAuth } from '../contexts/AuthContext';
import { useToast } from '../hooks/useToast';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

const BlogAdmin = () => {
  const [posts, setPosts] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  const [loading, setLoading] = useState(true);
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
  
  const { isOpen, onOpen, onClose } = useDisclosure();
  const { showToast, ToastComponent } = useToast();
  const navigate = useNavigate();
  const { user } = useAuth();
  const bgColor = 'white';
  const borderColor = 'gray.200';

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
    onOpen();
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
      onOpen();
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
      if (selectedPost) {
        // Update existing post
        await apiClient.patch(`/admin/blog/posts/${selectedPost.id}`, formData);
        showToast('Post updated successfully', 'success');
      } else {
        // Create new post
        await apiClient.post('/admin/blog/posts', formData);
        showToast('Post created successfully', 'success');
      }
      onClose();
      fetchPosts();
    } catch (error) {
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
        return 'green';
      case 'draft':
        return 'gray';
      case 'archived':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <>
      <Container maxW="container.xl" py={8}>
      <Tabs>
        <TabList>
          <Tab>Blog Posts</Tab>
          <Tab>Subscriptions</Tab>
        </TabList>

        <TabPanels>
          <TabPanel>
            <VStack spacing={6} align="stretch">
              <HStack justify="space-between">
                <Heading size="lg">Blog Posts</Heading>
                <Button
                  leftIcon={<AddIcon />}
                  colorScheme="blue"
                  onClick={handleCreatePost}
                >
                  New Post
                </Button>
              </HStack>

              <Box
                bg={bgColor}
                borderRadius="lg"
                borderWidth={1}
                borderColor={borderColor}
                overflowX="auto"
              >
                <Table variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Title</Th>
                      <Th>Author</Th>
                      <Th>Status</Th>
                      <Th>Created</Th>
                      <Th>Views</Th>
                      <Th>Actions</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {posts.map(post => (
                      <Tr key={post.id}>
                        <Td>{post.title}</Td>
                        <Td>{post.author_name}</Td>
                        <Td>
                          <Badge colorScheme={getStatusColor(post.status)}>
                            {post.status}
                          </Badge>
                        </Td>
                        <Td>{new Date(post.created_at).toLocaleDateString()}</Td>
                        <Td>{post.view_count}</Td>
                        <Td>
                          <HStack spacing={2}>
                            <IconButton
                              icon={<ViewIcon />}
                              size="sm"
                              onClick={() => navigate(`/blog/${post.slug}`)}
                              aria-label="View post"
                            />
                            <IconButton
                              icon={<EditIcon />}
                              size="sm"
                              onClick={() => handleEditPost(post.id)}
                              aria-label="Edit post"
                            />
                            <IconButton
                              icon={<DeleteIcon />}
                              size="sm"
                              colorScheme="red"
                              onClick={() => handleDeletePost(post.id)}
                              aria-label="Delete post"
                            />
                          </HStack>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </VStack>
          </TabPanel>

          <TabPanel>
            <VStack spacing={6} align="stretch">
              <Heading size="lg">Subscriptions</Heading>

              <Box
                bg={bgColor}
                borderRadius="lg"
                borderWidth={1}
                borderColor={borderColor}
                overflowX="auto"
              >
                <Table variant="simple">
                  <Thead>
                    <Tr>
                      <Th>Email</Th>
                      <Th>Status</Th>
                      <Th>Frequency</Th>
                      <Th>Created</Th>
                      <Th>Last Notified</Th>
                      <Th>Actions</Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {subscriptions.map(sub => (
                      <Tr key={sub.id}>
                        <Td>{sub.email}</Td>
                        <Td>
                          <Badge colorScheme={sub.status === 'active' ? 'green' : 'gray'}>
                            {sub.status}
                          </Badge>
                        </Td>
                        <Td>{sub.frequency}</Td>
                        <Td>{new Date(sub.created_at).toLocaleDateString()}</Td>
                        <Td>
                          {sub.last_notified_at
                            ? new Date(sub.last_notified_at).toLocaleDateString()
                            : 'Never'}
                        </Td>
                        <Td>
                          <IconButton
                            icon={<DeleteIcon />}
                            size="sm"
                            colorScheme="red"
                            onClick={() => handleDeleteSubscription(sub.id)}
                            aria-label="Delete subscription"
                          />
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
              </Box>
            </VStack>
          </TabPanel>
        </TabPanels>
      </Tabs>

      {/* Post Editor Modal */}
      <Modal isOpen={isOpen} onClose={onClose} size="6xl">
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {selectedPost ? 'Edit Post' : 'Create New Post'}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              <FormControl isRequired>
                <FormLabel>Title</FormLabel>
                <Input
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                  placeholder="Enter post title"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Slug</FormLabel>
                <Input
                  value={formData.slug}
                  onChange={(e) => setFormData({ ...formData, slug: e.target.value })}
                  placeholder="URL-friendly slug (auto-generated if empty)"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Excerpt</FormLabel>
                <Textarea
                  value={formData.excerpt}
                  onChange={(e) => setFormData({ ...formData, excerpt: e.target.value })}
                  placeholder="Brief description of the post"
                  rows={3}
                />
              </FormControl>

              <FormControl isRequired>
                <FormLabel>Content</FormLabel>
                <Box minH="300px">
                  <ReactQuill
                    theme="snow"
                    value={formData.content}
                    onChange={(value) => setFormData({ ...formData, content: value })}
                    style={{ height: '250px', marginBottom: '50px' }}
                  />
                </Box>
              </FormControl>

              <FormControl>
                <FormLabel>Featured Image URL</FormLabel>
                <Input
                  value={formData.featured_image}
                  onChange={(e) => setFormData({ ...formData, featured_image: e.target.value })}
                  placeholder="https://example.com/image.jpg"
                />
              </FormControl>

              <FormControl>
                <FormLabel>Tags</FormLabel>
                <HStack mb={2}>
                  <Input
                    value={newTag}
                    onChange={(e) => setNewTag(e.target.value)}
                    placeholder="Add a tag"
                    onKeyPress={(e) => e.key === 'Enter' && handleAddTag()}
                  />
                  <Button onClick={handleAddTag}>Add</Button>
                </HStack>
                <HStack wrap="wrap">
                  {formData.tags.map(tag => (
                    <Tag key={tag} size="md" colorScheme="blue">
                      <TagLabel>{tag}</TagLabel>
                      <TagCloseButton onClick={() => handleRemoveTag(tag)} />
                    </Tag>
                  ))}
                </HStack>
              </FormControl>

              <FormControl>
                <FormLabel>Status</FormLabel>
                <Select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                  <option value="archived">Archived</option>
                </Select>
              </FormControl>

              <FormControl>
                <FormLabel>Meta Description</FormLabel>
                <Textarea
                  value={formData.meta_description}
                  onChange={(e) => setFormData({ ...formData, meta_description: e.target.value })}
                  placeholder="SEO meta description"
                  rows={2}
                />
              </FormControl>

              <FormControl>
                <FormLabel>Meta Keywords</FormLabel>
                <Input
                  value={formData.meta_keywords}
                  onChange={(e) => setFormData({ ...formData, meta_keywords: e.target.value })}
                  placeholder="SEO keywords, comma-separated"
                />
              </FormControl>
            </VStack>
          </ModalBody>

          <ModalFooter>
            <Button variant="ghost" mr={3} onClick={onClose}>
              Cancel
            </Button>
            <Button colorScheme="blue" onClick={handleSavePost}>
              {selectedPost ? 'Update' : 'Create'} Post
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Container>
      <ToastComponent />
    </>
  );
};

export default BlogAdmin;