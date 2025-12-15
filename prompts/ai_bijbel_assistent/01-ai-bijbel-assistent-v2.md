# 🤖 AI Bijbel Assistent (Nederlands) - V2

## Projectnaam: **BijbelWijs** of **SchriftHulp**

---

## 📋 Executive Summary

Een Nederlandse AI-gestuurde Bijbelstudie assistent die gebruikers helpt bij het begrijpen van Bijbelteksten, theologische vragen beantwoordt, en verbanden legt tussen Schriftgedeelten. Specifiek ontwikkeld voor de Nederlandse markt met ondersteuning voor meerdere vertalingen en theologische tradities.

---

## 🌐 Domeinnaam Suggesties

### Beschikbaar te checken (.nl):
| Domein | Opmerking |
|--------|-----------|
| **bijbelwijs.nl** | Primaire keuze, duidelijk en professioneel |
| **schrifthulp.nl** | Alternatief, nadruk op hulp |
| **bijbelvraag.nl** | Actiegericht, laagdrempelig |
| **bijbelassistent.nl** | Beschrijvend |
| **vraagdebijbel.nl** | Conversationeel |
| **bijbelstudie.ai** | Modern, tech-forward |
| **schriftwijzer.nl** | Traditioneler |
| **bijbelgids.nl** | Eenvoudig |
| **tekstuitleg.nl** | Functioneel |
| **openjedebijbel.nl** | Uitnodigend |

### Aanbeveling:
1. **bijbelwijs.nl** - Kort, memorabel, past bij "PreekWijs" branding
2. **bijbelvraag.nl** - Laagdrempelig, beschrijft de actie

---

## 🎯 Probleemstelling

### Huidige situatie:
- NBG heeft een experimentele chatbot, maar beperkt tot eigen content
- Internationale AI tools (ChatGPT, Claude) hebben geen specifieke Nederlandse theologische kennis
- Geen tool die HSV, NBV21, SV, BGT tegelijk kan doorzoeken en vergelijken
- Predikanten en gemeenteleden moeten zelf door veel bronnen zoeken

### Pijnpunten gebruikers:
1. "Wat betekent deze tekst eigenlijk?"
2. "Welke andere teksten gaan hierover?"
3. "Hoe legde Calvijn/Matthew Henry dit uit?"
4. "Wat is het Hebreeuwse/Griekse grondwoord?"
5. "Hoe past dit in de context van het hele boek?"

---

## 👥 Doelgroepen

### Primair:
| Doelgroep | Grootte (NL) | Betalingsbereidheid |
|-----------|--------------|---------------------|
| Predikanten/voorgangers | ~15.000 | Hoog (€10-30/maand) |
| Catecheten | ~20.000 | Medium (€5-15/maand) |
| Bijbelstudiegroep leiders | ~50.000 | Medium |

### Secundair:
| Doelgroep | Grootte (NL) | Betalingsbereidheid |
|-----------|--------------|---------------------|
| Theologiestudenten | ~3.000 | Laag (studentenkorting) |
| Actieve gemeenteleden | ~500.000 | Laag (€3-5/maand) |
| Geïnteresseerde zoekers | onbekend | Freemium |

---

## ✨ Features

### MVP (Fase 1 - 3 maanden)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Tekst uitleg** | Vraag stellen over specifieke Bijbeltekst | Must |
| **Multi-vertaling** | SV, HSV, NBV21, BGT naast elkaar | Must |
| **Context weergave** | Omliggende verzen tonen | Must |
| **Parallelle teksten** | Gerelateerde Schriftplaatsen | Must |
| **Grondwoord lookup** | Hebreeuws/Grieks met Strong's | Should |
| **Chat historie** | Gesprekken bewaren | Should |
| **Basis account** | Login, voorkeuren opslaan | Should |

### Fase 2 (3-6 maanden)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Commentaren** | Matthew Henry, Calvijn, Korte Verklaring | Must |
| **Theologische traditie** | Filter op gereformeerd/evangelisch/etc | Should |
| **Woordstudie** | Diepgaande analyse van begrippen | Should |
| **Bookmarks** | Favoriete teksten/antwoorden opslaan | Should |
| **Delen** | Antwoorden delen via link/WhatsApp | Could |
| **Audio** | Antwoorden voorlezen | Could |

### Fase 3 (6-12 maanden)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Preek modus** | Uitgebreide exegese voor predikanten | Must |
| **Groepsstudie** | Gedeelde ruimte voor Bijbelkring | Should |
| **API** | Voor integratie in kerk-apps | Should |
| **Heidelbergse Catechismus** | HC vragen koppelen aan teksten | Should |
| **Offline mode** | PWA met lokale cache | Could |
| **Spraak input** | Vragen stellen via voice | Could |

---

## 🏗️ Technische Architectuur

### High-Level Overview (Hetzner + Plesk + Docker)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                 Hetzner Dedicated Server                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Plesk Panel                             │  │
│  │  • SSL/TLS (Let's Encrypt)                                │  │
│  │  • Domain: bijbelwijs.nl                                   │  │
│  │  • Reverse Proxy → Docker containers                      │  │
│  │  • Port 80/443 → localhost:8080 (frontend)                │  │
│  │  • /api/* → localhost:8001 (backend)                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Docker Compose Stack                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │  Frontend   │  │   Backend   │  │ PostgreSQL  │        │  │
│  │  │  (Next.js)  │  │  (Node.js)  │  │   + pgvector│        │  │
│  │  │  Port 8080  │  │  Port 8001  │  │  Port 5432  │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐                         │  │
│  │  │    Redis    │  │   Backup    │                         │  │
│  │  │  Port 6379  │  │   Service   │                         │  │
│  │  └─────────────┘  └─────────────┘                         │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Claude API  │  │  SendGrid   │  │   Mollie    │              │
│  │ (Anthropic) │  │   (Email)   │  │  (Payments) │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Component | Technologie | Reden |
|-----------|-------------|-------|
| **Frontend** | Next.js 14 (React) | SSR, SEO, snelle ontwikkeling |
| **Frontend Mobile** | PWA (Progressive Web App) | Geen app store nodig |
| **API** | Node.js + Fastify | Snel, TypeScript support |
| **Database** | PostgreSQL 15 + pgvector | Betrouwbaar, vector search ingebouwd |
| **Vector Search** | pgvector extension | Geen externe service nodig |
| **AI** | Claude 3.5 Sonnet | Beste Nederlands, veilig |
| **Cache** | Redis 7 | Sessies, rate limiting |
| **Auth** | Auth.js (NextAuth) | Gratis, flexibel |
| **Email** | SendGrid | Bestaande setup |
| **Payments** | Mollie | Nederlands, iDEAL |
| **Hosting** | Hetzner Dedicated + Plesk | Bestaande infrastructuur |
| **SSL** | Let's Encrypt via Plesk | Gratis, automatisch |
| **CI/CD** | GitHub Actions | Automatische deployment |

---

## 🐳 Docker Compose Setup

### docker-compose.yml

```yaml
version: '3.8'

services:
  # Frontend - Next.js
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-https://bijbelwijs.nl/api}
    container_name: bijbelwijs_frontend
    restart: unless-stopped
    ports:
      - "8080:3000"
    environment:
      NODE_ENV: production
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-https://bijbelwijs.nl/api}
    depends_on:
      - backend
    networks:
      - bijbelwijs_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Backend - Node.js/Fastify
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: bijbelwijs_backend
    restart: unless-stopped
    ports:
      - "8001:5000"
    environment:
      NODE_ENV: production
      PORT: 5000
      DATABASE_URL: postgresql://${POSTGRES_USER:-bijbelwijs}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-bijbelwijs}
      REDIS_URL: redis://redis:6379
      
      # Auth
      JWT_SECRET: ${JWT_SECRET}
      JWT_REFRESH_SECRET: ${JWT_REFRESH_SECRET}
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
      
      # External APIs
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      
      # Email (SendGrid)
      SENDGRID_API_KEY: ${SENDGRID_API_KEY}
      SENDGRID_FROM_EMAIL: ${SENDGRID_FROM_EMAIL:-noreply@bijbelwijs.nl}
      
      # Payments (Mollie)
      MOLLIE_API_KEY: ${MOLLIE_API_KEY}
      MOLLIE_WEBHOOK_URL: ${MOLLIE_WEBHOOK_URL:-https://bijbelwijs.nl/api/webhooks/mollie}
      
      # App config
      FRONTEND_URL: ${FRONTEND_URL:-https://bijbelwijs.nl}
      CORS_ORIGINS: ${CORS_ORIGINS:-https://bijbelwijs.nl}
    volumes:
      - uploads:/app/uploads
      - logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - bijbelwijs_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    command: >
      sh -c "
        npm run db:migrate &&
        npm run start:prod
      "

  # PostgreSQL with pgvector
  postgres:
    image: pgvector/pgvector:pg15
    container_name: bijbelwijs_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-bijbelwijs}
      POSTGRES_USER: ${POSTGRES_USER:-bijbelwijs}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - bijbelwijs_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-bijbelwijs}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: bijbelwijs_redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - bijbelwijs_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backup service
  backup:
    image: postgres:15-alpine
    container_name: bijbelwijs_backup
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-bijbelwijs}
      POSTGRES_USER: ${POSTGRES_USER:-bijbelwijs}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGHOST: postgres
    volumes:
      - ./backups:/backups
      - ./scripts/backup.sh:/backup.sh:ro
    entrypoint: ["/bin/sh", "-c"]
    command: ["chmod +x /backup.sh && while true; do /backup.sh; sleep 86400; done"]
    depends_on:
      - postgres
    networks:
      - bijbelwijs_network

networks:
  bijbelwijs_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  uploads:
  logs:
```

### .env.example

```bash
# Database
POSTGRES_DB=bijbelwijs
POSTGRES_USER=bijbelwijs
POSTGRES_PASSWORD=your-secure-password-here

# Auth
JWT_SECRET=your-jwt-secret-min-32-chars
JWT_REFRESH_SECRET=your-refresh-secret-min-32-chars
NEXTAUTH_SECRET=your-nextauth-secret

# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# SendGrid (Email)
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@bijbelwijs.nl

# Mollie (Payments)
MOLLIE_API_KEY=live_xxxxx
MOLLIE_WEBHOOK_URL=https://bijbelwijs.nl/api/webhooks/mollie

# URLs
FRONTEND_URL=https://bijbelwijs.nl
NEXT_PUBLIC_API_URL=https://bijbelwijs.nl/api
CORS_ORIGINS=https://bijbelwijs.nl
```

---

## 🔧 Plesk Configuration

### Nginx Proxy Rules

In Plesk Panel → Domain → Apache & nginx Settings → Additional nginx directives:

```nginx
# Frontend proxy (main site)
location / {
    proxy_pass http://localhost:8080;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # WebSocket support (for real-time features)
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Timeouts
    proxy_connect_timeout 60;
    proxy_send_timeout 60;
    proxy_read_timeout 60;
    
    # Buffering
    proxy_buffering off;
}

# Backend API proxy
location /api/ {
    proxy_pass http://localhost:8001/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # Longer timeout for AI requests
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
    
    # Allow larger request bodies
    client_max_body_size 10M;
}

# Health check endpoint
location /health {
    proxy_pass http://localhost:8001/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
}
```

### SSL Setup (Plesk)

1. Go to: Domains → bijbelwijs.nl → SSL/TLS Certificates
2. Click "Install" next to Let's Encrypt
3. Enable:
   - ☑ Include www subdomain
   - ☑ Secure the website
4. Click "Install"

---

## 🚀 GitHub Actions Deployment

### .github/workflows/deploy.yml

```yaml
name: Deploy to Plesk Server

on:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup SSH
        run: |
          mkdir -p ~/.ssh
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/id_rsa
          chmod 600 ~/.ssh/id_rsa
          ssh-keyscan -H ${{ secrets.PLESK_HOST }} >> ~/.ssh/known_hosts

      - name: Create .env file
        run: |
          cat > .env << EOF
          POSTGRES_DB=${{ secrets.POSTGRES_DB }}
          POSTGRES_USER=${{ secrets.POSTGRES_USER }}
          POSTGRES_PASSWORD=${{ secrets.POSTGRES_PASSWORD }}
          JWT_SECRET=${{ secrets.JWT_SECRET }}
          JWT_REFRESH_SECRET=${{ secrets.JWT_REFRESH_SECRET }}
          NEXTAUTH_SECRET=${{ secrets.NEXTAUTH_SECRET }}
          ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}
          SENDGRID_API_KEY=${{ secrets.SENDGRID_API_KEY }}
          SENDGRID_FROM_EMAIL=${{ secrets.SENDGRID_FROM_EMAIL }}
          MOLLIE_API_KEY=${{ secrets.MOLLIE_API_KEY }}
          FRONTEND_URL=${{ secrets.FRONTEND_URL }}
          NEXT_PUBLIC_API_URL=${{ secrets.NEXT_PUBLIC_API_URL }}
          EOF

      - name: Create deployment package
        run: |
          tar -czf deploy.tar.gz \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='.next' \
            --exclude='backups/*.sql' \
            .

      - name: Upload to server
        run: |
          scp deploy.tar.gz ${{ secrets.PLESK_USER }}@${{ secrets.PLESK_HOST }}:${{ secrets.DEPLOY_PATH }}/
          scp .env ${{ secrets.PLESK_USER }}@${{ secrets.PLESK_HOST }}:${{ secrets.DEPLOY_PATH }}/

      - name: Deploy on server
        run: |
          ssh ${{ secrets.PLESK_USER }}@${{ secrets.PLESK_HOST }} << 'ENDSSH'
            cd ${{ secrets.DEPLOY_PATH }}
            
            # Extract deployment package
            tar -xzf deploy.tar.gz
            rm deploy.tar.gz
            
            # Build and restart containers
            docker compose down
            docker compose build --no-cache
            docker compose up -d
            
            # Wait for services
            echo "Waiting for services to start..."
            sleep 30
            
            # Run migrations
            docker compose exec -T backend npm run db:migrate
            
            # Health check
            curl -f http://localhost:8001/health || echo "Health check failed"
            
            # Show status
            docker compose ps
            
            echo "Deployment completed!"
          ENDSSH

      - name: Cleanup
        if: always()
        run: rm -f .env deploy.tar.gz
```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `SSH_PRIVATE_KEY` | SSH key for server access |
| `PLESK_HOST` | Server IP/hostname |
| `PLESK_USER` | SSH user (usually root) |
| `DEPLOY_PATH` | e.g., `/var/www/vhosts/bijbelwijs.nl` |
| `POSTGRES_DB` | Database name |
| `POSTGRES_USER` | Database user |
| `POSTGRES_PASSWORD` | Database password |
| `JWT_SECRET` | JWT signing secret |
| `JWT_REFRESH_SECRET` | JWT refresh token secret |
| `NEXTAUTH_SECRET` | NextAuth secret |
| `ANTHROPIC_API_KEY` | Claude API key |
| `SENDGRID_API_KEY` | SendGrid API key |
| `SENDGRID_FROM_EMAIL` | Sender email address |
| `MOLLIE_API_KEY` | Mollie payment API key |
| `FRONTEND_URL` | e.g., `https://bijbelwijs.nl` |
| `NEXT_PUBLIC_API_URL` | e.g., `https://bijbelwijs.nl/api` |

---

## 💾 Database Schema

### PostgreSQL with pgvector

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Gebruikers
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    preferred_translation VARCHAR(10) DEFAULT 'HSV',
    theological_tradition VARCHAR(50),
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    stripe_customer_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat sessies
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Chat berichten
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    bible_references JSONB,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Bijbel teksten
CREATE TABLE bible_verses (
    id SERIAL PRIMARY KEY,
    translation VARCHAR(10) NOT NULL,
    book VARCHAR(50) NOT NULL,
    book_number INTEGER NOT NULL,
    chapter INTEGER NOT NULL,
    verse INTEGER NOT NULL,
    text TEXT NOT NULL,
    embedding vector(1536), -- OpenAI embedding dimensie
    UNIQUE(translation, book, chapter, verse)
);

-- Strong's nummers
CREATE TABLE strongs (
    id SERIAL PRIMARY KEY,
    strongs_number VARCHAR(10) UNIQUE NOT NULL,
    original_word VARCHAR(100),
    transliteration VARCHAR(100),
    definition TEXT,
    usage_notes TEXT
);

-- Bookmarks
CREATE TABLE bookmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message_id UUID REFERENCES chat_messages(id),
    bible_reference VARCHAR(100),
    note TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Usage tracking (voor rate limiting)
CREATE TABLE usage_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    month VARCHAR(7) NOT NULL, -- '2024-01'
    questions_count INTEGER DEFAULT 0,
    tokens_used INTEGER DEFAULT 0,
    UNIQUE(user_id, month)
);

-- Indexes
CREATE INDEX idx_bible_verses_lookup ON bible_verses(translation, book, chapter);
CREATE INDEX idx_bible_verses_embedding ON bible_verses USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_usage_tracking_user_month ON usage_tracking(user_id, month);
```

---

## 📧 SendGrid Email Templates

### Configuratie

```typescript
// backend/src/services/email.service.ts
import sgMail from '@sendgrid/mail';

sgMail.setApiKey(process.env.SENDGRID_API_KEY!);

export async function sendWelcomeEmail(user: { email: string; name: string }) {
  await sgMail.send({
    to: user.email,
    from: {
      email: process.env.SENDGRID_FROM_EMAIL!,
      name: 'BijbelWijs'
    },
    subject: 'Welkom bij BijbelWijs! 📖',
    templateId: 'd-xxxxx', // SendGrid dynamic template
    dynamicTemplateData: {
      name: user.name,
      loginUrl: `${process.env.FRONTEND_URL}/login`
    }
  });
}

export async function sendPasswordReset(email: string, resetToken: string) {
  await sgMail.send({
    to: email,
    from: {
      email: process.env.SENDGRID_FROM_EMAIL!,
      name: 'BijbelWijs'
    },
    subject: 'Wachtwoord resetten - BijbelWijs',
    templateId: 'd-xxxxx',
    dynamicTemplateData: {
      resetUrl: `${process.env.FRONTEND_URL}/reset-password?token=${resetToken}`
    }
  });
}

export async function sendSubscriptionConfirmation(user: { email: string; name: string }, tier: string) {
  await sgMail.send({
    to: user.email,
    from: {
      email: process.env.SENDGRID_FROM_EMAIL!,
      name: 'BijbelWijs'
    },
    subject: 'Je abonnement is geactiveerd! 🎉',
    templateId: 'd-xxxxx',
    dynamicTemplateData: {
      name: user.name,
      tier: tier,
      dashboardUrl: `${process.env.FRONTEND_URL}/dashboard`
    }
  });
}
```

---

## 💰 Kostenraming (Aangepast)

### Ontwikkelkosten (MVP)

| Item | Uren | Uurtarief | Totaal |
|------|------|-----------|--------|
| Backend development | 120 | €75 | €9.000 |
| Frontend development | 80 | €75 | €6.000 |
| AI/RAG implementatie | 40 | €100 | €4.000 |
| Design/UX | 30 | €60 | €1.800 |
| Testing | 20 | €60 | €1.200 |
| **Totaal** | **290** | | **€22.000** |

*Of zelf bouwen: ~3 maanden fulltime*

### Maandelijkse operationele kosten

| Item | Kosten/maand | Notities |
|------|--------------|----------|
| Hetzner Dedicated (bestaand) | €0* | Deel van bestaande server |
| Docker resources | €0* | Op bestaande server |
| PostgreSQL + pgvector | €0* | Self-hosted in Docker |
| Redis | €0* | Self-hosted in Docker |
| Claude API | €100-500 | Afhankelijk van gebruik |
| SendGrid | €0-20* | Bestaand account / free tier tot 100/dag |
| Cloudflare | €0 | Free tier |
| Domein (.nl) | €1 | Per maand |
| **Totaal** | **€100-520** | |

*Kosten gedeeld met andere projecten op dezelfde server

### Claude API kosten detail

| Tier | Tokens/maand | Kosten | Vragen/maand* |
|------|--------------|--------|---------------|
| 100 gebruikers | 5M tokens | ~€50 | ~2.500 |
| 1.000 gebruikers | 50M tokens | ~€500 | ~25.000 |
| 10.000 gebruikers | 500M tokens | ~€5.000 | ~250.000 |

*Gemiddeld 2.000 tokens per vraag/antwoord

---

## 💵 Prijsmodel

### Freemium Model

| Tier | Prijs | Features |
|------|-------|----------|
| **Gratis** | €0 | 20 vragen/maand, 1 vertaling, geen historie |
| **Basis** | €4,99/maand | 200 vragen/maand, alle vertalingen, historie |
| **Standaard** | €9,99/maand | Onbeperkt, commentaren, Strong's |
| **Pro** | €19,99/maand | + API toegang, groepsstudie, prioriteit |
| **Kerk** | €49,99/maand | 10 gebruikers, branding, support |

### Mollie Integratie

```typescript
// backend/src/services/payment.service.ts
import { createMollieClient } from '@mollie/api-client';

const mollieClient = createMollieClient({ 
  apiKey: process.env.MOLLIE_API_KEY! 
});

export async function createSubscription(userId: string, tier: string) {
  const prices: Record<string, string> = {
    basis: '4.99',
    standaard: '9.99',
    pro: '19.99',
    kerk: '49.99'
  };

  const payment = await mollieClient.payments.create({
    amount: {
      currency: 'EUR',
      value: prices[tier]
    },
    description: `BijbelWijs ${tier} abonnement`,
    redirectUrl: `${process.env.FRONTEND_URL}/subscription/success`,
    webhookUrl: `${process.env.MOLLIE_WEBHOOK_URL}`,
    metadata: {
      userId,
      tier
    }
  });

  return payment;
}
```

---

## 📅 Roadmap

### Fase 1: MVP (Maand 1-3)

```
Week 1-2:   Project setup, Docker config, database schema
Week 3-4:   Bijbel data import, basis API
Week 5-6:   RAG systeem met pgvector, prompt engineering
Week 7-8:   Frontend chat interface
Week 9-10:  Auth, SendGrid integratie
Week 11-12: Plesk deployment, testing, soft launch
```

### Fase 2: Groei (Maand 4-6)

```
- Commentaren toevoegen (Matthew Henry, etc.)
- PWA optimalisatie
- Mollie subscription systeem
- Marketing: christelijke media, kerken
```

### Fase 3: Uitbreiding (Maand 7-12)

```
- Preek modus voor predikanten
- Groepsstudie feature
- API voor derden
- Heidelbergse Catechismus integratie
```

---

## 🔧 Backup Script

### scripts/backup.sh

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/bijbelwijs_$DATE.sql.gz"

# Backup database
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h $PGHOST -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_FILE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "bijbelwijs_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

---

## ⚠️ Risico's & Mitigatie

| Risico | Impact | Kans | Mitigatie |
|--------|--------|------|-----------|
| **Bijbel licenties** | Hoog | Medium | Start met SV (rechtenvrij), onderhandel met NBG |
| **AI hallucinaties** | Hoog | Medium | Strenge prompts, fact-checking, disclaimers |
| **Theologische controverse** | Medium | Hoog | Neutraal blijven, meerdere perspectieven tonen |
| **Hoge API kosten** | Medium | Medium | Caching, rate limiting, efficient prompts |
| **Server downtime** | Medium | Laag | Docker health checks, automated restarts |
| **Lage adoptie** | Hoog | Medium | Freemium, marketing via kerken |

---

## ✅ Volgende Stappen

1. [ ] Domein registreren (bijbelwijs.nl)
2. [ ] Project repository aanmaken
3. [ ] Docker Compose setup opzetten
4. [ ] Plesk domain configureren met proxy rules
5. [ ] Database schema implementeren
6. [ ] Proof of concept bouwen met SV
7. [ ] SendGrid templates maken
8. [ ] GitHub Actions workflow testen
9. [ ] Landing page met waitlist
10. [ ] NBG contacteren over licenties

---

## 📁 Project Structuur

```
bijbelwijs/
├── .github/
│   └── workflows/
│       └── deploy.yml
├── backend/
│   ├── src/
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── utils/
│   ├── Dockerfile
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── lib/
│   ├── Dockerfile
│   └── package.json
├── database/
│   └── init.sql
├── scripts/
│   └── backup.sh
├── backups/
├── docker-compose.yml
├── .env.example
└── README.md
```
