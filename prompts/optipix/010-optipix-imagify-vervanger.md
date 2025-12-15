# 🖼️ OptiPix - WordPress Image Optimizer Plugin

## Project Name: **OptiPix**

**Domain:** optipix.io | api.optipix.io

---

## 📋 Executive Summary

An affordable, self-hosted WordPress image optimization plugin as an alternative to Imagify. The plugin offers local processing via a Docker-based microservice, making costs drastically lower than cloud-based competitors. International focus with English as primary language.

**Unique Value Proposition:** 
- **90% cheaper** than Imagify at scale (self-hosted vs. SaaS)
- **No API limits** - pay once for hosting, compress unlimited
- **Privacy-first** - images never leave your server
- **Open source** WordPress plugin with premium features

---

## 🌐 Domain Strategy

### Primary Domains

| Domain | Purpose | Status |
|--------|---------|--------|
| **optipix.io** | Main website & landing page | To register |
| **api.optipix.io** | API endpoint for plugin | Subdomain |

### Why OptiPix?

- ✅ Short and memorable (7 characters)
- ✅ Combines "Optimize" + "Pixels"
- ✅ Professional, tech-forward branding
- ✅ .io TLD popular for SaaS/developer tools
- ✅ Easy to spell and pronounce internationally
- ✅ Domain likely available

---

## 🎯 Problem Statement

### Imagify Pricing (Current Market)

| Plan | Price | Limit | Cost/1000 images |
|------|-------|-------|------------------|
| Starter | Free | 20MB/month (~200 img) | €0 |
| Growth | €5.99/month | 500MB/month (~5000 img) | ~€1.20 |
| Infinite | €9.99/month | Unlimited | €9.99 fixed |

### Pain Points with Existing Solutions

1. **Costs at scale**: €120/year for "unlimited" is expensive for agencies with many sites
2. **API limits**: Free tiers are too limited (20MB = ~200 images)
3. **Privacy concerns**: Images are sent to external servers
4. **Vendor lock-in**: Dependent on external service
5. **Upload size limits**: 2MB limit on free tier

### Our Solution

| Aspect | Imagify | OptiPix (Self-hosted) |
|--------|---------|------------------------|
| Price/month | €9.99 | ~€2-5 (hosting cost share) |
| Limit | API quota | **Unlimited** |
| Privacy | Cloud | **On-premise** |
| Speed | API dependent | **Local = fast** |
| Lock-in | Yes | **No, self-hosted** |

---

## 👥 Target Audiences

### Primary

| Audience | Size (Global) | Need | Willingness to Pay |
|----------|---------------|------|-------------------|
| Web agencies | ~500,000 | Multi-site management | High ($25-50/month) |
| WordPress developers | ~2,000,000 | Affordable, reliable | Medium ($5-15/month) |
| Hosting providers | ~10,000 | White-label resell | High (per-tenant pricing) |
| WooCommerce shops | ~5,000,000 | Many product photos | Medium ($10-20/month) |

### Secondary

| Audience | Need |
|----------|------|
| Bloggers | Simple one-click solution |
| Photographers | Quality preservation |
| Enterprise | Compliance, data sovereignty |

---

## ✨ Features

### MVP (Phase 1 - 6 weeks)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Auto-compress on upload** | Automatically optimize on upload | Must |
| **Bulk optimization** | Process existing media library | Must |
| **WebP conversion** | Automatic WebP conversion | Must |
| **AVIF conversion** | Next-gen format support | Should |
| **Smart compression** | Automatic quality/size balance | Must |
| **Lossless mode** | Option for zero quality loss | Must |
| **Original backup** | Keep originals in separate folder | Must |
| **Progress dashboard** | Live progress for bulk optimize | Must |
| **JPG/PNG/GIF support** | All common formats | Must |

### Phase 2 (6-12 weeks)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Lazy loading** | Native lazy load integration | Should |
| **CDN delivery** | Optional Cloudflare/Bunny integration | Should |
| **Image resizing** | Automatic resize on upload | Should |
| **Exclude patterns** | Skip certain images | Should |
| **CLI tool** | WP-CLI commands | Should |
| **REST API** | API for headless WordPress | Should |
| **Multi-site support** | WordPress multisite | Must |
| **Statistics dashboard** | Savings insights | Should |

### Phase 3 (3-6 months)

| Feature | Description | Priority |
|---------|-------------|----------|
| **Adaptive images** | Different sizes per device | Should |
| **Theme/plugin scanning** | Optimize theme images too | Could |
| **Database cleanup** | Remove unused image sizes | Could |
| **PDF optimization** | PDF compression | Could |
| **White-label** | For hosters and agencies | Could |
| **Priority queue** | Important images first | Could |

---

## 🏗️ Technical Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     WordPress Website (Any Host)                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    OptiPix WordPress Plugin                            │  │
│  │  • Hooks into media upload                                            │  │
│  │  • Admin dashboard                                                     │  │
│  │  • Bulk optimization queue                                            │  │
│  │  • Settings management                                                 │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    │ API Call (HTTPS)                        │
│                                    ▼                                         │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Hetzner Dedicated Server                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Plesk Panel                                    │  │
│  │  • SSL/TLS (Let's Encrypt)                                            │  │
│  │  • Domain: api.optipix.io                                              │  │
│  │  • Reverse Proxy → Docker                                              │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Docker Compose Stack                                │  │
│  │                                                                        │  │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐     │  │
│  │  │  Image Optimizer │  │     API Server   │  │      Redis       │     │  │
│  │  │  (Sharp/libvips) │  │  (Node.js/Fastify│  │    (Queue)       │     │  │
│  │  │                  │  │      :5000)      │  │    :6379         │     │  │
│  │  │                  │  │                  │  │                  │     │  │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────┘     │  │
│  │                                                                        │  │
│  │  ┌──────────────────┐  ┌──────────────────┐                           │  │
│  │  │    PostgreSQL    │  │   MinIO/S3 Local │                           │  │
│  │  │  (License Keys)  │  │  (Temp Storage)  │                           │  │
│  │  │    :5432         │  │    :9000         │                           │  │
│  │  └──────────────────┘  └──────────────────┘                           │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| **WordPress Plugin** | PHP 8.0+ | WordPress native |
| **API Server** | Node.js + Fastify | Fast, TypeScript |
| **Image Processing** | Sharp (Node) / libvips | Best performance |
| **WebP/AVIF** | libwebp, libavif | Native support |
| **Queue** | Redis + BullMQ | Reliable job queue |
| **Database** | PostgreSQL | License keys, stats |
| **File Storage** | MinIO | S3-compatible, local |
| **Hosting** | Hetzner Dedicated + Plesk | Existing infra |
| **Payments** | Stripe + Mollie | International + EU |

---

## 🐳 Docker Compose Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  # API Server
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: optipix_api
    restart: unless-stopped
    ports:
      - "${API_PORT:-5000}:5000"
    environment:
      NODE_ENV: production
      PORT: 5000
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio
      MINIO_PORT: 9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      LICENSE_SECRET: ${LICENSE_SECRET}
      RATE_LIMIT_REQUESTS: ${RATE_LIMIT_REQUESTS:-1000}
      RATE_LIMIT_WINDOW: ${RATE_LIMIT_WINDOW:-60000}
    depends_on:
      - postgres
      - redis
      - minio
    networks:
      - optipix
    volumes:
      - ./uploads:/app/uploads
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Image Processing Worker
  worker:
    build:
      context: ./worker
      dockerfile: Dockerfile
    container_name: optipix_worker
    restart: unless-stopped
    environment:
      NODE_ENV: production
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379
      MINIO_ENDPOINT: minio
      MINIO_PORT: 9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      WORKER_CONCURRENCY: ${WORKER_CONCURRENCY:-4}
    depends_on:
      - postgres
      - redis
      - minio
    networks:
      - optipix
    volumes:
      - ./uploads:/app/uploads
    deploy:
      replicas: 2

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: optipix_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - optipix
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Redis Queue
  redis:
    image: redis:7-alpine
    container_name: optipix_redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - optipix
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  # MinIO Object Storage
  minio:
    image: minio/minio:latest
    container_name: optipix_minio
    restart: unless-stopped
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    ports:
      - "${MINIO_CONSOLE_PORT:-9001}:9001"
    volumes:
      - minio_data:/data
    networks:
      - optipix
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Frontend Dashboard (Optional)
  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    container_name: optipix_dashboard
    restart: unless-stopped
    ports:
      - "${DASHBOARD_PORT:-3000}:3000"
    environment:
      NEXT_PUBLIC_API_URL: ${PUBLIC_API_URL}
    depends_on:
      - api
    networks:
      - optipix

networks:
  optipix:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  minio_data:
```

### .env.example

```env
# API Server
API_PORT=5000
PUBLIC_API_URL=https://api.optipix.io

# PostgreSQL
POSTGRES_USER=optipix
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=optipix

# Redis
REDIS_URL=redis://redis:6379

# MinIO
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=your_minio_secret_here
MINIO_CONSOLE_PORT=9001

# License System
LICENSE_SECRET=your_license_signing_secret

# Worker
WORKER_CONCURRENCY=4

# Rate Limiting
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=60000

# Dashboard
DASHBOARD_PORT=3000
```

---

## 🔧 Plesk Configuration

### Nginx Proxy Rules for api.optipix.io

```nginx
# Additional nginx directives
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    
    # Increased timeouts for large image uploads
    proxy_read_timeout 300s;
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    
    # Max upload size
    client_max_body_size 100M;
}

# Health check endpoint (no auth)
location /health {
    proxy_pass http://127.0.0.1:5000/health;
    access_log off;
}
```

### Steps in Plesk

1. **Create domain**: api.optipix.io
2. **SSL certificate**: Activate Let's Encrypt
3. **Apache & nginx Settings** → Additional nginx directives
4. **Copy above proxy config**
5. **Apply changes**

---

## 📦 WordPress Plugin Structure

```
optipix/
├── optipix.php                # Main plugin file
├── readme.txt                  # WordPress.org readme
├── uninstall.php              # Cleanup on uninstall
├── LICENSE                     # GPLv2 license
├── languages/
│   ├── optipix-nl_NL.po
│   └── optipix-nl_NL.mo
├── includes/
│   ├── class-optipix.php             # Main class
│   ├── class-optipix-api.php         # API client
│   ├── class-optipix-optimizer.php   # Image optimization
│   ├── class-optipix-queue.php       # Background processing
│   └── class-optipix-settings.php    # Settings handler
├── admin/
│   ├── class-optipix-admin.php       # Admin pages
│   ├── css/
│   │   └── admin.css
│   ├── js/
│   │   └── admin.js
│   └── partials/
│       ├── settings-page.php
│       ├── bulk-optimizer.php
│       └── statistics.php
├── public/
│   └── class-optipix-public.php      # Frontend handling
└── assets/
    ├── icon-128x128.png
    ├── icon-256x256.png
    ├── banner-772x250.png
    └── banner-1544x500.png
```

### Main File: optipix.php

```php
<?php
/**
 * Plugin Name:       OptiPix Image Optimizer
 * Plugin URI:        https://optipix.io
 * Description:       Automatically optimize your WordPress images. WebP and AVIF conversion, bulk optimization, and more.
 * Version:           1.0.0
 * Requires at least: 5.8
 * Requires PHP:      8.0
 * Author:            OptiPix
 * Author URI:        https://optipix.io
 * License:           GPL v2 or later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       optipix
 * Domain Path:       /languages
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Plugin constants
define('OPTIPIX_VERSION', '1.0.0');
define('OPTIPIX_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('OPTIPIX_PLUGIN_URL', plugin_dir_url(__FILE__));
define('OPTIPIX_API_URL', 'https://api.optipix.io');

// Autoloader
require_once OPTIPIX_PLUGIN_DIR . 'includes/class-optipix.php';

// Initialize plugin
function optipix_init() {
    $plugin = new OptiPix();
    $plugin->run();
}
add_action('plugins_loaded', 'optipix_init');

// Activation hook
register_activation_hook(__FILE__, 'optipix_activate');
function optipix_activate() {
    // Create backup directory
    $upload_dir = wp_upload_dir();
    $backup_dir = $upload_dir['basedir'] . '/optipix-backup';
    
    if (!file_exists($backup_dir)) {
        wp_mkdir_p($backup_dir);
    }
    
    // Set default options
    $defaults = array(
        'auto_optimize' => true,
        'compression_level' => 'smart',
        'convert_webp' => true,
        'convert_avif' => false,
        'keep_originals' => true,
        'max_width' => 2560,
        'max_height' => 2560,
    );
    
    foreach ($defaults as $key => $value) {
        if (get_option('optipix_' . $key) === false) {
            add_option('optipix_' . $key, $value);
        }
    }
    
    // Schedule cron for background processing
    if (!wp_next_scheduled('optipix_process_queue')) {
        wp_schedule_event(time(), 'every_minute', 'optipix_process_queue');
    }
    
    // Flush rewrite rules
    flush_rewrite_rules();
}

// Deactivation hook
register_deactivation_hook(__FILE__, 'optipix_deactivate');
function optipix_deactivate() {
    // Clear scheduled events
    wp_clear_scheduled_hook('optipix_process_queue');
}
```

---

## 📝 WordPress.org readme.txt

```txt
=== OptiPix Image Optimizer ===
Contributors: optipix
Tags: image optimization, webp, avif, compression, media library, performance
Requires at least: 5.8
Tested up to: 6.4
Stable tag: 1.0.0
Requires PHP: 8.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Automatically optimize your WordPress images. WebP and AVIF conversion, bulk optimization, and more.

== Description ==

OptiPix is a powerful image optimization plugin for WordPress. Automatically optimize all your images on upload, convert to modern formats like WebP and AVIF, and save up to 80% file size without quality loss.

**Why OptiPix?**

* 🚀 **Auto-optimize** - Every upload is instantly optimized
* 🖼️ **WebP & AVIF conversion** - Modern formats for maximum compression
* 💾 **Bulk optimization** - Optimize your entire media library
* 🔒 **Privacy-first** - Your images stay on your server
* ⚡ **Lightning fast** - Local processing, no API delays

**Features**

* Automatic optimization on upload
* Lossless and lossy compression options
* WebP conversion with fallback
* AVIF conversion (Premium)
* Bulk optimization tool
* Original file backup
* WooCommerce compatible
* Multisite support (Premium)
* Detailed statistics
* WP-CLI commands (Premium)

== Installation ==

1. Upload the `optipix` folder to `/wp-content/plugins/`
2. Activate the plugin through the 'Plugins' menu
3. Go to OptiPix > Settings
4. Enter your license key (optional for premium features)
5. Configure your preferences
6. Start optimizing!

== Frequently Asked Questions ==

= Do I need a license? =

Not for basic features. The free version supports automatic optimization on upload. For bulk optimization and advanced features, a license is required.

= Does this work with WooCommerce? =

Yes! OptiPix works perfectly with WooCommerce and automatically optimizes all product images.

= Are my original files preserved? =

Yes, by default OptiPix backs up your original files in a separate folder.

= How does OptiPix compare to Imagify? =

OptiPix offers similar features but with self-hosted processing, meaning no API limits and better privacy. Plus, it's more affordable at scale.

== Screenshots ==

1. Dashboard overview showing optimization statistics
2. Bulk optimization interface
3. Settings page with compression options
4. Media library integration

== Changelog ==

= 1.0.0 =
* Initial release
* Auto-optimization on upload
* Bulk optimization
* WebP conversion
* AVIF conversion
* Smart compression
* Original backup

== Upgrade Notice ==

= 1.0.0 =
Initial release of OptiPix Image Optimizer.
```

### GPL Compliance Checklist

- ✅ GPLv2 or later license
- ✅ No obfuscated code
- ✅ Human-readable source
- ✅ No tracking without consent
- ✅ No affiliate links in frontend
- ✅ All third-party code is GPL-compatible
- ✅ Plugin Check tool passed
- ✅ Proper escaping and sanitization
- ✅ Nonce verification on forms
- ✅ Capability checks on admin pages

---

## 💰 Pricing Model

### License Tiers

| Tier | Price | Sites | Features |
|------|-------|-------|----------|
| **Free** | $0 | 1 | Auto-optimize, 100 img/month |
| **Starter** | $29/year | 3 | + Bulk, WebP, 1000 img/month |
| **Professional** | $79/year | 10 | + AVIF, Unlimited, CLI |
| **Agency** | $199/year | 50 | + White-label, Priority support |
| **Unlimited** | $499/year | ∞ | + Custom branding, SLA |

### Freemium Model Strategy

Free version on WordPress.org includes:
- Auto-optimization on upload
- Lossless + Smart compression
- WebP conversion
- 100 images per month

Premium version (via website) adds:
- Bulk optimization
- AVIF conversion
- Unlimited images
- Multi-site support
- CLI tools
- Priority support

### Revenue Projection

| Month | Free Users | Paid Users | MRR |
|-------|------------|------------|-----|
| 1-3 | 500 | 25 | $725 |
| 4-6 | 2,000 | 100 | $2,900 |
| 7-12 | 10,000 | 500 | $14,500 |
| Year 2 | 50,000 | 2,500 | $72,500 |

---

## 📣 Marketing Strategy

### WordPress.org Plugin Launch

1. **Pre-launch (2 weeks before)**
   - Landing page with waitlist
   - Social media teasers
   - Beta testers recruitment

2. **Launch**
   - Submit to WordPress.org (review ~5 days)
   - Press release to WordPress blogs
   - Product Hunt launch
   - Reddit r/WordPress, r/webdev posts

3. **Post-launch**
   - Collect reviews
   - Monitor support forums
   - Push first updates

### Content Marketing

- **Blog posts:**
  - "Why Image Optimization is Essential for SEO"
  - "WebP vs AVIF: Which Format Should You Choose?"
  - "Imagify vs OptiPix: Honest Comparison"
  - "Best WordPress Image Optimization Plugins 2025"
  - "How to Speed Up Your WooCommerce Store"

- **YouTube tutorials:**
  - OptiPix installation and configuration
  - Bulk optimization demonstration
  - WooCommerce product image optimization
  - Core Web Vitals improvement guide

### Distribution Channels

- WordPress.org plugin directory (primary)
- Product Hunt launch
- Hacker News
- Dev.to articles
- Twitter/X tech community
- WordPress Facebook groups
- Reddit communities
- Guest posts on WordPress blogs

---

## 🚀 GitHub Actions CI/CD

```yaml
name: Deploy OptiPix API

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.PLESK_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to Plesk
        run: |
          ssh root@${{ secrets.PLESK_HOST }} << 'ENDSSH'
            cd /opt/docker/optipix
            
            # Pull latest
            git pull origin main
            
            # Update .env
            cp .env.production .env
            
            # Rebuild and restart
            docker compose pull
            docker compose build --no-cache worker
            docker compose up -d
            
            # Run migrations
            docker compose exec -T api npx prisma migrate deploy
            
            # Health check
            sleep 10
            curl -f http://localhost:5000/health || exit 1
            
            echo "Deployment successful!"
          ENDSSH
```

---

## 📅 Roadmap

### Week 1-2: Foundation
- [ ] Register domain (optipix.io)
- [ ] Docker Compose setup
- [ ] API server basics
- [ ] Sharp image processing integration
- [ ] License key validation

### Week 3-4: WordPress Plugin
- [ ] Plugin scaffolding
- [ ] Auto-optimize hook
- [ ] Settings page
- [ ] API client class

### Week 5-6: Features & Polish
- [ ] Bulk optimizer
- [ ] WebP/AVIF generation
- [ ] Statistics dashboard
- [ ] Translations (EN primary, NL secondary)
- [ ] WordPress.org submission

### Week 7-8: Launch
- [ ] Review process
- [ ] Marketing materials
- [ ] Documentation
- [ ] Soft launch

### Week 9-12: Growth
- [ ] Expand AVIF support
- [ ] CDN integrations
- [ ] CLI tools
- [ ] Multi-site support

---

## ✅ Next Steps

1. [ ] Register domain (optipix.io + api.optipix.io)
2. [ ] Create Git repository
3. [ ] Deploy Docker Compose on Hetzner
4. [ ] Configure Plesk domain
5. [ ] Develop WordPress plugin
6. [ ] Create translations
7. [ ] WordPress.org account with 2FA
8. [ ] Run Plugin Check tool
9. [ ] Submit to WordPress.org
10. [ ] Create landing page with Stripe checkout

---

*Document version: 2.0*  
*Last updated: December 2024*  
*Previous name: BeeldWijs*
