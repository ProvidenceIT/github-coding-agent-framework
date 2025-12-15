# 📖 Bijbel Leesplan Generator met AI - V2

## Projectnaam: **LeesWijs** of **BijbelPad**

---

## 📋 Executive Summary

Een AI-gestuurde tool die gepersonaliseerde Bijbelleesplannen genereert op basis van persoonlijke situatie, interesses en beschikbare tijd. Inclusief dagelijkse reflectievragen en voortgangsregistratie.

---

## 🌐 Domeinnaam Suggesties

### Beschikbaar te checken (.nl):

| Domein | Opmerking |
|--------|-----------|
| **leeswijs.nl** | Primaire keuze, kort en krachtig |
| **bijbelpad.nl** | Alternatief, "pad" suggereert reis |
| **dagelijkswoord.nl** | Beschrijvend, traditioneel |
| **bijbelroute.nl** | Reis-metafoor |
| **leesplan.nl** | Direct beschrijvend |
| **bijbelreis.nl** | Avontuurlijk |
| **schriftpad.nl** | Traditioneler |
| **dagelijkslezen.nl** | Actiegericht |
| **mijnbijbelplan.nl** | Persoonlijk |
| **bijbelstart.nl** | Voor beginners |

### Aanbeveling:
1. **leeswijs.nl** - Kort, memorabel, past bij branding (BijbelWijs, PreekWijs)
2. **bijbelpad.nl** - Suggereert een persoonlijke reis door de Bijbel

---

## 🎯 Probleemstelling

### Huidige situatie:
- Bestaande leesplannen zijn one-size-fits-all
- YouVersion heeft veel plannen maar geen personalisatie
- NBG Bijbel in een jaar is te intensief voor velen
- Mensen beginnen enthousiast maar haken af
- Geen koppeling tussen levenssituatie en Bijbelgedeelte

### Pijnpunten:
1. "Waar moet ik beginnen met Bijbellezen?"
2. "Dit leesplan past niet bij mijn leven nu"
3. "Ik heb maar 10 minuten per dag"
4. "Ik worstel met X, wat zegt de Bijbel daarover?"
5. "Ik haak altijd af bij Leviticus"

---

## 👥 Doelgroepen

### Primair:

| Doelgroep | Behoefte |
|-----------|----------|
| Nieuwe gelovigen | Waar te beginnen |
| Herintreders | Weer op gang komen |
| Drukke professionals | Korte, relevante plannen |
| Jongvolwassenen | Toegankelijke start |

### Secundair:

| Doelgroep | Behoefte |
|-----------|----------|
| Bijbelstudiegroepen | Gezamenlijk plan |
| Catechisanten | Plan bij catechese |
| Mensen in crisis | Troost-gerichte plannen |

---

## ✨ Features

### MVP (Fase 1 - 6 weken)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Intake wizard** | Vragen over situatie, tijd, interesse | Must |
| **Plan generator** | AI genereert gepersonaliseerd plan | Must |
| **Dagelijkse lezing** | Tekst + korte reflectie | Must |
| **Voortgang tracking** | Check-off, streak | Must |
| **Plan aanpassen** | Tempo/focus wijzigen | Should |

### Fase 2 (6-12 weken)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Multi-vertaling** | Kies je vertaling | Must |
| **Audio optie** | Luister naar dagelijkse lezing | Should |
| **Reflectievragen** | AI-gegenereerde vragen | Should |
| **Journal** | Notities bij lezingen | Should |
| **Herinneringen** | Push/email op vaste tijd | Should |

### Fase 3 (3-6 maanden)

| Feature | Beschrijving | Prioriteit |
|---------|--------------|------------|
| **Groepsplannen** | Samen lezen | Should |
| **Predikant modus** | Plan voor gemeente maken | Should |
| **Thematische plannen** | Kant-en-klare thema's | Should |
| **Integratie apps** | Export naar YouVersion/etc | Could |

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
│  │  • Domain: leeswijs.nl                                     │  │
│  │  • Reverse Proxy → Docker containers                      │  │
│  │  • Port 80/443 → localhost:8082 (frontend)                │  │
│  │  • /api/* → localhost:8003 (backend)                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              Docker Compose Stack                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │  │
│  │  │  Frontend   │  │   Backend   │  │ PostgreSQL  │        │  │
│  │  │  (Next.js)  │  │  (Node.js)  │  │             │        │  │
│  │  │  Port 8082  │  │  Port 8003  │  │  Port 5434  │        │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘        │  │
│  │                                                            │  │
│  │  ┌─────────────┐  ┌─────────────┐                         │  │
│  │  │    Redis    │  │   Backup    │                         │  │
│  │  │  Port 6381  │  │   Service   │                         │  │
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
| **Frontend** | Next.js 14 + PWA | SSR, SEO, offline capable |
| **Backend** | Node.js + tRPC | Type-safe, snel |
| **Database** | PostgreSQL 15 | Betrouwbaar, JSONB support |
| **AI** | Claude 3.5 Sonnet | Beste Nederlands, veilig |
| **Cache** | Redis 7 | Sessies, streak caching |
| **Auth** | Auth.js (NextAuth) | Gratis, magic links |
| **Email** | SendGrid | Bestaande setup, herinneringen |
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
  # Frontend - Next.js PWA
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
      args:
        - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-https://leeswijs.nl/api}
    container_name: leeswijs_frontend
    restart: unless-stopped
    ports:
      - "8082:3000"
    environment:
      NODE_ENV: production
      NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-https://leeswijs.nl/api}
    depends_on:
      - backend
    networks:
      - leeswijs_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Backend - Node.js/tRPC
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: leeswijs_backend
    restart: unless-stopped
    ports:
      - "8003:5000"
    environment:
      NODE_ENV: production
      PORT: 5000
      DATABASE_URL: postgresql://${POSTGRES_USER:-leeswijs}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB:-leeswijs}
      REDIS_URL: redis://redis:6379
      
      # Auth
      JWT_SECRET: ${JWT_SECRET}
      JWT_REFRESH_SECRET: ${JWT_REFRESH_SECRET}
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET}
      
      # External APIs
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      
      # Email (SendGrid)
      SENDGRID_API_KEY: ${SENDGRID_API_KEY}
      SENDGRID_FROM_EMAIL: ${SENDGRID_FROM_EMAIL:-noreply@leeswijs.nl}
      
      # Payments (Mollie)
      MOLLIE_API_KEY: ${MOLLIE_API_KEY}
      MOLLIE_WEBHOOK_URL: ${MOLLIE_WEBHOOK_URL:-https://leeswijs.nl/api/webhooks/mollie}
      
      # App config
      FRONTEND_URL: ${FRONTEND_URL:-https://leeswijs.nl}
      CORS_ORIGINS: ${CORS_ORIGINS:-https://leeswijs.nl}
    volumes:
      - logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - leeswijs_network
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

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    container_name: leeswijs_postgres
    restart: unless-stopped
    ports:
      - "5434:5432"
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-leeswijs}
      POSTGRES_USER: ${POSTGRES_USER:-leeswijs}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - leeswijs_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-leeswijs}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis
  redis:
    image: redis:7-alpine
    container_name: leeswijs_redis
    restart: unless-stopped
    ports:
      - "6381:6379"
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    networks:
      - leeswijs_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Backup service
  backup:
    image: postgres:15-alpine
    container_name: leeswijs_backup
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-leeswijs}
      POSTGRES_USER: ${POSTGRES_USER:-leeswijs}
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
      - leeswijs_network

networks:
  leeswijs_network:
    driver: bridge

volumes:
  postgres_data:
  redis_data:
  logs:
```

### .env.example

```bash
# Database
POSTGRES_DB=leeswijs
POSTGRES_USER=leeswijs
POSTGRES_PASSWORD=your-secure-password-here

# Auth
JWT_SECRET=your-jwt-secret-min-32-chars
JWT_REFRESH_SECRET=your-refresh-secret-min-32-chars
NEXTAUTH_SECRET=your-nextauth-secret

# Claude API
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx

# SendGrid (Email)
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@leeswijs.nl

# Mollie (Payments) - Optional for MVP
MOLLIE_API_KEY=live_xxxxx
MOLLIE_WEBHOOK_URL=https://leeswijs.nl/api/webhooks/mollie

# URLs
FRONTEND_URL=https://leeswijs.nl
NEXT_PUBLIC_API_URL=https://leeswijs.nl/api
CORS_ORIGINS=https://leeswijs.nl

# App Settings
DEFAULT_REMINDER_TIME=08:00
```

---

## 🔧 Plesk Configuration

### Nginx Proxy Rules

In Plesk Panel → Domain → Apache & nginx Settings → Additional nginx directives:

```nginx
# Frontend proxy (main site)
location / {
    proxy_pass http://localhost:8082;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    
    # PWA Service Worker support
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # Timeouts
    proxy_connect_timeout 60;
    proxy_send_timeout 60;
    proxy_read_timeout 60;
}

# Backend API proxy
location /api/ {
    proxy_pass http://localhost:8003/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Longer timeout for AI plan generation
    proxy_connect_timeout 120;
    proxy_send_timeout 120;
    proxy_read_timeout 120;
}

# Health check endpoint
location /health {
    proxy_pass http://localhost:8003/health;
}
```

---

## 🚀 GitHub Actions Deployment

### .github/workflows/deploy.yml

```yaml
name: Deploy LeesWijs to Plesk

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
          FRONTEND_URL=${{ secrets.FRONTEND_URL }}
          NEXT_PUBLIC_API_URL=${{ secrets.NEXT_PUBLIC_API_URL }}
          EOF

      - name: Deploy to server
        run: |
          rsync -avz --delete \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='.next' \
            --exclude='backups/*.sql' \
            ./ ${{ secrets.PLESK_USER }}@${{ secrets.PLESK_HOST }}:${{ secrets.DEPLOY_PATH }}/
          
          scp .env ${{ secrets.PLESK_USER }}@${{ secrets.PLESK_HOST }}:${{ secrets.DEPLOY_PATH }}/

      - name: Build and restart containers
        run: |
          ssh ${{ secrets.PLESK_USER }}@${{ secrets.PLESK_HOST }} << 'ENDSSH'
            cd ${{ secrets.DEPLOY_PATH }}
            docker compose down
            docker compose build --no-cache
            docker compose up -d
            sleep 30
            docker compose exec -T backend npm run db:migrate
            docker compose ps
            echo "Deployment completed!"
          ENDSSH

      - name: Cleanup
        if: always()
        run: rm -f .env
```

---

## 🤖 AI Plan Generator

### Intake Vragen

```typescript
interface IntakeQuestions {
  // Basis
  name: string;
  email: string;
  
  // Ervaring
  bibleExperience: 'beginner' | 'some' | 'regular' | 'advanced';
  favoriteBooks: string[]; // Optioneel
  
  // Situatie
  currentLifeSituation: string[]; // Multi-select:
  // ['nieuw_geloof', 'groei', 'crisis', 'rouw', 'stress', 
  //  'relatie', 'opvoeding', 'werk', 'ziekte', 'anders']
  situationDetails?: string; // Optioneel vrij veld
  
  // Interesses
  interests: string[]; // Multi-select:
  // ['jezus_leven', 'psalmen', 'wijsheid', 'profeten', 
  //  'brieven', 'geschiedenis', 'eindtijd', 'schepping']
  
  // Tijd
  dailyMinutes: 5 | 10 | 15 | 20 | 30;
  preferredTime: 'morning' | 'evening' | 'flexible';
  
  // Plan lengte
  duration: '1week' | '2weeks' | '1month' | '3months' | '6months' | '1year';
  
  // Voorkeur
  translation: 'HSV' | 'NBV21' | 'BGT' | 'SV';
  includeOT: boolean;
  includeNT: boolean;
  
  // Denominatie (optioneel, voor context)
  denomination?: string;
}
```

### AI Prompt voor Plan Generatie

```markdown
Genereer een gepersonaliseerd Bijbelleesplan.

## Gebruiker profiel:
- Ervaring: {{bibleExperience}}
- Situatie: {{currentLifeSituation}}
- Details: {{situationDetails}}
- Interesses: {{interests}}
- Tijd per dag: {{dailyMinutes}} minuten
- Duur plan: {{duration}}
- Vertaling: {{translation}}

## Richtlijnen:
1. Start met toegankelijke gedeelten voor beginners
2. Wissel af tussen OT en NT (indien beide gewenst)
3. Koppel aan levenssituatie waar mogelijk
4. Houd rekening met leestijd (gemiddeld 200 woorden/minuut)
5. Bouw op van eenvoudig naar complexer
6. Vermijd lange genealogieën/wetten voor beginners
7. Voeg voor elke dag een korte reflectievraag toe

## Output format (JSON):
{
  "title": "Persoonlijk plan voor [naam]",
  "description": "Korte beschrijving van het plan",
  "total_days": number,
  "days": [
    {
      "day": 1,
      "title": "Dag titel",
      "passage": "Johannes 1:1-18",
      "estimated_minutes": 8,
      "theme": "Gods Woord wordt mens",
      "reflection_question": "Wat betekent het voor jou dat God naar de aarde kwam?",
      "connection_to_situation": "In moeilijke tijden..."
    }
  ]
}
```

---

## 💾 Database Schema

```sql
-- Gebruikers
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    preferred_translation VARCHAR(10) DEFAULT 'HSV',
    reminder_time TIME DEFAULT '08:00',
    reminder_enabled BOOLEAN DEFAULT true,
    timezone VARCHAR(50) DEFAULT 'Europe/Amsterdam',
    subscription_tier VARCHAR(20) DEFAULT 'free',
    subscription_expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Intake antwoorden
CREATE TABLE intake_responses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    bible_experience VARCHAR(50),
    life_situation JSONB,
    interests JSONB,
    daily_minutes INTEGER,
    duration VARCHAR(20),
    include_ot BOOLEAN DEFAULT true,
    include_nt BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Leesplannen
CREATE TABLE reading_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    total_days INTEGER NOT NULL,
    start_date DATE,
    status VARCHAR(20) DEFAULT 'active',
    current_day INTEGER DEFAULT 1,
    ai_generated BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);

-- Plan dagen
CREATE TABLE plan_days (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID REFERENCES reading_plans(id) ON DELETE CASCADE,
    day_number INTEGER NOT NULL,
    title VARCHAR(255),
    passage VARCHAR(100) NOT NULL,
    estimated_minutes INTEGER,
    theme VARCHAR(255),
    reflection_question TEXT,
    connection_to_situation TEXT,
    UNIQUE(plan_id, day_number)
);

-- Voortgang
CREATE TABLE reading_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_day_id UUID REFERENCES plan_days(id) ON DELETE CASCADE,
    completed BOOLEAN DEFAULT false,
    completed_at TIMESTAMP,
    journal_entry TEXT,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    UNIQUE(user_id, plan_day_id)
);

-- Streaks
CREATE TABLE streaks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_read_date DATE,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Email herinneringen log
CREATE TABLE reminder_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    sent_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20),
    plan_id UUID REFERENCES reading_plans(id)
);

-- Indexes
CREATE INDEX idx_reading_plans_user ON reading_plans(user_id);
CREATE INDEX idx_reading_plans_status ON reading_plans(status);
CREATE INDEX idx_reading_progress_user ON reading_progress(user_id);
CREATE INDEX idx_streaks_user ON streaks(user_id);
```

---

## 📧 SendGrid Email Templates

### Daily Reminder Email

```typescript
// backend/src/services/reminder.service.ts
import sgMail from '@sendgrid/mail';
import { CronJob } from 'cron';

sgMail.setApiKey(process.env.SENDGRID_API_KEY!);

export async function sendDailyReminder(user: {
  email: string;
  name: string;
  planTitle: string;
  todayPassage: string;
  currentStreak: number;
}) {
  await sgMail.send({
    to: user.email,
    from: {
      email: process.env.SENDGRID_FROM_EMAIL!,
      name: 'LeesWijs'
    },
    subject: `📖 Je Bijbellezing van vandaag - ${user.planTitle}`,
    templateId: 'd-reminder-template-id',
    dynamicTemplateData: {
      name: user.name,
      planTitle: user.planTitle,
      passage: user.todayPassage,
      streak: user.currentStreak,
      readUrl: `${process.env.FRONTEND_URL}/lezen`
    }
  });
}

// Cron job voor dagelijkse herinneringen
export function startReminderCron() {
  // Elke dag om 06:00 checken wie herinnering moet krijgen
  const job = new CronJob('0 6 * * *', async () => {
    const users = await getUsersWithReminders();
    
    for (const user of users) {
      const localTime = new Date().toLocaleString('nl-NL', {
        timeZone: user.timezone
      });
      
      // Check of het tijd is voor deze gebruiker
      if (isReminderTime(user.reminder_time, user.timezone)) {
        await sendDailyReminder(user);
      }
    }
  });
  
  job.start();
}
```

### Streak Milestone Email

```typescript
export async function sendStreakMilestone(user: {
  email: string;
  name: string;
  streak: number;
}) {
  const milestones = [7, 14, 30, 50, 100, 365];
  
  if (milestones.includes(user.streak)) {
    await sgMail.send({
      to: user.email,
      from: {
        email: process.env.SENDGRID_FROM_EMAIL!,
        name: 'LeesWijs'
      },
      subject: `🎉 ${user.streak} dagen streak! Geweldig gedaan!`,
      templateId: 'd-streak-milestone-template',
      dynamicTemplateData: {
        name: user.name,
        streak: user.streak,
        shareUrl: `${process.env.FRONTEND_URL}/share?streak=${user.streak}`
      }
    });
  }
}
```

---

## 📱 UI Flow

### Intake Wizard

```
Scherm 1: Welkom
┌─────────────────────────────────────────┐
│  Welkom bij LeesWijs! 📖               │
│                                         │
│  Laten we samen een Bijbelleesplan     │
│  maken dat bij jou past.               │
│                                         │
│  Dit duurt ongeveer 2 minuten.         │
│                                         │
│         [Start →]                       │
└─────────────────────────────────────────┘

Scherm 2-5: Vragen (ervaring, situatie, interesses, tijd)

Scherm 6: Genereren
┌─────────────────────────────────────────┐
│  Je plan wordt gemaakt... ⏳            │
│                                         │
│  ████████████░░░░░░░░                   │
│                                         │
│  AI analyseert je antwoorden en         │
│  stelt het perfecte plan samen.         │
└─────────────────────────────────────────┘
```

### Plan View (PWA)

```
┌─────────────────────────────────────────┐
│  Jezus ontmoeten 📖          Dag 5/28  │
│  ████████░░░░░░░░░░░░ 18%              │
│                                         │
│  🔥 5 dagen streak!                     │
│                                         │
├─────────────────────────────────────────┤
│                                         │
│  Vandaag: De eerste wonderen           │
│                                         │
│  📖 Johannes 2:1-12                    │
│  ⏱️ ~8 minuten                          │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ Op de derde dag was er een      │    │
│  │ bruiloft te Kana in Galilea...  │    │
│  │                                 │    │
│  │ [Lees verder ↓]                 │    │
│  └─────────────────────────────────┘    │
│                                         │
│  💭 Reflectievraag:                    │
│  "Jezus' eerste wonder was op een      │
│   feest. Wat zegt dit over Hem?"       │
│                                         │
│  ┌─────────────────────────────────┐    │
│  │ 📝 Mijn gedachten...            │    │
│  │                                 │    │
│  └─────────────────────────────────┘    │
│                                         │
│  [✓ Gelezen, door naar morgen]         │
│                                         │
└─────────────────────────────────────────┘
```

---

## 💰 Kostenraming (Aangepast)

### Ontwikkelkosten

| Item | Uren | Totaal |
|------|------|--------|
| Frontend (Next.js + PWA) | 60 | €4.500 |
| Backend + AI + tRPC | 50 | €5.000 |
| Database + Auth | 20 | €1.500 |
| Design | 20 | €1.200 |
| **Totaal** | **150** | **€12.200** |

### Maandelijkse kosten

| Item | Kosten | Notities |
|------|--------|----------|
| Hetzner Dedicated (bestaand) | €0* | Deel van bestaande server |
| Docker resources | €0* | Op bestaande server |
| PostgreSQL | €0* | Self-hosted in Docker |
| Redis | €0* | Self-hosted in Docker |
| Claude API | €50-150 | ~1000 plan generaties |
| SendGrid | €0-20* | Bestaand account |
| Domein (.nl) | €1 | Per maand |
| **Totaal** | **€50-170** | |

*Kosten gedeeld met andere projecten

---

## 💵 Prijsmodel

| Tier | Prijs | Features |
|------|-------|----------|
| **Gratis** | €0 | 1 plan tegelijk, basis features, email herinnering |
| **Plus** | €3,99/maand | Onbeperkt plannen, audio, journal, geen ads |
| **Familie** | €6,99/maand | 4 accounts, gezamenlijke plannen |

### Mollie Integratie

```typescript
// backend/src/services/payment.service.ts
import { createMollieClient } from '@mollie/api-client';

const mollieClient = createMollieClient({ 
  apiKey: process.env.MOLLIE_API_KEY! 
});

export async function createSubscription(userId: string, tier: 'plus' | 'familie') {
  const prices = {
    plus: '3.99',
    familie: '6.99'
  };

  const payment = await mollieClient.payments.create({
    amount: { currency: 'EUR', value: prices[tier] },
    description: `LeesWijs ${tier} abonnement`,
    redirectUrl: `${process.env.FRONTEND_URL}/subscription/success`,
    webhookUrl: `${process.env.FRONTEND_URL}/api/webhooks/mollie`,
    metadata: { userId, tier }
  });

  return payment;
}
```

---

## 📅 Roadmap

### Fase 1 (Week 1-6): MVP
```
Week 1-2:   Project setup, Docker config, database
Week 3-4:   Intake wizard, AI plan generator
Week 5:     Frontend leesinterface, voortgang
Week 6:     Email herinneringen, deployment
```

### Fase 2 (Week 7-12): Polish
```
- PWA optimalisatie (offline support)
- Audio integratie (optioneel)
- Journal functie
- Streak systeem met badges
- Mollie payments
```

### Fase 3 (Maand 4-6): Groei
```
- Groepsplannen
- Thematische templates
- Predikant modus
```

---

## 📁 Project Structuur

```
leeswijs/
├── .github/
│   └── workflows/
│       └── deploy.yml
├── backend/
│   ├── src/
│   │   ├── routers/           # tRPC routers
│   │   ├── services/
│   │   │   ├── ai.service.ts
│   │   │   ├── email.service.ts
│   │   │   ├── reminder.service.ts
│   │   │   └── payment.service.ts
│   │   ├── db/
│   │   └── utils/
│   ├── Dockerfile
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Landing
│   │   │   ├── intake/            # Wizard
│   │   │   ├── lezen/             # Reading view
│   │   │   └── dashboard/
│   │   ├── components/
│   │   └── lib/
│   ├── public/
│   │   └── manifest.json          # PWA manifest
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

---

## ✅ Volgende Stappen

1. [ ] Domein registreren (leeswijs.nl of bijbelpad.nl)
2. [ ] GitHub repository aanmaken
3. [ ] Docker Compose setup opzetten
4. [ ] Plesk domain configureren
5. [ ] Database schema implementeren
6. [ ] AI plan generator testen
7. [ ] SendGrid templates maken
8. [ ] PWA manifest configureren
9. [ ] Beta test met 20 gebruikers
10. [ ] Itereren op feedback
