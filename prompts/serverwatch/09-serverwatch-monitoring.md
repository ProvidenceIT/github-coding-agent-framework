# 🔍 ServerWatch - Monitoring Platform Competitor

## Projectnaam: **ServerWatch** / **MonitorWijs** / **UptimeNL**

---

## 📋 Executive Summary

Een moderne, betaalbare monitoring oplossing voor servers en websites. Direct concurrent van 360 Monitoring maar met betere prijs/kwaliteit verhouding en meer flexibiliteit. Specifieke focus op Plesk servers en Nederlandse hosters.

**Doel:** 360 Monitoring verslaan op prijs (€9,99 vs €24,99) terwijl we dezelfde of betere features bieden.

---

## 🌐 Domeinnaam Suggesties (.nl)

### Primaire keuzes:

| Domein | Opmerking | Geschatte prijs |
|--------|-----------|-----------------|
| **serverwatch.nl** | Direct duidelijk, professioneel | €10/jaar |
| **monitorwijs.nl** | Past bij "Wijs" branding familie | €10/jaar |
| **uptimecheck.nl** | Functioneel, SEO-vriendelijk | €10/jaar |
| **serverwacht.nl** | Nederlands, uniek | €10/jaar |
| **hostmonitor.nl** | Voor hosters | €10/jaar |
| **pleskwatch.nl** | Niche, Plesk focus | €10/jaar |
| **sitewacht.nl** | Kort, Nederlands | €10/jaar |
| **pingmonitor.nl** | Technisch, duidelijk | €10/jaar |

### Aanbeveling:
1. **serverwatch.nl** - Internationaal, professioneel
2. **monitorwijs.nl** - Past bij eventuele andere "Wijs" producten

---

## 🎯 Probleemstelling

### Huidige markt:
- **360 Monitoring Business**: €24,99/maand voor basic features
- **UptimeRobot**: Gratis tier is beperkt, Pro is duur
- **Pingdom**: Te duur voor kleine bedrijven (€10+/maand)
- **Self-hosted (Uptime Kuma)**: Geen enterprise features, geen distributed checks

### Specifieke pijnpunten:
1. "€25/maand voor basis monitoring is te duur"
2. "Geen goede Plesk integratie"
3. "Alerting opties zijn beperkt"
4. "Geen Nederlandse support/interface"
5. "Geen transparante prijzen voor groei"

---

## 👥 Doelgroepen

### Primair:

| Rol | Aantal (NL) | Behoefte |
|-----|-------------|----------|
| Web Agencies | ~5.000 | Multi-client monitoring |
| Freelance developers | ~20.000 | Betaalbare monitoring |
| System administrators | ~15.000 | Server health |
| Kleine hosters | ~500 | Plesk monitoring |

### Secundair:

| Rol | Behoefte |
|-----|----------|
| Enterprise IT | Compliance, SLA reporting |
| E-commerce | Uptime kritisch |
| SaaS bedrijven | API access, integrations |

---

## ✨ Features

### MVP (Fase 1 - 6 weken)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **HTTP/HTTPS Checks** | URL monitoring met response time | Must |
| **Multi-location pings** | 10+ Cloudflare Workers locaties | Must |
| **Email alerts** | Via SendGrid | Must |
| **Dashboard** | Uptime stats, response times | Must |
| **SSL monitoring** | Cert expiry alerts | Must |
| **User auth** | Magic links + password | Must |
| **Stripe billing** | €4,99/€9,99/€19,99 plans | Must |

### Fase 2 (6-12 weken)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Server agent** | CPU/RAM/Disk metrics | Must |
| **Slack/Discord/Telegram** | Multi-channel alerts | Must |
| **Status pages** | Public status pages | Should |
| **API access** | REST API | Should |
| **TCP/ICMP checks** | Port en ping monitoring | Should |
| **Webhook alerts** | Custom integrations | Should |

### Fase 3 (12-20 weken)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Plesk integration** | Native Plesk plugin | Must |
| **Incident management** | Auto incidents | Should |
| **SLA reporting** | Monthly reports | Should |
| **Team management** | Multi-user access | Should |
| **DNS monitoring** | DNS propagation | Should |
| **Maintenance windows** | Scheduled downtime | Should |

---

## 🏗️ Technische Architectuur

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Internet                                          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
          ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ Cloudflare CDN  │  │  Cloudflare     │  │  Cloudflare     │
│ (Marketing)     │  │  Workers        │  │  Workers        │
│                 │  │  (EU Locations) │  │  (US/Asia)      │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │         ┌──────────┴──────────┐         │
         │         │                     │         │
         ▼         ▼                     ▼         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      Hetzner Dedicated Server                                │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         Plesk Panel                                    │  │
│  │  • SSL/TLS (Let's Encrypt via Cloudflare DNS)                         │  │
│  │  • Domain: serverwatch.nl                                              │  │
│  │  • Docker Proxy Rules                                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│                                    ▼                                         │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Docker Compose Stack                                │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │   Frontend   │  │   Backend    │  │   Worker     │                 │  │
│  │  │   Next.js    │  │   Fastify    │  │   BullMQ     │                 │  │
│  │  │   :3000      │  │   :5000      │  │   Jobs       │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  │                                                                        │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │  │
│  │  │  PostgreSQL  │  │    Redis     │  │  TimescaleDB │                 │  │
│  │  │   :5432      │  │    :6379     │  │  (metrics)   │                 │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         External Services                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  SendGrid   │  │   Stripe    │  │   Twilio    │  │  PagerDuty  │        │
│  │   (Email)   │  │  (Payments) │  │    (SMS)    │  │  (On-call)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cloudflare Workers - Distributed Ping Network

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    Cloudflare Workers Network                             │
│                                                                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ Amsterdam   │  │ Frankfurt   │  │   London    │  │   Paris     │     │
│  │   (AMS)     │  │    (FRA)    │  │    (LHR)    │  │   (CDG)     │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │                │             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ New York    │  │ San Jose    │  │  Singapore  │  │   Sydney    │     │
│  │   (EWR)     │  │    (SJC)    │  │    (SIN)    │  │   (SYD)     │     │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘     │
│         │                │                │                │             │
│         └────────────────┴────────────────┴────────────────┘             │
│                                   │                                       │
│                                   ▼                                       │
│                         ┌─────────────────┐                              │
│                         │  Results Queue  │                              │
│                         │    (KV Store)   │                              │
│                         └────────┬────────┘                              │
│                                  │                                       │
└──────────────────────────────────┼───────────────────────────────────────┘
                                   │
                                   ▼
                          Backend API (webhook)
```

---

## 🐳 Docker Compose Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  # Frontend - Next.js Marketing + App
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-https://serverwatch.nl/api}
        - NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${STRIPE_PUBLISHABLE_KEY}
    container_name: serverwatch_frontend
    restart: unless-stopped
    ports:
      - "${FRONTEND_PORT:-3000}:3000"
    environment:
      NODE_ENV: production
    depends_on:
      - backend
    networks:
      - serverwatch_network

  # Backend - Fastify API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: serverwatch_backend
    restart: unless-stopped
    ports:
      - "${BACKEND_PORT:-5000}:5000"
    environment:
      NODE_ENV: production
      PORT: 5000
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379
      
      # Auth
      JWT_SECRET: ${JWT_SECRET}
      JWT_REFRESH_SECRET: ${JWT_REFRESH_SECRET}
      
      # Email (SendGrid)
      SENDGRID_API_KEY: ${SENDGRID_API_KEY}
      SENDGRID_FROM_EMAIL: ${SENDGRID_FROM_EMAIL:-noreply@serverwatch.nl}
      
      # SMS (Twilio)
      TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID}
      TWILIO_AUTH_TOKEN: ${TWILIO_AUTH_TOKEN}
      TWILIO_FROM_NUMBER: ${TWILIO_FROM_NUMBER}
      
      # Payments (Stripe)
      STRIPE_SECRET_KEY: ${STRIPE_SECRET_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
      
      # Cloudflare Workers
      CF_WORKER_AUTH_TOKEN: ${CF_WORKER_AUTH_TOKEN}
      
      # App config
      FRONTEND_URL: ${FRONTEND_URL:-https://serverwatch.nl}
      CHECK_INTERVAL_SECONDS: ${CHECK_INTERVAL_SECONDS:-30}
    volumes:
      - logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - serverwatch_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Worker - Background jobs (alerts, reports)
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: serverwatch_worker
    restart: unless-stopped
    environment:
      NODE_ENV: production
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379
      SENDGRID_API_KEY: ${SENDGRID_API_KEY}
      SENDGRID_FROM_EMAIL: ${SENDGRID_FROM_EMAIL}
      TWILIO_ACCOUNT_SID: ${TWILIO_ACCOUNT_SID}
      TWILIO_AUTH_TOKEN: ${TWILIO_AUTH_TOKEN}
      TWILIO_FROM_NUMBER: ${TWILIO_FROM_NUMBER}
      SLACK_WEBHOOK_ENABLED: "true"
      TELEGRAM_BOT_TOKEN: ${TELEGRAM_BOT_TOKEN}
      DISCORD_WEBHOOK_ENABLED: "true"
    depends_on:
      - postgres
      - redis
    networks:
      - serverwatch_network
    command: npm run worker

  # Scheduler - Cron jobs for checks
  scheduler:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: serverwatch_scheduler
    restart: unless-stopped
    environment:
      NODE_ENV: production
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      REDIS_URL: redis://redis:6379
      CF_WORKER_AUTH_TOKEN: ${CF_WORKER_AUTH_TOKEN}
    depends_on:
      - postgres
      - redis
    networks:
      - serverwatch_network
    command: npm run scheduler

  # PostgreSQL + TimescaleDB for metrics
  postgres:
    image: timescale/timescaledb:latest-pg15
    container_name: serverwatch_postgres
    restart: unless-stopped
    ports:
      - "${POSTGRES_PORT:-5432}:5432"
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-serverwatch}
      POSTGRES_USER: ${POSTGRES_USER:-serverwatch}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./database/timescale.sql:/docker-entrypoint-initdb.d/02-timescale.sql
    networks:
      - serverwatch_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-serverwatch}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for queue and caching
  redis:
    image: redis:7-alpine
    container_name: serverwatch_redis
    restart: unless-stopped
    ports:
      - "${REDIS_PORT:-6379}:6379"
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - serverwatch_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  serverwatch_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  logs:
```

---

## 💾 Database Schema

```sql
-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Organizations (multi-tenant)
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    stripe_customer_id VARCHAR(255),
    stripe_subscription_id VARCHAR(255),
    subscription_tier VARCHAR(50) DEFAULT 'free',
    subscription_status VARCHAR(50) DEFAULT 'active',
    monitors_limit INTEGER DEFAULT 5,
    servers_limit INTEGER DEFAULT 1,
    check_interval_seconds INTEGER DEFAULT 60,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'member',
    email_verified BOOLEAN DEFAULT false,
    timezone VARCHAR(50) DEFAULT 'Europe/Amsterdam',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(organization_id, email)
);

-- Monitors (HTTP/HTTPS/TCP/ICMP/DNS checks)
CREATE TABLE monitors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    type VARCHAR(50) DEFAULT 'http',
    method VARCHAR(10) DEFAULT 'GET',
    timeout_ms INTEGER DEFAULT 30000,
    interval_seconds INTEGER DEFAULT 60,
    expected_status_codes INTEGER[] DEFAULT '{200,201,204,301,302}',
    expected_body TEXT,
    headers JSONB DEFAULT '{}',
    body TEXT,
    
    -- SSL specific
    ssl_check BOOLEAN DEFAULT true,
    ssl_expiry_days_warning INTEGER DEFAULT 14,
    
    -- TCP specific
    port INTEGER,
    
    -- Status
    status VARCHAR(50) DEFAULT 'active',
    current_state VARCHAR(50) DEFAULT 'unknown',
    last_check_at TIMESTAMPTZ,
    last_status_change_at TIMESTAMPTZ,
    consecutive_failures INTEGER DEFAULT 0,
    
    -- Config
    confirmation_checks INTEGER DEFAULT 3,
    locations TEXT[] DEFAULT '{"ams","fra","lhr"}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Check Results (TimescaleDB hypertable for time-series)
CREATE TABLE check_results (
    id UUID DEFAULT uuid_generate_v4(),
    monitor_id UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    location VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    response_time_ms INTEGER,
    status_code INTEGER,
    error_message TEXT,
    ssl_days_remaining INTEGER,
    headers_size INTEGER,
    body_size INTEGER,
    dns_time_ms INTEGER,
    connect_time_ms INTEGER,
    tls_time_ms INTEGER,
    ttfb_ms INTEGER,
    PRIMARY KEY (monitor_id, timestamp)
);

-- Convert to hypertable for efficient time-series storage
SELECT create_hypertable('check_results', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Compression policy (compress after 7 days)
ALTER TABLE check_results SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'monitor_id,location'
);
SELECT add_compression_policy('check_results', INTERVAL '7 days');

-- Retention policy (keep 90 days)
SELECT add_retention_policy('check_results', INTERVAL '90 days');

-- Servers (for agent-based monitoring)
CREATE TABLE servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    hostname VARCHAR(255),
    ip_address VARCHAR(45),
    agent_token VARCHAR(255) UNIQUE,
    agent_version VARCHAR(50),
    os VARCHAR(100),
    os_version VARCHAR(100),
    status VARCHAR(50) DEFAULT 'pending',
    last_seen_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Server Metrics (TimescaleDB)
CREATE TABLE server_metrics (
    server_id UUID NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    cpu_percent DECIMAL(5,2),
    memory_percent DECIMAL(5,2),
    memory_used_mb INTEGER,
    memory_total_mb INTEGER,
    disk_percent DECIMAL(5,2),
    disk_used_gb INTEGER,
    disk_total_gb INTEGER,
    network_rx_bytes BIGINT,
    network_tx_bytes BIGINT,
    load_1 DECIMAL(5,2),
    load_5 DECIMAL(5,2),
    load_15 DECIMAL(5,2),
    process_count INTEGER,
    PRIMARY KEY (server_id, timestamp)
);

SELECT create_hypertable('server_metrics', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Alert Channels
CREATE TABLE alert_channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Monitor Alert Channels (many-to-many)
CREATE TABLE monitor_alert_channels (
    monitor_id UUID REFERENCES monitors(id) ON DELETE CASCADE,
    alert_channel_id UUID REFERENCES alert_channels(id) ON DELETE CASCADE,
    PRIMARY KEY (monitor_id, alert_channel_id)
);

-- Incidents
CREATE TABLE incidents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    monitor_id UUID REFERENCES monitors(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    cause VARCHAR(255),
    status VARCHAR(50) DEFAULT 'ongoing',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert History
CREATE TABLE alerts_sent (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    incident_id UUID REFERENCES incidents(id) ON DELETE CASCADE,
    alert_channel_id UUID REFERENCES alert_channels(id) ON DELETE SET NULL,
    type VARCHAR(50) NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT
);

-- Status Pages
CREATE TABLE status_pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    slug VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    custom_domain VARCHAR(255),
    logo_url VARCHAR(512),
    favicon_url VARCHAR(512),
    header_color VARCHAR(7) DEFAULT '#10b981',
    published BOOLEAN DEFAULT true,
    show_uptime_percentage BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Status Page Monitors
CREATE TABLE status_page_monitors (
    status_page_id UUID REFERENCES status_pages(id) ON DELETE CASCADE,
    monitor_id UUID REFERENCES monitors(id) ON DELETE CASCADE,
    display_name VARCHAR(255),
    display_order INTEGER DEFAULT 0,
    PRIMARY KEY (status_page_id, monitor_id)
);

-- API Keys
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    permissions JSONB DEFAULT '["read"]',
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_monitors_org ON monitors(organization_id);
CREATE INDEX idx_monitors_status ON monitors(status, current_state);
CREATE INDEX idx_check_results_monitor_time ON check_results(monitor_id, timestamp DESC);
CREATE INDEX idx_servers_org ON servers(organization_id);
CREATE INDEX idx_incidents_org ON incidents(organization_id, status);
CREATE INDEX idx_incidents_monitor ON incidents(monitor_id, started_at DESC);
```

---

## 💰 Prijsmodel

### Vergelijking met 360 Monitoring

| Feature | 360 Monitoring Business | ServerWatch Pro |
|---------|------------------------|-----------------|
| **Prijs** | €24,99/maand | €9,99/maand |
| Websites | 50 | **Onbeperkt** |
| Servers | 10 | 25 |
| Check interval | 1 min | **30 sec** |
| Check locaties | 26 | 10 |
| Alert kanalen | 3 | **Onbeperkt** |
| SSL monitoring | ✅ | ✅ |
| Status pages | 1 | **3** |
| API access | ✅ | ✅ |
| Team members | 3 | **10** |
| Data retention | 30 dagen | **90 dagen** |

### Pricing Tiers

| Tier | Prijs | Monitors | Servers | Interval | Features |
|------|-------|----------|---------|----------|----------|
| **Free** | €0 | 5 | 1 | 5 min | Email alerts, 1 location |
| **Starter** | €4,99/mo | 25 | 5 | 1 min | + 5 locations, SSL, Slack |
| **Pro** | €9,99/mo | ∞ | 25 | 30 sec | + 10 locations, Status page, API |
| **Business** | €24,99/mo | ∞ | 100 | 15 sec | + Team, SLA reports, Phone |
| **Enterprise** | Custom | ∞ | ∞ | 10 sec | + On-prem, Custom locations |

---

## 📧 Alert Channels

### Supported Channels

| Channel | Tier | Implementation |
|---------|------|----------------|
| Email | Free | SendGrid |
| Slack | Starter | Webhook |
| Discord | Starter | Webhook |
| Telegram | Starter | Bot API |
| Microsoft Teams | Pro | Webhook |
| SMS | Pro | Twilio |
| PagerDuty | Business | API |
| Opsgenie | Business | API |
| Webhook | Starter | Custom HTTP |
| Push notifications | Pro | Web Push API |

---

## 🔧 Cloudflare Workers

### Ping Worker Code

```typescript
// worker.ts - Deployed to multiple CF edge locations
export interface Env {
  BACKEND_URL: string;
  AUTH_TOKEN: string;
}

interface CheckRequest {
  monitor_id: string;
  url: string;
  method: string;
  timeout_ms: number;
  expected_status_codes: number[];
  expected_body?: string;
  headers?: Record<string, string>;
  body?: string;
}

interface CheckResult {
  monitor_id: string;
  location: string;
  status: 'up' | 'down' | 'degraded';
  response_time_ms: number;
  status_code?: number;
  error_message?: string;
  ssl_days_remaining?: number;
  dns_time_ms?: number;
  connect_time_ms?: number;
  tls_time_ms?: number;
  ttfb_ms?: number;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Verify auth token
    const authHeader = request.headers.get('Authorization');
    if (authHeader !== `Bearer ${env.AUTH_TOKEN}`) {
      return new Response('Unauthorized', { status: 401 });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    const checks: CheckRequest[] = await request.json();
    const location = request.cf?.colo || 'unknown';
    const results: CheckResult[] = [];

    for (const check of checks) {
      const result = await performCheck(check, location);
      results.push(result);
    }

    // Send results back to backend
    await fetch(`${env.BACKEND_URL}/api/internal/check-results`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${env.AUTH_TOKEN}`,
      },
      body: JSON.stringify(results),
    });

    return new Response(JSON.stringify({ processed: results.length }), {
      headers: { 'Content-Type': 'application/json' },
    });
  },

  // Scheduled checks (Cron trigger)
  async scheduled(event: ScheduledEvent, env: Env): Promise<void> {
    // Fetch pending checks from backend
    const response = await fetch(`${env.BACKEND_URL}/api/internal/pending-checks`, {
      headers: { 'Authorization': `Bearer ${env.AUTH_TOKEN}` },
    });
    
    if (!response.ok) return;
    
    const checks: CheckRequest[] = await response.json();
    const location = 'scheduled';
    
    for (const check of checks) {
      const result = await performCheck(check, location);
      
      await fetch(`${env.BACKEND_URL}/api/internal/check-results`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${env.AUTH_TOKEN}`,
        },
        body: JSON.stringify([result]),
      });
    }
  },
};

async function performCheck(check: CheckRequest, location: string): Promise<CheckResult> {
  const startTime = performance.now();
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), check.timeout_ms);
    
    const response = await fetch(check.url, {
      method: check.method,
      headers: check.headers || {},
      body: check.body,
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    const responseTime = Math.round(performance.now() - startTime);
    const isExpectedStatus = check.expected_status_codes.includes(response.status);
    
    let bodyMatch = true;
    if (check.expected_body) {
      const body = await response.text();
      bodyMatch = body.includes(check.expected_body);
    }
    
    // Check SSL certificate
    let sslDaysRemaining: number | undefined;
    if (check.url.startsWith('https://')) {
      // Note: In real implementation, use a separate SSL check
      sslDaysRemaining = 30; // Placeholder
    }
    
    const isUp = isExpectedStatus && bodyMatch;
    
    return {
      monitor_id: check.monitor_id,
      location,
      status: isUp ? 'up' : 'down',
      response_time_ms: responseTime,
      status_code: response.status,
      ssl_days_remaining: sslDaysRemaining,
      error_message: !isUp ? `Status: ${response.status}, Body match: ${bodyMatch}` : undefined,
    };
    
  } catch (error: any) {
    const responseTime = Math.round(performance.now() - startTime);
    
    return {
      monitor_id: check.monitor_id,
      location,
      status: 'down',
      response_time_ms: responseTime,
      error_message: error.message || 'Unknown error',
    };
  }
}
```

### wrangler.toml

```toml
name = "serverwatch-ping"
main = "src/worker.ts"
compatibility_date = "2024-01-01"

# Deploy to multiple locations
routes = [
  { pattern = "ping-ams.serverwatch.nl/*", zone_name = "serverwatch.nl" },
  { pattern = "ping-fra.serverwatch.nl/*", zone_name = "serverwatch.nl" },
  { pattern = "ping-lhr.serverwatch.nl/*", zone_name = "serverwatch.nl" },
]

[triggers]
crons = ["*/1 * * * *"]  # Every minute

[vars]
BACKEND_URL = "https://serverwatch.nl"

# Secrets (add via wrangler secret put)
# AUTH_TOKEN
```

---

## 🚀 GitHub Actions CI/CD

```yaml
name: Build and Deploy

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-push:
    name: Build and Push Docker Images
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    outputs:
      backend-image: ${{ steps.image.outputs.backend }}
      frontend-image: ${{ steps.image.outputs.frontend }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
            echo "url=https://serverwatch.nl" >> $GITHUB_OUTPUT
            echo "api_url=https://serverwatch.nl/api" >> $GITHUB_OUTPUT
          else
            echo "environment=staging" >> $GITHUB_OUTPUT
            echo "url=https://staging.serverwatch.nl" >> $GITHUB_OUTPUT
            echo "api_url=https://staging.serverwatch.nl/api" >> $GITHUB_OUTPUT
          fi

      - name: Build and push backend
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.ref_name }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          target: production

      - name: Build and push frontend
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.ref_name }}
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.sha }}
          build-args: |
            NEXT_PUBLIC_API_URL=${{ steps.env.outputs.api_url }}
            NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=${{ secrets.STRIPE_PUBLISHABLE_KEY }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          target: production

      - name: Set output
        id: image
        run: |
          echo "backend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-backend:${{ github.ref_name }}" >> $GITHUB_OUTPUT
          echo "frontend=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}-frontend:${{ github.ref_name }}" >> $GITHUB_OUTPUT

  deploy-cloudflare-workers:
    name: Deploy Cloudflare Workers
    runs-on: ubuntu-latest
    needs: build-and-push
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install Wrangler
        run: npm install -g wrangler
      
      - name: Deploy Workers
        working-directory: ./workers
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
        run: |
          wrangler deploy --env production

  deploy:
    name: Deploy to Plesk Server
    runs-on: ubuntu-latest
    needs: [build-and-push, deploy-cloudflare-workers]
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
      url: https://serverwatch.nl

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Deploy to Plesk
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.PLESK_HOST }}
          username: ${{ secrets.PLESK_USER }}
          password: ${{ secrets.PLESK_SSH_PASSWORD }}
          port: ${{ secrets.PLESK_SSH_PORT }}
          timeout: 5m
          script: |
            DEPLOY_PATH="/opt/psa/var/modules/docker/stacks/serverwatch.nl"
            
            # Login to GHCR
            echo "${{ secrets.GITHUB_TOKEN }}" | sudo docker login ghcr.io -u ${{ github.actor }} --password-stdin
            
            # Pull latest images
            sudo docker pull ${{ needs.build-and-push.outputs.backend-image }}
            sudo docker pull ${{ needs.build-and-push.outputs.frontend-image }}
            
            cd $DEPLOY_PATH
            
            # Update image tags in compose file
            sudo docker compose pull
            sudo docker compose up -d --no-build
            
            # Run migrations
            sleep 10
            sudo docker compose exec -T backend npx prisma migrate deploy
            
            echo "Deployment complete!"

      - name: Health check
        run: |
          sleep 20
          response=$(curl -s -o /dev/null -w "%{http_code}" https://serverwatch.nl/health)
          if [ $response -eq 200 ]; then
            echo "✅ Health check passed"
          else
            echo "❌ Health check failed with status: $response"
            exit 1
          fi

      - name: Notify on success
        if: success()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"✅ ServerWatch deployed successfully to production"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}

      - name: Notify on failure
        if: failure()
        run: |
          curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"❌ ServerWatch deployment failed"}' \
            ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 💵 Kostenraming

### Ontwikkelkosten (MVP - 6 weken)

| Item | Uren | Totaal |
|------|------|--------|
| Backend API (Fastify + Prisma) | 80 | €6.000 |
| Frontend (Next.js) | 60 | €4.500 |
| Cloudflare Workers | 20 | €1.500 |
| Database + TimescaleDB | 15 | €1.125 |
| Auth + Stripe integration | 20 | €1.500 |
| Dashboard + Charts | 30 | €2.250 |
| Marketing website | 15 | €1.125 |
| **Totaal** | **240** | **€18.000** |

### Maandelijkse kosten (bij 100 klanten)

| Item | Kosten | Notities |
|------|--------|----------|
| Hetzner (deel van server) | €10 | Gedeeld |
| Cloudflare Workers | €5 | Gratis tier + betaald |
| SendGrid | €20 | 40K emails/maand |
| Twilio SMS | €20 | 200 SMS |
| Stripe fees | €50 | 2.9% + €0.25 |
| Domein | €1 | |
| **Totaal** | **~€106** | |

### Break-even analyse

| Klanten | MRR | Kosten | Winst |
|---------|-----|--------|-------|
| 10 | €100 | €50 | €50 |
| 50 | €500 | €80 | €420 |
| 100 | €1.000 | €106 | €894 |
| 500 | €5.000 | €200 | €4.800 |

---

## 📅 Roadmap

### Week 1-2: Foundation
- [ ] Database schema + Prisma setup
- [ ] Basic auth (magic links)
- [ ] Organization/user CRUD
- [ ] First Cloudflare Worker

### Week 3-4: Core Monitoring
- [ ] Monitor CRUD
- [ ] HTTP checks via Workers
- [ ] Check results storage (TimescaleDB)
- [ ] Basic dashboard

### Week 5-6: Alerts & Billing
- [ ] Email alerts (SendGrid)
- [ ] Incident detection
- [ ] Stripe subscription integration
- [ ] Marketing landing page

### Week 7-8: Polish & Launch
- [ ] SSL monitoring
- [ ] Multi-location dashboard
- [ ] Slack/Discord integration
- [ ] Documentation
- [ ] Beta launch

### Week 9-12: Growth Features
- [ ] Server agent
- [ ] Status pages
- [ ] API access
- [ ] Team management

---

## ✅ Volgende Stappen

1. [ ] Domein registreren (serverwatch.nl of monitorwijs.nl)
2. [ ] Stripe account opzetten
3. [ ] Cloudflare Workers account aanmaken
4. [ ] Docker Compose setup deployen
5. [ ] MVP bouwen (6 weken)
6. [ ] Beta lanceren met 10 test klanten
7. [ ] Feedback verwerken
8. [ ] Officiële launch

---

*Created: December 2024*
*Version: 1.0*
