import { check, sleep } from 'k6';
import http from 'k6/http';
import { Counter, Rate, Trend } from 'k6/metrics';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';
import redis from 'k6/x/redis';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.0.2/index.js';

// Custom metrics
const customMetrics = {
    redis_ops: new Counter('redis_operations'),
    message_publish_rate: new Rate('message_publish_rate'),
    api_reqs: new Counter('api_requests'),
    api_req_duration: new Trend('api_request_duration'),
};

// Test configuration
export const options = {
    scenarios: {
        // Integration tests
        integration: {
            executor: 'shared-iterations',
            vus: 1,
            iterations: 1,
            exec: 'integrationTests',
            startTime: '0s',
        },
        // Load tests
        load: {
            executor: 'ramping-vus',
            startVUs: 0,
            stages: [
                { duration: '30s', target: 10 },  // Ramp up
                { duration: '1m', target: 10 },   // Steady state
                { duration: '30s', target: 20 },  // Scale up
                { duration: '1m', target: 20 },   // Steady state
                { duration: '30s', target: 0 },   // Scale down
            ],
            exec: 'loadTests',
            startTime: '2m',  // Start after integration tests
        },
        // Stress tests
        stress: {
            executor: 'ramping-arrival-rate',
            startRate: 10,
            timeUnit: '1s',
            preAllocatedVUs: 20,
            maxVUs: 50,
            stages: [
                { duration: '1m', target: 20 },
                { duration: '2m', target: 40 },
                { duration: '1m', target: 0 },
            ],
            exec: 'loadTests',
            startTime: '6m',  // Start after load tests
        },
    },
    thresholds: {
        http_req_duration: ['p(95)<500'],  // 95% of requests should be below 500ms
        http_req_failed: ['rate<0.01'],    // Less than 1% of requests should fail
        'api_request_duration': ['p(95)<1000'],  // Custom threshold for API requests
        'redis_operations': ['count>100'],       // Minimum Redis operations
    },
};

// Shared state
const state = {
    redisClient: null,
    baseUrl: __ENV.API_URL || 'http://localhost:8000',
    authToken: null,
};

// Setup code
export function setup() {
    console.log('Setting up test environment...');
    
    // Connect to Redis
    state.redisClient = new redis.Client({
        addr: __ENV.REDIS_URL || 'localhost:6379',
        password: __ENV.REDIS_PASSWORD || '',
    });
    
    // Get auth token if needed
    // state.authToken = getAuthToken();
    
    return state;
}

// Teardown code
export function teardown(data) {
    console.log('Cleaning up test environment...');
    if (data.redisClient) {
        data.redisClient.close();
    }
}

// Integration tests
export function integrationTests() {
    console.log('Running integration tests...');
    
    // Health check
    {
        const response = http.get(`${state.baseUrl}/health`);
        check(response, {
            'health check returns 200': (r) => r.status === 200,
            'health check shows healthy': (r) => r.json('status') === 'healthy',
        });
        customMetrics.api_req_duration.add(response.timings.duration);
        customMetrics.api_reqs.add(1);
    }
    
    // Redis operations
    {
        const testKey = `test:${randomString(8)}`;
        const testValue = randomString(16);
        
        state.redisClient.set(testKey, testValue);
        customMetrics.redis_ops.add(1);
        
        const value = state.redisClient.get(testKey);
        customMetrics.redis_ops.add(1);
        
        check(value, {
            'redis get returns correct value': (v) => v === testValue,
        });
        
        state.redisClient.del(testKey);
        customMetrics.redis_ops.add(1);
    }
    
    // Message publishing
    {
        const message = {
            type: 'test_message',
            payload: {
                id: randomString(8),
                timestamp: new Date().toISOString(),
            },
        };
        
        const response = http.post(
            `${state.baseUrl}/messages/system`,
            JSON.stringify(message),
            {
                headers: { 'Content-Type': 'application/json' },
            }
        );
        
        check(response, {
            'message publish returns 202': (r) => r.status === 202,
        });
        
        customMetrics.message_publish_rate.add(true);
        customMetrics.api_reqs.add(1);
        customMetrics.api_req_duration.add(response.timings.duration);
    }
}

// Load tests
export function loadTests() {
    // Random sleep between requests (1-5 seconds)
    sleep(Math.random() * 4 + 1);
    
    const endpoints = [
        { path: '/health', method: 'GET' },
        { 
            path: '/messages/system',
            method: 'POST',
            body: {
                type: 'test_message',
                payload: {
                    id: randomString(8),
                    timestamp: new Date().toISOString(),
                },
            },
        },
        {
            path: '/projects',
            method: 'POST',
            body: {
                name: `Test Project ${randomString(8)}`,
                description: 'Load test project',
            },
        },
    ];
    
    // Randomly select an endpoint
    const endpoint = endpoints[Math.floor(Math.random() * endpoints.length)];
    
    // Make request
    const response = endpoint.method === 'GET'
        ? http.get(`${state.baseUrl}${endpoint.path}`)
        : http.post(
            `${state.baseUrl}${endpoint.path}`,
            JSON.stringify(endpoint.body),
            { headers: { 'Content-Type': 'application/json' } }
        );
    
    // Record metrics
    customMetrics.api_reqs.add(1);
    customMetrics.api_req_duration.add(response.timings.duration);
    
    // Verify response
    check(response, {
        'status is 200-299': (r) => r.status >= 200 && r.status < 300,
        'response time OK': (r) => r.timings.duration < 500,
    });
}

// Custom summary
export function handleSummary(data) {
    return {
        'stdout': textSummary(data, { indent: ' ', enableColors: true }),
        'tests/k6/results.json': JSON.stringify(data),
    };
} 