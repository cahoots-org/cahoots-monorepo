// Tech stack configuration for the Create Task wizard
export const TECH_STACK_CONFIG = {
  'web-application': {
    label: 'Web Application',
    description: 'Full-stack web applications with user interfaces',
    stacks: [
      {
        id: 'react-node-postgres',
        name: 'React + Node.js + PostgreSQL',
        description: 'Modern SPA stack',
        frontend_framework: 'React',
        backend_language: 'JavaScript/Node.js',
        database: 'PostgreSQL'
      },
      {
        id: 'nextjs-postgres',
        name: 'Next.js + PostgreSQL',
        description: 'Full-stack React framework',
        frontend_framework: 'Next.js',
        backend_language: 'JavaScript/Node.js',
        database: 'PostgreSQL'
      },
      {
        id: 'vue-express-mysql',
        name: 'Vue.js + Express + MySQL',
        description: 'Progressive framework stack',
        frontend_framework: 'Vue.js',
        backend_language: 'JavaScript/Node.js',
        database: 'MySQL'
      },
      {
        id: 'angular-dotnet-sqlserver',
        name: 'Angular + .NET + SQL Server',
        description: 'Enterprise stack',
        frontend_framework: 'Angular',
        backend_language: 'C#',
        database: 'SQL Server'
      },
      {
        id: 'svelte-fastapi-postgres',
        name: 'Svelte + FastAPI + PostgreSQL',
        description: 'Modern lightweight stack',
        frontend_framework: 'Svelte',
        backend_language: 'Python',
        database: 'PostgreSQL'
      },
      {
        id: 'wordpress-mysql',
        name: 'WordPress + MySQL',
        description: 'Content management',
        frontend_framework: 'WordPress',
        backend_language: 'PHP',
        database: 'MySQL'
      },
      {
        id: 'django-postgres',
        name: 'Django + PostgreSQL',
        description: 'Python full-stack',
        frontend_framework: 'Django Templates',
        backend_language: 'Python',
        database: 'PostgreSQL'
      },
      {
        id: 'rails-postgres',
        name: 'Ruby on Rails + PostgreSQL',
        description: 'Convention over configuration',
        frontend_framework: 'Rails Views',
        backend_language: 'Ruby',
        database: 'PostgreSQL'
      }
    ]
  },
  'mobile-application': {
    label: 'Mobile Application',
    description: 'Native and cross-platform mobile apps',
    stacks: [
      {
        id: 'react-native-firebase',
        name: 'React Native + Firebase',
        description: 'Cross-platform with backend-as-a-service',
        frontend_framework: 'React Native',
        backend_language: 'Firebase Functions',
        database: 'Firebase'
      },
      {
        id: 'flutter-firebase',
        name: 'Flutter + Firebase',
        description: 'Google\'s cross-platform framework',
        frontend_framework: 'Flutter',
        backend_language: 'Firebase Functions',
        database: 'Firebase'
      },
      {
        id: 'swift-coredata',
        name: 'Swift + Core Data',
        description: 'Native iOS',
        frontend_framework: 'SwiftUI',
        backend_language: 'Swift',
        database: 'Core Data'
      },
      {
        id: 'kotlin-room',
        name: 'Kotlin + Room + Retrofit',
        description: 'Native Android',
        frontend_framework: 'Android Views',
        backend_language: 'Kotlin',
        database: 'Room/SQLite'
      },
      {
        id: 'expo-supabase',
        name: 'Expo + Supabase',
        description: 'Managed React Native',
        frontend_framework: 'React Native',
        backend_language: 'Supabase Edge Functions',
        database: 'Supabase'
      },
      {
        id: 'ionic-angular-firebase',
        name: 'Ionic + Angular + Firebase',
        description: 'Hybrid mobile',
        frontend_framework: 'Ionic',
        backend_language: 'Firebase Functions',
        database: 'Firebase'
      },
      {
        id: 'xamarin-azure',
        name: 'Xamarin + Azure',
        description: 'Microsoft cross-platform',
        frontend_framework: 'Xamarin',
        backend_language: 'C#',
        database: 'Azure SQL'
      }
    ]
  },
  'api-backend': {
    label: 'API/Backend Service',
    description: 'Server-side applications and microservices',
    stacks: [
      {
        id: 'fastapi-postgres',
        name: 'FastAPI + PostgreSQL',
        description: 'Modern Python API',
        frontend_framework: 'API Only',
        backend_language: 'Python',
        database: 'PostgreSQL'
      },
      {
        id: 'express-mongodb',
        name: 'Express.js + MongoDB',
        description: 'Node.js REST API',
        frontend_framework: 'API Only',
        backend_language: 'JavaScript/Node.js',
        database: 'MongoDB'
      },
      {
        id: 'spring-boot-mysql',
        name: 'Spring Boot + MySQL',
        description: 'Enterprise Java',
        frontend_framework: 'API Only',
        backend_language: 'Java',
        database: 'MySQL'
      },
      {
        id: 'aspnet-core-sqlserver',
        name: 'ASP.NET Core + SQL Server',
        description: 'Microsoft stack',
        frontend_framework: 'API Only',
        backend_language: 'C#',
        database: 'SQL Server'
      },
      {
        id: 'go-postgres',
        name: 'Go + PostgreSQL',
        description: 'High-performance API',
        frontend_framework: 'API Only',
        backend_language: 'Go',
        database: 'PostgreSQL'
      },
      {
        id: 'rails-api-postgres',
        name: 'Ruby on Rails API + PostgreSQL',
        description: 'API-only mode',
        frontend_framework: 'API Only',
        backend_language: 'Ruby',
        database: 'PostgreSQL'
      },
      {
        id: 'graphql-postgres',
        name: 'GraphQL + PostgreSQL',
        description: 'Query language API',
        frontend_framework: 'API Only',
        backend_language: 'JavaScript/Node.js',
        database: 'PostgreSQL'
      },
      {
        id: 'serverless-dynamodb',
        name: 'Serverless + DynamoDB',
        description: 'AWS Lambda functions',
        frontend_framework: 'API Only',
        backend_language: 'JavaScript/Node.js',
        database: 'DynamoDB'
      }
    ]
  },
  'desktop-application': {
    label: 'Desktop Application',
    description: 'Native desktop applications',
    stacks: [
      {
        id: 'electron-react',
        name: 'Electron + React',
        description: 'Cross-platform desktop',
        frontend_framework: 'React',
        backend_language: 'JavaScript/Node.js',
        database: 'SQLite'
      },
      {
        id: 'tauri-react',
        name: 'Tauri + React/Vue',
        description: 'Rust-based lightweight desktop',
        frontend_framework: 'React',
        backend_language: 'Rust',
        database: 'SQLite'
      },
      {
        id: 'qt-cpp',
        name: 'Qt + C++',
        description: 'Native cross-platform',
        frontend_framework: 'Qt',
        backend_language: 'C++',
        database: 'SQLite'
      },
      {
        id: 'wpf-csharp',
        name: 'WPF + C#',
        description: 'Windows native',
        frontend_framework: 'WPF',
        backend_language: 'C#',
        database: 'SQL Server'
      },
      {
        id: 'swiftui-coredata',
        name: 'SwiftUI + Core Data',
        description: 'macOS native',
        frontend_framework: 'SwiftUI',
        backend_language: 'Swift',
        database: 'Core Data'
      },
      {
        id: 'flutter-desktop',
        name: 'Flutter Desktop',
        description: 'Multi-platform from single codebase',
        frontend_framework: 'Flutter',
        backend_language: 'Dart',
        database: 'SQLite'
      },
      {
        id: 'tkinter-python',
        name: 'Tkinter + Python',
        description: 'Simple Python desktop',
        frontend_framework: 'Tkinter',
        backend_language: 'Python',
        database: 'SQLite'
      }
    ]
  },
  'data-science': {
    label: 'Data Science/Analytics',
    description: 'Data processing, analysis, and machine learning',
    stacks: [
      {
        id: 'python-pandas-jupyter',
        name: 'Python + Pandas + Jupyter',
        description: 'Data analysis',
        frontend_framework: 'Jupyter Notebooks',
        backend_language: 'Python',
        database: 'CSV/Parquet'
      },
      {
        id: 'python-sklearn-postgres',
        name: 'Python + Scikit-learn + PostgreSQL',
        description: 'Machine learning',
        frontend_framework: 'Jupyter Notebooks',
        backend_language: 'Python',
        database: 'PostgreSQL'
      },
      {
        id: 'r-shiny-postgres',
        name: 'R + Shiny + PostgreSQL',
        description: 'Statistical analysis with web interface',
        frontend_framework: 'Shiny',
        backend_language: 'R',
        database: 'PostgreSQL'
      },
      {
        id: 'spark-scala',
        name: 'Apache Spark + Scala',
        description: 'Big data processing',
        frontend_framework: 'Spark UI',
        backend_language: 'Scala',
        database: 'HDFS/S3'
      },
      {
        id: 'tensorflow-python',
        name: 'TensorFlow + Python + PostgreSQL',
        description: 'Deep learning',
        frontend_framework: 'TensorBoard',
        backend_language: 'Python',
        database: 'PostgreSQL'
      },
      {
        id: 'streamlit-python',
        name: 'Streamlit + Python',
        description: 'Data apps',
        frontend_framework: 'Streamlit',
        backend_language: 'Python',
        database: 'PostgreSQL'
      },
      {
        id: 'powerbi-sqlserver',
        name: 'Power BI + SQL Server',
        description: 'Business intelligence',
        frontend_framework: 'Power BI',
        backend_language: 'DAX/SQL',
        database: 'SQL Server'
      }
    ]
  },
  'ecommerce': {
    label: 'E-commerce Platform',
    description: 'Online stores and marketplace applications',
    stacks: [
      {
        id: 'shopify-liquid',
        name: 'Shopify + Liquid',
        description: 'Hosted e-commerce',
        frontend_framework: 'Liquid Templates',
        backend_language: 'Shopify',
        database: 'Shopify'
      },
      {
        id: 'woocommerce-wordpress',
        name: 'WooCommerce + WordPress',
        description: 'WordPress-based store',
        frontend_framework: 'WordPress',
        backend_language: 'PHP',
        database: 'MySQL'
      },
      {
        id: 'magento-mysql',
        name: 'Magento + MySQL',
        description: 'Enterprise e-commerce',
        frontend_framework: 'Magento',
        backend_language: 'PHP',
        database: 'MySQL'
      },
      {
        id: 'nextjs-stripe-postgres',
        name: 'Next.js + Stripe + PostgreSQL',
        description: 'Custom storefront',
        frontend_framework: 'Next.js',
        backend_language: 'JavaScript/Node.js',
        database: 'PostgreSQL'
      },
      {
        id: 'react-shopify-storefront',
        name: 'React + Shopify Storefront API',
        description: 'Headless commerce',
        frontend_framework: 'React',
        backend_language: 'Shopify API',
        database: 'Shopify'
      },
      {
        id: 'medusa-react-postgres',
        name: 'Medusa + React + PostgreSQL',
        description: 'Open source commerce',
        frontend_framework: 'React',
        backend_language: 'JavaScript/Node.js',
        database: 'PostgreSQL'
      }
    ]
  },
  'cms': {
    label: 'Content Management System',
    description: 'Websites with content management capabilities',
    stacks: [
      {
        id: 'wordpress-mysql',
        name: 'WordPress + MySQL',
        description: 'Popular CMS',
        frontend_framework: 'WordPress',
        backend_language: 'PHP',
        database: 'MySQL'
      },
      {
        id: 'drupal-postgres',
        name: 'Drupal + PostgreSQL',
        description: 'Enterprise CMS',
        frontend_framework: 'Drupal',
        backend_language: 'PHP',
        database: 'PostgreSQL'
      },
      {
        id: 'strapi-react-postgres',
        name: 'Strapi + React + PostgreSQL',
        description: 'Headless CMS',
        frontend_framework: 'React',
        backend_language: 'JavaScript/Node.js',
        database: 'PostgreSQL'
      },
      {
        id: 'ghost-mysql',
        name: 'Ghost + MySQL',
        description: 'Publishing platform',
        frontend_framework: 'Ghost',
        backend_language: 'JavaScript/Node.js',
        database: 'MySQL'
      },
      {
        id: 'contentful-gatsby',
        name: 'Contentful + Gatsby + GraphQL',
        description: 'JAMstack CMS',
        frontend_framework: 'Gatsby',
        backend_language: 'JavaScript/Node.js',
        database: 'Contentful'
      },
      {
        id: 'sanity-nextjs',
        name: 'Sanity + Next.js',
        description: 'Headless CMS with React',
        frontend_framework: 'Next.js',
        backend_language: 'JavaScript/Node.js',
        database: 'Sanity'
      }
    ]
  },
  'game': {
    label: 'Game Development',
    description: 'Video games and interactive applications',
    stacks: [
      {
        id: 'unity-csharp',
        name: 'Unity + C#',
        description: 'Cross-platform game engine',
        frontend_framework: 'Unity',
        backend_language: 'C#',
        database: 'Unity Cloud'
      },
      {
        id: 'unreal-cpp',
        name: 'Unreal Engine + C++',
        description: 'AAA game development',
        frontend_framework: 'Unreal Engine',
        backend_language: 'C++',
        database: 'Unreal Backend'
      },
      {
        id: 'godot-gdscript',
        name: 'Godot + GDScript',
        description: 'Open source game engine',
        frontend_framework: 'Godot',
        backend_language: 'GDScript',
        database: 'SQLite'
      },
      {
        id: 'react-phaser',
        name: 'React + Phaser',
        description: 'Web-based games',
        frontend_framework: 'React',
        backend_language: 'JavaScript',
        database: 'LocalStorage'
      },
      {
        id: 'javascript-canvas',
        name: 'JavaScript + HTML5 Canvas',
        description: 'Browser games',
        frontend_framework: 'HTML5 Canvas',
        backend_language: 'JavaScript',
        database: 'LocalStorage'
      },
      {
        id: 'python-pygame',
        name: 'Python + Pygame',
        description: 'Simple 2D games',
        frontend_framework: 'Pygame',
        backend_language: 'Python',
        database: 'SQLite'
      }
    ]
  },
  'iot': {
    label: 'IoT/Embedded System',
    description: 'Internet of Things and embedded applications',
    stacks: [
      {
        id: 'arduino-cpp',
        name: 'Arduino + C++',
        description: 'Microcontroller development',
        frontend_framework: 'Arduino IDE',
        backend_language: 'C++',
        database: 'EEPROM'
      },
      {
        id: 'raspberry-pi-python',
        name: 'Raspberry Pi + Python',
        description: 'Single-board computer projects',
        frontend_framework: 'Python GUI',
        backend_language: 'Python',
        database: 'SQLite'
      },
      {
        id: 'esp32-cpp',
        name: 'ESP32 + C++',
        description: 'WiFi-enabled microcontroller',
        frontend_framework: 'Web Interface',
        backend_language: 'C++',
        database: 'SPIFFS'
      },
      {
        id: 'nodejs-mqtt-influxdb',
        name: 'Node.js + MQTT + InfluxDB',
        description: 'IoT data collection',
        frontend_framework: 'React Dashboard',
        backend_language: 'JavaScript/Node.js',
        database: 'InfluxDB'
      },
      {
        id: 'python-flask-sqlite',
        name: 'Python + Flask + SQLite',
        description: 'IoT web interface',
        frontend_framework: 'Flask Templates',
        backend_language: 'Python',
        database: 'SQLite'
      },
      {
        id: 'rust-embedded',
        name: 'Rust + Embedded',
        description: 'System-level IoT',
        frontend_framework: 'Embedded UI',
        backend_language: 'Rust',
        database: 'Flash Storage'
      }
    ]
  },
  'automation': {
    label: 'Automation/Script',
    description: 'Task automation and scripting projects',
    stacks: [
      {
        id: 'python-selenium',
        name: 'Python + Selenium',
        description: 'Web automation',
        frontend_framework: 'Command Line',
        backend_language: 'Python',
        database: 'SQLite'
      },
      {
        id: 'python-pandas-excel',
        name: 'Python + Pandas + Excel',
        description: 'Data processing automation',
        frontend_framework: 'Excel/CSV',
        backend_language: 'Python',
        database: 'Excel/CSV'
      },
      {
        id: 'nodejs-puppeteer',
        name: 'Node.js + Puppeteer',
        description: 'Browser automation',
        frontend_framework: 'Command Line',
        backend_language: 'JavaScript/Node.js',
        database: 'JSON Files'
      },
      {
        id: 'powershell-windows',
        name: 'PowerShell + Windows',
        description: 'Windows automation',
        frontend_framework: 'Command Line',
        backend_language: 'PowerShell',
        database: 'Registry/Files'
      },
      {
        id: 'bash-linux',
        name: 'Bash + Linux',
        description: 'System administration',
        frontend_framework: 'Command Line',
        backend_language: 'Bash',
        database: 'Config Files'
      },
      {
        id: 'python-apis',
        name: 'Python + APIs',
        description: 'API automation and integration',
        frontend_framework: 'Command Line',
        backend_language: 'Python',
        database: 'SQLite'
      }
    ]
  }
};

// Helper function to get all application types
export const getApplicationTypes = () => {
  return Object.entries(TECH_STACK_CONFIG).map(([key, value]) => ({
    id: key,
    label: value.label,
    description: value.description
  }));
};

// Helper function to get tech stacks for a specific application type
export const getTechStacksForType = (applicationType) => {
  return TECH_STACK_CONFIG[applicationType]?.stacks || [];
};

// Helper function to get a specific tech stack by ID
export const getTechStackById = (applicationType, techStackId) => {
  const stacks = getTechStacksForType(applicationType);
  return stacks.find(stack => stack.id === techStackId);
};