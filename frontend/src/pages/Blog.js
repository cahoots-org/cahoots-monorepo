import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  Image,
  Badge,
  Input,
  Button,
  SimpleGrid,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalBody,
  ModalFooter,
  ModalCloseButton,
  FormControl,
  FormLabel,
  Select,
  useDisclosure,
  Spinner,
  Center,
  Tag,
  Wrap,
  WrapItem,
  InputGroup,
  InputLeftElement,
} from '@chakra-ui/react';
import { SearchIcon, BellIcon } from '@chakra-ui/icons';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '../services/unifiedApiClient';
import { useAuth } from '../contexts/AuthContext';
import DOMPurify from 'dompurify';

const BlogPostCard = ({ post, onClick }) => {
  const bgColor = 'white';
  const borderColor = 'gray.200';
  const textColor = 'gray.600';

  return (
    <Box
      bg={bgColor}
      borderRadius="lg"
      borderWidth={1}
      borderColor={borderColor}
      overflow="hidden"
      cursor="pointer"
      onClick={onClick}
      _hover={{ transform: 'translateY(-4px)', shadow: 'lg' }}
      transition="all 0.2s"
    >
      {post.featured_image && (
        <Image
          src={post.featured_image}
          alt={post.title}
          h="200px"
          w="100%"
          objectFit="cover"
        />
      )}
      <Box p={6}>
        <VStack align="start" spacing={3}>
          <Heading size="md" noOfLines={2}>
            {post.title}
          </Heading>
          <HStack>
            <Text fontSize="sm" color={textColor}>
              By {post.author_name}
            </Text>
            <Text fontSize="sm" color={textColor}>
              •
            </Text>
            <Text fontSize="sm" color={textColor}>
              {new Date(post.published_at || post.created_at).toLocaleDateString()}
            </Text>
          </HStack>
          <Text noOfLines={3} color={textColor}>
            {post.excerpt || post.content.replace(/<[^>]*>/g, '').substring(0, 150)}...
          </Text>
          {post.tags && post.tags.length > 0 && (
            <Wrap>
              {post.tags.slice(0, 3).map(tag => (
                <WrapItem key={tag}>
                  <Tag size="sm" colorScheme="blue">
                    {tag}
                  </Tag>
                </WrapItem>
              ))}
            </Wrap>
          )}
        </VStack>
      </Box>
    </Box>
  );
};

const BlogPost = ({ post, onBack }) => {
  const bgColor = 'white';
  const borderColor = 'gray.200';
  const textColor = 'gray.600';

  return (
    <Container maxW="container.md" py={8}>
      <Button onClick={onBack} mb={6} variant="ghost">
        ← Back to Blog
      </Button>
      
      <Box
        bg={bgColor}
        borderRadius="lg"
        borderWidth={1}
        borderColor={borderColor}
        p={8}
      >
        <VStack align="start" spacing={6}>
          {post.featured_image && (
            <Image
              src={post.featured_image}
              alt={post.title}
              w="100%"
              maxH="400px"
              objectFit="cover"
              borderRadius="md"
            />
          )}
          
          <VStack align="start" spacing={3} w="100%">
            <Heading size="xl">{post.title}</Heading>
            
            <HStack>
              <Text color={textColor}>By {post.author_name}</Text>
              <Text color={textColor}>•</Text>
              <Text color={textColor}>
                {new Date(post.published_at || post.created_at).toLocaleDateString()}
              </Text>
              <Text color={textColor}>•</Text>
              <Text color={textColor}>{post.view_count} views</Text>
            </HStack>
            
            {post.tags && post.tags.length > 0 && (
              <Wrap>
                {post.tags.map(tag => (
                  <WrapItem key={tag}>
                    <Tag colorScheme="blue">{tag}</Tag>
                  </WrapItem>
                ))}
              </Wrap>
            )}
          </VStack>
          
          <Box
            w="100%"
            className="blog-content"
            dangerouslySetInnerHTML={{
              __html: DOMPurify.sanitize(post.content)
            }}
            sx={{
              '& h1, & h2, & h3, & h4, & h5, & h6': {
                mt: 6,
                mb: 3,
                fontWeight: 'bold',
              },
              '& p': {
                mb: 4,
                lineHeight: 1.8,
              },
              '& ul, & ol': {
                ml: 6,
                mb: 4,
              },
              '& li': {
                mb: 2,
              },
              '& blockquote': {
                borderLeft: '4px solid',
                borderColor: 'blue.500',
                pl: 4,
                my: 4,
                fontStyle: 'italic',
              },
              '& img': {
                maxW: '100%',
                h: 'auto',
                my: 4,
                borderRadius: 'md',
              },
              '& a': {
                color: 'blue.500',
                textDecoration: 'underline',
              },
              '& pre': {
                bg: 'gray.100',
                p: 4,
                borderRadius: 'md',
                overflowX: 'auto',
                my: 4,
              },
              '& code': {
                bg: 'gray.100',
                px: 1,
                borderRadius: 'sm',
                fontSize: 'sm',
              },
            }}
          />
        </VStack>
      </Box>
    </Container>
  );
};

const Blog = () => {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('');
  const [selectedPost, setSelectedPost] = useState(null);
  const [subscriptionEmail, setSubscriptionEmail] = useState('');
  const [subscriptionFrequency, setSubscriptionFrequency] = useState('immediate');
  const [mySubscription, setMySubscription] = useState(null);
  
  const { isOpen, onOpen, onClose } = useDisclosure();
  const toast = useToast();
  const navigate = useNavigate();
  const { slug } = useParams();
  const { user } = useAuth();
  
  const bgColor = 'gray.50';
  const cardBgColor = 'white';

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
      if (selectedTag) params.tag = selectedTag;
      
      const response = await apiClient.get('/blog/posts', { params });
      setPosts(response.posts || []);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to fetch blog posts',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
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
      toast({
        title: 'Error',
        description: 'Failed to fetch blog post',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
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

  const handleSubscribe = async () => {
    try {
      const data = {
        email: user ? user.email : subscriptionEmail,
        frequency: subscriptionFrequency,
        categories: [],
      };
      
      await apiClient.post('/blog/subscribe', data);
      
      toast({
        title: 'Success',
        description: 'Successfully subscribed to blog notifications! Check your email to verify.',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      onClose();
      setSubscriptionEmail('');
      
      if (user) {
        fetchMySubscription();
      }
    } catch (error) {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to subscribe',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleUnsubscribe = async () => {
    try {
      await apiClient.delete('/blog/my-subscription');
      
      toast({
        title: 'Success',
        description: 'Successfully unsubscribed from blog notifications',
        status: 'success',
        duration: 5000,
        isClosable: true,
      });
      
      setMySubscription(null);
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to unsubscribe',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  const handleUpdateSubscription = async () => {
    try {
      const updated = await apiClient.patch('/blog/my-subscription', {
        frequency: subscriptionFrequency,
      });
      
      setMySubscription(updated);
      
      toast({
        title: 'Success',
        description: 'Subscription preferences updated',
        status: 'success',
        duration: 3000,
        isClosable: true,
      });
      
      onClose();
    } catch (error) {
      toast({
        title: 'Error',
        description: 'Failed to update subscription',
        status: 'error',
        duration: 5000,
        isClosable: true,
      });
    }
  };

  if (loading) {
    return (
      <Center h="100vh">
        <Spinner size="xl" />
      </Center>
    );
  }

  if (selectedPost) {
    return <BlogPost post={selectedPost} onBack={handleBackToBlog} />;
  }

  return (
    <Box bg={bgColor} minH="100vh">
      <Container maxW="container.xl" py={8}>
        <VStack spacing={8} align="stretch">
          {/* Header */}
          <VStack spacing={4}>
            <Heading size="2xl">Blog</Heading>
            <Text fontSize="lg" color="gray.600">
              Insights, updates, and tutorials from the Cahoots team
            </Text>
          </VStack>

          {/* Search and Subscribe */}
          <HStack justify="space-between" flexWrap="wrap" spacing={4}>
            <InputGroup maxW="400px">
              <InputLeftElement pointerEvents="none">
                <SearchIcon color="gray.400" />
              </InputLeftElement>
              <Input
                placeholder="Search posts..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
            </InputGroup>
            
            <Button
              leftIcon={<BellIcon />}
              colorScheme="blue"
              onClick={() => {
                if (mySubscription) {
                  setSubscriptionFrequency(mySubscription.frequency);
                }
                onOpen();
              }}
            >
              {mySubscription ? 'Manage Subscription' : 'Subscribe'}
            </Button>
          </HStack>

          {/* Blog Posts Grid */}
          {posts.length === 0 ? (
            <Center py={16}>
              <VStack>
                <Text fontSize="lg" color="gray.500">
                  No blog posts found
                </Text>
              </VStack>
            </Center>
          ) : (
            <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} spacing={6}>
              {posts.map(post => (
                <BlogPostCard
                  key={post.id}
                  post={post}
                  onClick={() => handlePostClick(post)}
                />
              ))}
            </SimpleGrid>
          )}
        </VStack>
      </Container>

      {/* Subscription Modal */}
      <Modal isOpen={isOpen} onClose={onClose}>
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            {mySubscription ? 'Manage Subscription' : 'Subscribe to Blog'}
          </ModalHeader>
          <ModalCloseButton />
          <ModalBody>
            <VStack spacing={4}>
              {!user && !mySubscription && (
                <FormControl isRequired>
                  <FormLabel>Email</FormLabel>
                  <Input
                    type="email"
                    value={subscriptionEmail}
                    onChange={(e) => setSubscriptionEmail(e.target.value)}
                    placeholder="your@email.com"
                  />
                </FormControl>
              )}
              
              <FormControl>
                <FormLabel>Notification Frequency</FormLabel>
                <Select
                  value={subscriptionFrequency}
                  onChange={(e) => setSubscriptionFrequency(e.target.value)}
                >
                  <option value="immediate">Immediate</option>
                  <option value="daily">Daily Digest</option>
                  <option value="weekly">Weekly Digest</option>
                  <option value="monthly">Monthly Digest</option>
                </Select>
              </FormControl>
              
              {mySubscription && (
                <Text fontSize="sm" color="gray.500">
                  Currently subscribed with: {mySubscription.email}
                </Text>
              )}
            </VStack>
          </ModalBody>
          
          <ModalFooter>
            {mySubscription ? (
              <>
                <Button variant="ghost" colorScheme="red" mr="auto" onClick={handleUnsubscribe}>
                  Unsubscribe
                </Button>
                <Button variant="ghost" mr={3} onClick={onClose}>
                  Cancel
                </Button>
                <Button colorScheme="blue" onClick={handleUpdateSubscription}>
                  Update Preferences
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" mr={3} onClick={onClose}>
                  Cancel
                </Button>
                <Button
                  colorScheme="blue"
                  onClick={handleSubscribe}
                  isDisabled={!user && !subscriptionEmail}
                >
                  Subscribe
                </Button>
              </>
            )}
          </ModalFooter>
        </ModalContent>
      </Modal>
      <ToastComponent />
    </Box>
  );
};

export default Blog;