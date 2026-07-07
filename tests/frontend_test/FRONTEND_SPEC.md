# Frontend Specification: Autonomous Swarm UI
### Version 1.0 — Complete Reference Blueprint
### Last Updated: 2026-07-04

---

> This document is the **single source of truth** for building the frontend of the Autonomous Multi-Agent Swarm System. Every screen, button, input field, state transition, icon, logo, error state, and edge case is defined here. Nothing should be built without first being documented in this file.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture: Frontend ↔ Backend](#2-architecture-frontend--backend)
3. [Screen Map (All Pages)](#3-screen-map-all-pages)
4. [Screen 1: Landing / Dashboard](#4-screen-1-landing--dashboard)
5. [Screen 2: Chat Interface (Main Workspace)](#5-screen-2-chat-interface-main-workspace)
6. [Screen 3: Agent Registry Panel](#6-screen-3-agent-registry-panel)
7. [Screen 4: File Manager (Inbox & Outputs)](#7-screen-4-file-manager-inbox--outputs)
8. [Screen 5: History & Past Results](#8-screen-5-history--past-results)
9. [Screen 6: Settings & Model Configuration](#9-screen-6-settings--model-configuration)
10. [Screen 7: Health Monitor / System Status](#10-screen-7-health-monitor--system-status)
11. [All Buttons, Actions & Operations](#11-all-buttons-actions--operations)
12. [All Input Types & How They Are Handled](#12-all-input-types--how-they-are-handled)
13. [Output Display Rules](#13-output-display-rules)
14. [Error States & Edge Cases](#14-error-states--edge-cases)
15. [Notification & Toast System](#15-notification--toast-system)
16. [Keyboard Shortcuts](#16-keyboard-shortcuts)
17. [Icon Inventory (SVG/Icon Library Required)](#17-icon-inventory-svgicon-library-required)
18. [Brand Logo Inventory (External Logos Required)](#18-brand-logo-inventory-external-logos-required)
19. [Design Tokens & Theme](#19-design-tokens--theme)
20. [Future Considerations (v2)](#20-future-considerations-v2)

---

## 1. Project Overview

**Product Name:** Autonomous Swarm

**What it does:** A fully local, multi-agent AI system that can scrape the web, read emails, manage calendars, process PDFs, transcribe audio, interact with GitHub, manage files, query databases, post to social media, and autonomously improve itself — all from a single chat interface.

**Core Philosophy:**
- **Everything from one text box.** The user types a natural-language command. The Orchestrator decides which agents to call, in what order, and chains their outputs together.
- **Files go in, results come out.** Users can attach/upload/drop files (PDFs, audio, images) and the system processes them automatically.
- **Full transparency.** Every agent call, every intermediate step, every error is visible in real-time as the Orchestrator thinks.

**Backend stack (already built):**
- Python (Flask/FastAPI will serve as the bridge)
- Ollama (local LLMs: `llama3.1:8b`, `qwen3.5:9b`, `qwen3-vl:4b`, `llama3.2:3b`, `gemma4:e2b-mlx`)
- 25+ agents in `/agents/`
- SQLite database at `database.db`
- Vector memory store in `/memory/`
- File sandbox at `archive/workspace/` and `archive/inbox/`

---

## 2. Architecture: Frontend ↔ Backend

```
┌──────────────────────────────────┐
│          FRONTEND (Browser)      │
│  HTML / CSS / JS                 │
│                                  │
│  ┌─────────────────────────────┐ │
│  │  Chat Interface             │ │     HTTP / WebSocket
│  │  File Upload Zone           │ │ ◄──────────────────────►
│  │  Agent Registry Panel       │ │
│  │  History Viewer             │ │
│  │  Settings Panel             │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────┐
│          BACKEND (Python)        │
│  FastAPI / Flask                 │
│                                  │
│  POST /api/chat     ← user msg   │
│  GET  /api/agents   ← registry   │
│  POST /api/upload   ← file inp   │
│  GET  /api/history  ← past runs  │
│  GET  /api/health   ← sys stat   │
│  WS   /ws/stream    ← live out   │
│                                  │
│  ┌─────────────────────────────┐ │
│  │  Orchestrator (ReAct Loop)  │ │
│  │  25+ Agents                 │ │
│  │  Ollama / Gemini LLM        │ │
│  │  SQLite + Vector Memory     │ │
│  └─────────────────────────────┘ │
└──────────────────────────────────┘
```

**Communication Protocol:**
- **REST API** for one-shot requests (send prompt, get final answer).
- **WebSocket** for streaming the ReAct loop in real-time (the user sees each step as the Orchestrator thinks: "Calling web_scraper...", "Result received...", "Calling ner_agent...", etc.).

---

## 3. Screen Map (All Pages)

| Screen | URL Route | Purpose |
|--------|-----------|---------|
| Landing / Dashboard | `/` | Overview of system health, quick stats, recent activity |
| Chat Interface | `/chat` | The main workspace — prompt input, file attach, live output |
| Agent Registry | `/agents` | Browse all 25+ agents, see their parameters, descriptions, and status |
| File Manager | `/files` | Browse `archive/inbox/`, `archive/outputs/`, `archive/workspace/` |
| History | `/history` | View past prompts, their agent chains, outputs, and timestamps |
| Settings | `/settings` | Model selection, theme toggle, API keys, system config |
| Health Monitor | `/health` | Live status of Ollama, Docker, database, agents, memory store |

**Navigation:** All screens are accessible from a persistent **left sidebar** that is always visible. The sidebar collapses to icon-only mode on smaller viewports.

---

## 4. Screen 1: Landing / Dashboard

### Purpose
The first thing the user sees. It should feel like a mission control center — alive, dynamic, and informative at a glance.

### Layout
```
┌───────────────────────────────────────────────────────────────┐
│ [Sidebar]  │              DASHBOARD                           │
│            │                                                  │
│  Dashboard │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  Chat      │  │ Agents   │ │ Tasks    │ │ Uptime   │          │
│  Agents    │  │ Active:25│ │ Today: 12│ │ 4h 23m   │          │ 
│  Files     │  └──────────┘ └──────────┘ └──────────┘          │
│  History   │                                                  │
│  Settings  │  ┌────────────────────────────────────────────┐  │
│  Health    │  │  RECENT ACTIVITY FEED                      │  │
│            │  │  • 2m ago: email_agent read 3 new emails   │  │
│            │  │  • 15m ago: web_scraper fetched HN         │  │
│            │  │  • 1h ago: pdf_ocr_agent processed doc.pdf │  │
│            │  └────────────────────────────────────────────┘  │
│            │                                                  │
│            │  ┌────────────────────────────────────────────┐  │
│            │  │  QUICK ACTIONS                             │  │
│            │  │  [+ New Chat] [Upload File] [Run Health]   │  │
│            │  └────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### Stat Cards (Top Row)
| Card | Data Source | Icon Needed |
|------|-------------|-------------|
| Total Agents | Count of `agents.REGISTRY` | `icon-cpu` or `icon-bot` |
| Tasks Run Today | Count from `archive/results.json` history entries for today | `icon-zap` |
| System Uptime | Time since backend server started | `icon-clock` |
| Model Active | Currently selected LLM model name | `icon-brain` |
| Inbox Files | Count of files in `archive/inbox/` | `icon-inbox` |

### Recent Activity Feed
- Pulls from a log of recent orchestrator runs.
- Each entry shows: **timestamp**, **agent name** (with its icon), **action summary**.
- Clicking an entry navigates to `/history/<run_id>` for the detailed view.

### Quick Actions
| Button | Label | Action |
|--------|-------|--------|
| Primary CTA | "+ New Chat" | Navigates to `/chat` and clears the current session |
| Secondary | "Upload File" | Opens the OS file picker, uploads to `archive/inbox/` |
| Secondary | "Run Health Check" | Triggers `GET /api/health` and navigates to `/health` |

---

## 5. Screen 2: Chat Interface (Main Workspace)

### Purpose
This is the core of the product. The user types prompts, attaches files, and watches the Swarm think and act in real-time.

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│ [Sidebar]  │                CHAT WORKSPACE                         │
│            │                                                       │
│            │  ┌──────────────────────────────────────────────────┐ │
│            │  │                                                  │ │
│            │  │  [User Bubble]  "Scrape the top 5 headlines      │ │
│            │  │                  from Hacker News"               │ │
│            │  │                                                  │ │
│            │  │  [Thinking Panel - Collapsible]                  │ │
│            │  │  ┌──────────────────────────────────────┐        │ │
│            │  │  │ Step 1: Calling web_scraper...       │        │ │
│            │  │  │ Step 2: Result received (200 OK)     │        │ │
│            │  │  │ Step 3: Calling ner_agent...         │        │ │
│            │  │  │ Step 4: Final answer generated       │        │ │
│            │  │  └──────────────────────────────────────┘        │ │
│            │  │                                                  │ │
│            │  │  [Assistant Bubble]                              │ │
│            │  │  "Here are the top 5 headlines from HN:          │ │
│            │  │   1. ...                                         │ │
│            │  │   2. ..."                                        │ │
│            │  │                                                  │ │
│            │  │  [File Output Card]   (if result is a file)      │ │
│            │  │  ┌─────────────────────────────┐                 │ │
│            │  │  │ 📄 export_competitors.csv   │                 │ │
│            │  │  │ Size: 12.4 KB               │                 │ │
│            │  │  │ [Download] [Preview]         │                │ │
│            │  │  └─────────────────────────────┘                 │ │
│            │  │                                                  │ │
│            │  └──────────────────────────────────────────────────┘ │
│            │                                                       │
│            │  ┌──────────────────────────────────────────────────┐ │
│            │  │ [Attach 📎] [Type your message...         ] [➤] ││ │
│            │  └──────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

### Chat Message Types

#### 1. User Message Bubble
- **Alignment:** Right-aligned.
- **Color:** Accent/brand color background, white text.
- **Contains:**
  - The raw text the user typed.
  - If files were attached: a small file chip/tag showing the filename and type icon.
    - e.g., `[icon-file-audio] meeting_recording.mp3`
  - Timestamp (subtle, below the bubble).

#### 2. Assistant Message Bubble
- **Alignment:** Left-aligned.
- **Color:** Subtle glass/translucent background on dark mode, soft gray on light mode.
- **Contains:**
  - The final answer text from the Orchestrator.
  - Supports **Markdown rendering**: bold, italic, code blocks, tables, lists.
  - If the answer includes a generated file (CSV, JSON, PDF): render a **File Output Card** (see below).

#### 3. Thinking/Reasoning Panel (Collapsible)
- **Purpose:** Shows the ReAct loop in real-time as the Orchestrator works.
- **Default state:** Collapsed (just shows "Thinking... 3 steps completed").
- **Expanded state:** Shows each step:
  - `Step 1: [icon-search] Calling web_scraper(url="https://...")` — with a spinning loader.
  - `Step 2: [icon-check-circle] Result received (200 OK, 1.2s)` — with a green checkmark.
  - `Step 3: [icon-alert-triangle] Error: SSL Certificate Failed. Retrying...` — with a yellow warning.
  - `Step 4: [icon-cpu] Calling ner_agent(text="$scraped_text")` — with agent icon.
  - `Step 5: [icon-flag] Final answer generated.`
- **Interaction:** Click to expand/collapse. Each step is a distinct row with its own icon and status color.
- **Condition:** If the Orchestrator hits `MAX_STEPS` (20) without a `final_answer`, show a red error bar: *"The Orchestrator exceeded the maximum step limit (20). The task may be too complex. Consider breaking it into smaller subtasks."*

#### 4. File Output Card
- **When shown:** Whenever the Orchestrator generates a file as output (CSV export, JSON result, transcribed text file, etc.).
- **Contents:**
  - File type icon (see Icon Inventory below).
  - File name.
  - File size.
  - **[Download]** button: Triggers a browser download of the file from `archive/outputs/`.
  - **[Preview]** button: Opens a modal with a preview:
    - `.csv` / `.json`: Rendered as a table.
    - `.txt` / `.md`: Rendered as formatted text.
    - `.png` / `.jpg`: Rendered as an image.
    - `.mp3` / `.wav`: Rendered as an audio player.
    - `.pdf`: Rendered in an embedded PDF viewer (or first-page preview).
  - **[Copy Path]** button: Copies the absolute file path to clipboard for use in follow-up prompts.

### Input Bar (Bottom of Chat)

#### Components (Left to Right):
| Element | Type | Behavior |
|---------|------|----------|
| Attach Button `📎` | Icon Button | Opens OS file picker. Accepted types: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.mp3`, `.wav`, `.m4a`, `.mp4`, `.csv`, `.json`, `.txt`, `.md`, `.docx`, `.xlsx`. Selected file is uploaded to `archive/inbox/` and a file chip appears above the input bar. |
| Text Input | Multiline textarea | Auto-grows up to 6 lines. Placeholder: *"Ask anything, or drop a file..."*. Supports `Shift+Enter` for newlines. `Enter` alone sends the message. |
| Send Button `➤` | Icon Button | Sends the current text + any attached files to `POST /api/chat`. Disabled (grayed out) when input is empty AND no file is attached. Shows a spinner while the Orchestrator is processing. |
| Stop Button `◼` | Icon Button | **Only visible while the Orchestrator is processing.** Replaces the Send button. Sends a cancel signal to abort the current ReAct loop. The Orchestrator returns whatever partial results it has gathered so far. |

#### File Attachment Chips (Conditional)
- When one or more files are attached, a row of **file chips** appears directly above the input bar.
- Each chip shows: `[type-icon] filename.ext [x]`
- The `[x]` removes the attachment before sending.
- **Drag & Drop:** The entire chat area supports drag-and-drop. When a file is dragged over the chat, a full-screen overlay appears: *"Drop file here to attach"* with a dashed border animation.
- **Paste from Clipboard:** If the user pastes an image from clipboard (`Ctrl+V`), it is automatically captured and attached as a `.png`.
- **Multiple Files:** Up to 5 files can be attached per message. If the user tries to add a 6th, show a toast: *"Maximum 5 files per message."*

#### Conditions & Edge Cases for the Input Bar:
| Condition | Behavior |
|-----------|----------|
| User sends empty text with no file | Send button is disabled. Nothing happens. |
| User sends empty text WITH a file | Valid. The Orchestrator receives: *"Process the attached file: meeting.mp3"* (auto-generated prompt). |
| User sends text with file | Both the text prompt and the file path are sent to the backend. |
| User sends while Orchestrator is still processing a previous request | Queue the message. Show a toast: *"Previous task is still running. Your message has been queued."* |
| User presses Stop | Orchestrator aborts. Partial results are displayed. A warning message appears: *"Task was interrupted. Partial results may be incomplete."* |
| Network disconnection during processing | WebSocket reconnects automatically. If it fails after 3 retries, show: *"Connection lost. Please check your network."* |
| Orchestrator returns an empty final_answer | Show: *"The agents completed their work but did not produce a summary. Check the Thinking panel for raw results."* |

---

## 6. Screen 3: Agent Registry Panel

### Purpose
A browsable catalog of every agent in the system. Each agent is displayed as a card with its name, description, parameters, status, and brand logo (if applicable).

### Layout
```
┌──────────────────────────────────────────────────────────────────┐
│ [Sidebar]  │              AGENT REGISTRY                         │
│            │                                                      │
│            │  [Search: ___________________________] [Filter ▼]    │
│            │                                                      │
│            │  ┌─────────────────┐  ┌─────────────────┐           │
│            │  │ [GitHub Logo]   │  │ [Mail Icon]     │           │
│            │  │ github_agent    │  │ email_agent     │           │
│            │  │ Clone repos,    │  │ Read inbox,     │           │
│            │  │ branch, commit  │  │ send emails     │           │
│            │  │                 │  │                 │           │
│            │  │ Status: ● Active│  │ Status: ○ No    │           │
│            │  │ [Try It →]      │  │ credentials     │           │
│            │  └─────────────────┘  │ [Configure →]   │           │
│            │                       └─────────────────┘           │
│            │  ┌─────────────────┐  ┌─────────────────┐           │
│            │  │ [DB Icon]       │  │ [File Icon]     │           │
│            │  │ sql_db_agent    │  │ file_system_    │           │
│            │  │ Query SQLite    │  │ agent           │           │
│            │  │ databases       │  │ Read/write in   │           │
│            │  │                 │  │ sandboxed dir   │           │
│            │  │ Status: ● Active│  │ Status: ● Active│           │
│            │  │ [Try It →]      │  │ [Try It →]      │           │
│            │  └─────────────────┘  └─────────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

### Agent Card (Detailed Breakdown)
| Element | Description |
|---------|-------------|
| **Icon/Logo** | The agent's brand icon or generic category icon (see Icon Inventory). For `github_agent` this is the GitHub Octocat logo. For `email_agent` this is a mail icon. |
| **Agent Name** | The Python function name, e.g., `github_agent`. |
| **Category Badge** | A small colored pill: `System of Record`, `Communicator`, `Archivist`, `Local Admin`, `Optimizer`, `Legacy`. |
| **Description** | First sentence of the agent's `DESCRIPTION` constant. |
| **Parameters** | Expandable section listing all parameters with their types and whether they are required or optional. |
| **Status Indicator** | A colored dot: `● Green` = Active & Ready, `○ Gray` = Missing Dependencies (e.g., no Playwright, no Docker), `● Yellow` = Degraded (e.g., API rate limited). |
| **[Try It →]** button | Opens a quick-test modal where the user can manually fill in the agent's parameters and execute a single call. The result is displayed in the modal. |
| **[Configure →]** button | Only shown for agents that require setup (email credentials, API keys, GitHub tokens). Opens the Settings page pre-scrolled to that agent's config section. |
| **Last Used** | Timestamp of the last time this agent was called by the Orchestrator. *"Never"* if not yet used. |

### Search & Filter Bar
| Element | Behavior |
|---------|----------|
| Search input | Filters agents by name or description substring in real-time as the user types. |
| Filter dropdown | Options: `All`, `System of Record`, `Communicator`, `Archivist`, `Local Admin`, `Optimizer`, `Legacy`. Selecting a category filters the grid. |
| Sort dropdown | Options: `A-Z`, `Most Used`, `Recently Used`, `Status`. |

### Agent Categories & Their Members
| Category | Agents | Badge Color |
|----------|--------|-------------|
| System of Record | `sql_db_agent`, `api_discovery_agent` | Blue |
| Communicator | `email_agent`, `calendar_agent`, `social_media_agent` | Green |
| Archivist | `pdf_ocr_agent`, `audio_transcription_agent`, `vision_agent` | Purple |
| Local Admin | `github_agent`, `file_system_agent`, `code_executor_agent` | Orange |
| Optimizer | `self_reflection_agent`, `qa_agent`, `memory_agent` | Red |
| Legacy | `web_scraper`, `link_extractor`, `ner_agent`, `sentiment_analysis`, `page_classifier`, `topic_modeling`, `data_exporter_agent`, `deep_research_agent`, `search_agent`, `meta_agent`, `auth_agent`, `browser_agent`, `external_service_agent` | Gray |

---

## 7. Screen 4: File Manager (Inbox & Outputs)

### Purpose
A visual file browser for the three key directories the Swarm uses. This is where users drop files for processing and retrieve results.

### Three Tabs
| Tab | Directory | Purpose |
|-----|-----------|---------|
| **Inbox** | `archive/inbox/` | Files the user drops here for the Swarm to process. |
| **Outputs** | `archive/outputs/` | Files generated by agents (CSVs, transcriptions, exports). |
| **Workspace** | `archive/workspace/` | The `file_system_agent`'s sandboxed working directory. |

### File List (Per Tab)
Each file row shows:
| Column | Description |
|--------|-------------|
| Type Icon | Icon based on file extension (see Icon Inventory) |
| Filename | Clickable — opens preview modal |
| Size | Human-readable (e.g., "12.4 KB", "3.2 MB") |
| Date Modified | Relative timestamp (e.g., "2 minutes ago") |
| Actions | `[Preview]` `[Download]` `[Delete]` `[Copy Path]` |

### Upload Zone (Inbox Tab Only)
- A **drag-and-drop zone** at the top of the Inbox tab.
- Dashed border, centered text: *"Drag files here or click to upload"*.
- Clicking opens the OS file picker.
- Supported file types: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.gif`, `.mp3`, `.wav`, `.m4a`, `.mp4`, `.csv`, `.json`, `.txt`, `.md`, `.docx`, `.xlsx`, `.pptx`.
- After upload: file appears in the list immediately. A toast confirms: *"meeting.mp3 uploaded to Inbox."*
- **Condition: File too large** (>100MB): Show warning toast: *"File exceeds 100MB limit. Large audio/video files may cause slow processing."* — but still allow the upload.
- **Condition: Unsupported file type**: Show error toast: *"File type .exe is not supported."* — reject the upload.

### Preview Modal
| File Type | Preview Behavior |
|-----------|-----------------|
| `.pdf` | Embedded PDF viewer (iframe or pdf.js) |
| `.csv` | Parsed and rendered as an HTML table with sortable columns |
| `.json` | Syntax-highlighted JSON viewer with collapse/expand |
| `.txt`, `.md` | Rendered as formatted text / Markdown |
| `.png`, `.jpg`, `.jpeg`, `.gif` | Full-size image with zoom controls |
| `.mp3`, `.wav`, `.m4a` | HTML5 audio player with waveform visualization |
| `.mp4` | HTML5 video player |
| `.docx` | First page rendered as image (or raw text extraction) |
| `.xlsx` | Parsed first sheet rendered as HTML table |

---

## 8. Screen 5: History & Past Results

### Purpose
A log of every task the user has ever sent to the Orchestrator. Each entry is expandable to show the full chain of agent calls, intermediate results, and the final answer.

### Layout
```
┌──────────────────────────────────────────────────────────────┐
│ HISTORY                                                      │
│                                                              │
│ [Search: _______________] [Date Range ▼] [Agent Filter ▼]   │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ ▶ "Scrape HN headlines and extract named entities"       │ │
│ │   2026-07-04 21:30  |  3 agents  |  4.2s  |  ✅ Success  │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ ▶ "Read the PDF in my inbox and summarize it"            │ │
│ │   2026-07-04 20:15  |  2 agents  |  6.1s  |  ✅ Success  │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ ▶ "Delete the users table from the database"             │ │
│ │   2026-07-04 19:00  |  1 agent   |  0.1s  |  🛡️ Blocked │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### History Entry (Collapsed)
| Field | Description |
|-------|-------------|
| Prompt preview | First 80 characters of the user's original prompt |
| Timestamp | When the task was submitted |
| Agent count | How many agents were called during execution |
| Duration | Total wall-clock time for the task |
| Status | `✅ Success`, `⚠️ Partial`, `❌ Failed`, `🛡️ Blocked` (safety rail triggered) |

### History Entry (Expanded)
When clicked, the entry expands to show:
1. **Full Original Prompt** — the complete text the user typed.
2. **Attached Files** — any files that were attached (with clickable links).
3. **Agent Chain** — a vertical timeline showing each agent call:
   - Agent name + icon.
   - Input arguments that were passed.
   - Output result (truncated to 500 chars with "Show more" toggle).
   - Duration of that individual agent call.
   - Status: success / error / skipped.
4. **Final Answer** — the complete Orchestrator response with Markdown rendering.
5. **Generated Files** — any output files, with Download/Preview buttons.
6. **Actions:**
   - **[Re-run]** — Sends the exact same prompt again (useful for retrying after fixing a dependency).
   - **[Copy Prompt]** — Copies the original prompt to clipboard.
   - **[Export as JSON]** — Downloads the entire run as a structured JSON log.

### Filters
| Filter | Options |
|--------|---------|
| Date Range | Today, Last 7 days, Last 30 days, All Time, Custom Range |
| Agent Filter | Dropdown of all agents — shows only runs that used the selected agent |
| Status Filter | All, Success, Partial, Failed, Blocked |
| Search | Full-text search across prompts and final answers |

---

## 9. Screen 6: Settings & Model Configuration

### Purpose
Central configuration hub for LLM models, API credentials, theme preferences, and system behavior.

### Sections

#### 6.1 Model Selection
| Setting | Type | Options | Current Default |
|---------|------|---------|-----------------|
| Primary Model | Dropdown | `llama3.1:8b`, `qwen3.5:9b`, `llama3.2:3b`, `gemma4:e2b-mlx`, `gemini-2.5-flash` | `llama3.1:8b` |
| Vision Model | Dropdown | `qwen3-vl:4b`, `llama3.2-vision:latest` | `qwen3-vl:4b` |
| Speed Model (Small Tasks) | Dropdown | `llama3.2:3b`, `qwen3.5:9b` | `llama3.2:3b` |
| Cloud Fallback | Toggle | Enable/Disable | Disabled |
| Cloud API Key | Password input | Gemini API key (masked) | From `.env` |

**Condition:** If the user selects a model that is not currently pulled in Ollama, show a warning banner: *"Model qwen3.5:9b is not available locally. Pull it with: `ollama pull qwen3.5:9b`"* with a **[Pull Now]** button that runs the pull command.

#### 6.2 Agent Credentials
| Agent | Required Credential | Input Type |
|-------|-------------------|------------|
| `email_agent` | EMAIL_USER, EMAIL_PASS | Text input, Password input |
| `email_agent` | IMAP_SERVER, SMTP_SERVER | Text input (pre-filled defaults: imap.gmail.com, smtp.gmail.com) |
| `github_agent` | GITHUB_TOKEN | Password input |
| `external_service_agent` | APIFY_TOKEN, BRIGHTDATA_TOKEN | Password input |
| `social_media_agent` | TWITTER_BEARER_TOKEN | Password input |

Each credential section has:
- **[Save]** button — writes to `.env` file.
- **[Test Connection]** button — runs a quick validation (e.g., tries IMAP login for email).
- **Status indicator** — Shows `Connected ●` or `Not Configured ○` based on whether the key exists in `.env`.

#### 6.3 System Behavior
| Setting | Type | Description | Default |
|---------|------|-------------|---------|
| Max ReAct Steps | Number input (range: 5-50) | Maximum iterations before the Orchestrator gives up | 20 |
| Context Limit | Number input (range: 200-2000) | Max words of tool output echoed back to the LLM | 800 |
| Auto-Save Results | Toggle | Automatically save every run to `archive/results.json` | Enabled |
| Verbose Mode | Toggle | Show all intermediate reasoning in the chat | Enabled |
| Human-in-the-Loop | Toggle | Require confirmation before executing dangerous tools (email send, file delete, data export) | Enabled |

#### 6.4 Appearance
| Setting | Type | Options |
|---------|------|---------|
| Theme | Toggle | Dark Mode / Light Mode |
| Accent Color | Color picker | Default: Electric Blue `#3B82F6` |
| Font | Dropdown | Inter (default), Roboto, JetBrains Mono |
| Sidebar Position | Toggle | Left / Right |

---

## 10. Screen 7: Health Monitor / System Status

### Purpose
A real-time dashboard showing whether all system dependencies are operational.

### Health Checks
| Component | Check Method | Healthy State | Unhealthy State |
|-----------|-------------|---------------|-----------------|
| Ollama Server | `GET http://localhost:11434/api/tags` | `● Running (5 models loaded)` | `○ Ollama is not running` |
| Primary LLM (`llama3.1:8b`) | Check if model exists in Ollama tags response | `● Available` | `○ Model not pulled` |
| Vision LLM (`qwen3-vl:4b`) | Check if model exists in Ollama tags response | `● Available` | `○ Model not pulled` |
| SQLite Database | `SELECT 1` on `database.db` | `● Connected (3 tables)` | `○ Database file missing` |
| Docker Engine | `docker info` | `● Running` | `○ Docker not running — code_executor_agent disabled` |
| Vector Memory | Check if `/memory/` directory has `.pkl` files | `● Active (128 memories stored)` | `○ Empty` |
| Inbox Folder | Check if `archive/inbox/` exists and count files | `● Ready (2 files pending)` | `○ Directory missing` |
| Playwright | `import playwright` | `● Installed` | `○ Not installed — auth_agent and browser_agent disabled` |
| ffmpeg | `which ffmpeg` | `● Installed` | `○ Not installed — audio_transcription_agent limited` |
| PyPDF2 | `import PyPDF2` | `● Installed` | `○ Not installed — pdf_ocr_agent disabled` |

Each component is a **card** with a status dot, name, and status message. Unhealthy components have a **[Fix]** button that either shows installation instructions or runs the fix command automatically.

---

## 11. All Buttons, Actions & Operations

This is the **complete** inventory of every clickable element in the UI.

### Global (Always Visible)
| Button | Location | Action | Icon |
|--------|----------|--------|------|
| Sidebar Toggle | Top-left corner | Collapses/expands the sidebar | `icon-menu` / `icon-x` |
| Theme Toggle | Sidebar footer | Switches between dark/light mode | `icon-moon` / `icon-sun` |
| New Chat | Sidebar | Creates a new chat session | `icon-plus` |

### Dashboard Buttons
| Button | Action | Icon |
|--------|--------|------|
| + New Chat | Navigate to `/chat` | `icon-message-square-plus` |
| Upload File | Open file picker, upload to inbox | `icon-upload` |
| Run Health Check | Navigate to `/health`, trigger checks | `icon-activity` |
| View All History | Navigate to `/history` | `icon-clock` |

### Chat Interface Buttons
| Button | Action | Icon | State Conditions |
|--------|--------|------|------------------|
| Attach File | Open file picker | `icon-paperclip` | Always enabled |
| Send Message | Submit prompt to backend | `icon-send` | Disabled when empty input AND no file |
| Stop | Cancel running task | `icon-square` | Only visible during processing |
| Expand Thinking | Toggle ReAct panel visibility | `icon-chevron-down` / `icon-chevron-up` | Only visible when there are steps |
| Copy Answer | Copy final answer to clipboard | `icon-copy` | On hover of assistant message |
| Re-run | Re-send the same prompt | `icon-refresh-cw` | On hover of user message |
| Download File | Download generated file | `icon-download` | On File Output Cards |
| Preview File | Open file preview modal | `icon-eye` | On File Output Cards |
| Copy Path | Copy file path to clipboard | `icon-clipboard` | On File Output Cards |
| Remove Attachment | Remove attached file before sending | `icon-x` | On file chips |

### Agent Registry Buttons
| Button | Action | Icon |
|--------|--------|------|
| Try It → | Open quick-test modal | `icon-play` |
| Configure → | Navigate to settings for that agent | `icon-settings` |
| Expand Params | Show/hide parameter details | `icon-chevron-down` |

### File Manager Buttons
| Button | Action | Icon |
|--------|--------|------|
| Upload (Inbox only) | Upload file to inbox | `icon-upload` |
| Preview | Open preview modal | `icon-eye` |
| Download | Trigger browser download | `icon-download` |
| Delete | Delete file (with confirmation dialog) | `icon-trash-2` |
| Copy Path | Copy absolute path to clipboard | `icon-clipboard` |
| Refresh | Re-scan directory for new files | `icon-refresh-cw` |

### History Buttons
| Button | Action | Icon |
|--------|--------|------|
| Expand Entry | Show full details of a run | `icon-chevron-down` |
| Re-run | Re-send original prompt | `icon-refresh-cw` |
| Copy Prompt | Copy original prompt to clipboard | `icon-copy` |
| Export as JSON | Download full run log | `icon-download` |

### Settings Buttons
| Button | Action | Icon |
|--------|--------|------|
| Save | Save credential/setting changes | `icon-save` |
| Test Connection | Validate credential | `icon-zap` |
| Pull Model | Run `ollama pull <model>` | `icon-download-cloud` |
| Reset to Defaults | Reset all settings | `icon-rotate-ccw` |

### Health Monitor Buttons
| Button | Action | Icon |
|--------|--------|------|
| Fix | Show fix instructions or auto-fix | `icon-wrench` |
| Re-check | Re-run health check for that component | `icon-refresh-cw` |
| Re-check All | Re-run all health checks | `icon-refresh-cw` |

---

## 12. All Input Types & How They Are Handled

### Text Prompts
- **Source:** Chat input bar.
- **Processing:** Sent directly to `POST /api/chat` as `{ "prompt": "...", "files": [...] }`.
- **The Orchestrator** determines which agents to call based on the text content.

### File Inputs
| File Type | Extension(s) | Routed To | Processing |
|-----------|-------------|-----------|------------|
| PDF Document | `.pdf` | `pdf_ocr_agent` | Text extraction, OCR, search |
| Audio Recording | `.mp3`, `.wav`, `.m4a` | `audio_transcription_agent` | Whisper transcription |
| Video | `.mp4` | `audio_transcription_agent` (audio track extraction via ffmpeg) | Extract audio, then transcribe |
| Image | `.png`, `.jpg`, `.jpeg`, `.gif` | `vision_agent` | Visual description via `qwen3-vl:4b` |
| Spreadsheet | `.csv`, `.xlsx` | `data_exporter_agent` or `sql_db_agent` | Import into DB or parse |
| Text / Markdown | `.txt`, `.md` | Direct LLM context injection | Content is read and passed as context |
| Word Document | `.docx` | `pdf_ocr_agent` (with python-docx extraction fallback) | Text extraction |
| JSON Data | `.json` | `data_exporter_agent` or direct context injection | Parse and present |
| Code Files | `.py`, `.js`, `.ts`, etc. | `code_executor_agent` or direct LLM analysis | Execute or review |

### Drag & Drop
- **Supported areas:** Chat interface (full area), File Manager Inbox tab.
- **Visual feedback:** When dragging over a valid drop zone, the zone highlights with a dashed blue border and shows text: *"Drop file here"*.
- **On drop:** File is uploaded to `archive/inbox/`, and a file chip appears in the chat input bar.

### Clipboard Paste
- **Supported content:** Images from clipboard (`Ctrl+V` / `Cmd+V`).
- **Behavior:** Image is saved as `clipboard_YYYY-MM-DD_HH-MM-SS.png` in `archive/inbox/` and attached to the message.

### Voice Input (Future v2)
- A microphone button next to the text input.
- Uses browser Web Speech API for speech-to-text.
- Transcribed text appears in the input bar for review before sending.

---

## 13. Output Display Rules

### How Different Output Types Are Rendered

| Output Type | Rendering |
|-------------|-----------|
| **Plain Text** | Rendered inside an assistant message bubble with Markdown support |
| **Table / Structured Data** | Rendered as an HTML table with alternating row colors, sortable headers |
| **Code** | Syntax-highlighted code block with a **[Copy]** button |
| **Generated File** | File Output Card (see Section 5) with Download/Preview |
| **Error Message** | Red-tinted bubble with `icon-alert-circle` and error description |
| **Safety Block** | Orange-tinted bubble with `icon-shield` and explanation of why the action was blocked |
| **Long Output** (>2000 chars) | Truncated with a **[Show Full Output]** toggle |
| **Image Result** | Inline embedded image with zoom-on-click |
| **Audio Result** | Inline HTML5 audio player |
| **Multiple Results** | Each result is its own card/section, stacked vertically |

### Real-Time Streaming
- The Orchestrator's steps stream in via WebSocket.
- Each step appears as a new line in the Thinking Panel with a subtle slide-in animation.
- The final answer streams token-by-token into the assistant bubble (typewriter effect).

---

## 14. Error States & Edge Cases

| Scenario | UI Behavior |
|----------|-------------|
| Ollama is not running | Banner at top of all pages: *"Ollama is offline. Start it with `ollama serve`."* `[Dismiss]` `[Check Again]` |
| Selected model not pulled | Toast: *"Model llama3.1:8b not found. Run `ollama pull llama3.1:8b`."* |
| Agent crashes mid-execution | Step in Thinking Panel turns red. Orchestrator attempts retry. If retry fails, shows error in assistant bubble. |
| WebSocket disconnects | Reconnect attempt every 2s for 3 tries. After failure: modal overlay *"Connection lost. Reconnecting..."* |
| File upload fails | Toast: *"Failed to upload meeting.mp3. Please try again."* |
| Empty database (no tables) | `sql_db_agent` returns graceful message: *"Database is empty."* — not an error. |
| Path traversal attempt | `file_system_agent` blocks and returns: *"SECURITY BLOCK: Attempted path traversal."* — rendered as a Safety Block bubble. |
| Destructive SQL (DROP/TRUNCATE) | `sql_db_agent` blocks and returns: *"SECURITY BLOCK: Destructive commands are disabled."* |
| Email credentials missing | `email_agent` returns: *"Missing EMAIL_USER or EMAIL_PASS."* — assistant bubble shows error with a **[Configure Email →]** link to Settings. |
| Docker not running | `code_executor_agent` returns: *"Docker is not running."* — assistant bubble shows error with instructions. |
| Rate limited (external APIs) | Agent retries 3 times with exponential backoff. If all fail, shows: *"Rate limited. Try again in X seconds."* |
| LLM returns invalid JSON | Orchestrator retries the LLM call up to 3 times. If all fail: *"The model failed to produce valid output. Consider switching to a larger model in Settings."* |
| Task exceeds MAX_STEPS (20) | Red banner in chat: *"Task exceeded maximum steps. Break it into smaller subtasks."* |
| Inbox folder is empty when referenced | Orchestrator: *"No files found in the Inbox. Please upload a file first."* |

---

## 15. Notification & Toast System

### Toast Notifications
- **Position:** Bottom-right corner, stacked vertically.
- **Auto-dismiss:** After 5 seconds (configurable).
- **Types:**

| Type | Color | Icon | Example |
|------|-------|------|---------|
| Success | Green | `icon-check-circle` | *"File uploaded successfully."* |
| Error | Red | `icon-alert-circle` | *"Failed to connect to Ollama."* |
| Warning | Yellow | `icon-alert-triangle` | *"Model not found locally."* |
| Info | Blue | `icon-info` | *"Task queued. Previous task still running."* |

### Confirmation Dialogs
Used for destructive actions:
- **Delete file:** *"Are you sure you want to delete meeting.mp3? This cannot be undone."* `[Cancel]` `[Delete]`
- **Reset session:** *"This will clear all chat history for this session."* `[Cancel]` `[Reset]`
- **HITL approval:** *"The Orchestrator wants to send an email to boss@company.com. Allow?"* `[Deny]` `[Allow]`

---

## 16. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line in input |
| `Ctrl/Cmd + K` | Focus search (global) |
| `Ctrl/Cmd + N` | New chat session |
| `Ctrl/Cmd + U` | Open file upload picker |
| `Ctrl/Cmd + .` | Toggle sidebar |
| `Ctrl/Cmd + D` | Toggle dark/light mode |
| `Escape` | Close any open modal or dialog |
| `Ctrl/Cmd + Shift + T` | Toggle Thinking panel |
| `Up Arrow` (in empty input) | Recall last sent message |

---

## 17. Icon Inventory (SVG/Icon Library Required)

> **Recommendation:** Use **Lucide Icons** (https://lucide.dev) — an open-source, consistent, and lightweight SVG icon library. All icon names below reference Lucide icon names. Alternatively, **Phosphor Icons** or **Tabler Icons** are acceptable substitutes.

### Navigation & Layout Icons
| Icon Name | Lucide Name | Used For |
|-----------|-------------|----------|
| `icon-menu` | `menu` | Sidebar hamburger toggle |
| `icon-x` | `x` | Close buttons, remove chips |
| `icon-chevron-down` | `chevron-down` | Expand/collapse sections |
| `icon-chevron-up` | `chevron-up` | Collapse sections |
| `icon-chevron-right` | `chevron-right` | Breadcrumbs, navigation |
| `icon-sidebar` | `panel-left` | Sidebar indicator |

### Action Icons
| Icon Name | Lucide Name | Used For |
|-----------|-------------|----------|
| `icon-send` | `send-horizontal` | Send message button |
| `icon-square` | `square` | Stop/cancel button |
| `icon-plus` | `plus` | New item / add |
| `icon-upload` | `upload` | File upload |
| `icon-download` | `download` | File download |
| `icon-download-cloud` | `cloud-download` | Pull model from Ollama |
| `icon-copy` | `copy` | Copy to clipboard |
| `icon-clipboard` | `clipboard` | Copy path to clipboard |
| `icon-refresh-cw` | `refresh-cw` | Re-run / refresh |
| `icon-rotate-ccw` | `rotate-ccw` | Reset to defaults |
| `icon-save` | `save` | Save settings |
| `icon-trash-2` | `trash-2` | Delete |
| `icon-play` | `play` | Try it / execute |
| `icon-settings` | `settings` | Configure |
| `icon-wrench` | `wrench` | Fix / repair |
| `icon-paperclip` | `paperclip` | Attach file |
| `icon-eye` | `eye` | Preview |
| `icon-search` | `search` | Search |
| `icon-filter` | `filter` | Filter |

### Status Icons
| Icon Name | Lucide Name | Used For |
|-----------|-------------|----------|
| `icon-check-circle` | `check-circle-2` | Success / passed |
| `icon-alert-circle` | `alert-circle` | Error |
| `icon-alert-triangle` | `alert-triangle` | Warning |
| `icon-info` | `info` | Informational |
| `icon-shield` | `shield` | Security block |
| `icon-loader` | `loader-2` | Loading spinner (animated) |
| `icon-zap` | `zap` | Quick action / test connection |
| `icon-activity` | `activity` | Health check / system pulse |

### Domain / Feature Icons
| Icon Name | Lucide Name | Used For |
|-----------|-------------|----------|
| `icon-message-square` | `message-square` | Chat |
| `icon-message-square-plus` | `message-square-plus` | New chat |
| `icon-bot` | `bot` | Agent / AI |
| `icon-cpu` | `cpu` | Processing / agent call |
| `icon-brain` | `brain` | LLM / model |
| `icon-database` | `database` | `sql_db_agent` |
| `icon-globe` | `globe` | `web_scraper`, `api_discovery_agent`, `search_agent` |
| `icon-mail` | `mail` | `email_agent` |
| `icon-calendar` | `calendar` | `calendar_agent` |
| `icon-share-2` | `share-2` | `social_media_agent` |
| `icon-file-text` | `file-text` | `pdf_ocr_agent`, text files |
| `icon-mic` | `mic` | `audio_transcription_agent` |
| `icon-image` | `image` | `vision_agent`, image files |
| `icon-git-branch` | `git-branch` | `github_agent` |
| `icon-folder` | `folder` | `file_system_agent`, directories |
| `icon-terminal` | `terminal` | `code_executor_agent` |
| `icon-sparkles` | `sparkles` | `self_reflection_agent` |
| `icon-book-open` | `book-open` | `deep_research_agent` |
| `icon-tag` | `tag` | `ner_agent`, topics |
| `icon-bar-chart` | `bar-chart-2` | `sentiment_analysis` |
| `icon-layers` | `layers` | `page_classifier` |
| `icon-package` | `package` | `external_service_agent` |
| `icon-file-output` | `file-output` | `data_exporter_agent` |
| `icon-key` | `key` | `auth_agent` |
| `icon-monitor` | `monitor` | `browser_agent` |
| `icon-hard-drive` | `hard-drive` | `memory_agent` |
| `icon-award` | `award` | `qa_agent` |
| `icon-code` | `code` | `meta_agent` |
| `icon-link` | `link` | `link_extractor` |
| `icon-inbox` | `inbox` | Inbox folder |
| `icon-clock` | `clock` | Timestamps, history, uptime |
| `icon-moon` | `moon` | Dark mode toggle |
| `icon-sun` | `sun` | Light mode toggle |
| `icon-flag` | `flag` | Final answer marker |

### File Type Icons
| Icon Name | Lucide Name | File Extensions |
|-----------|-------------|-----------------|
| `icon-file` | `file` | Generic/unknown |
| `icon-file-text` | `file-text` | `.txt`, `.md` |
| `icon-file-json` | `file-json` | `.json` |
| `icon-file-spreadsheet` | `file-spreadsheet` | `.csv`, `.xlsx` |
| `icon-file-image` | `file-image` | `.png`, `.jpg`, `.jpeg`, `.gif` |
| `icon-file-audio` | `file-audio` | `.mp3`, `.wav`, `.m4a` |
| `icon-file-video` | `file-video` | `.mp4` |
| `icon-file-code` | `file-code` | `.py`, `.js`, `.ts`, `.html`, `.css` |
| `icon-file-type` | `file-type` | `.pdf` |
| `icon-file-archive` | `file-archive` | `.zip`, `.tar`, `.gz` |

---

## 18. Brand Logo Inventory (External Logos Required)

> These are **third-party brand logos** that should be displayed alongside their respective agents in the Agent Registry and in the Thinking Panel when those agents are called. Use official SVG logos. Ensure compliance with each brand's usage guidelines.

| Brand | Where Used | Logo Source |
|-------|-----------|-------------|
| **GitHub** (Octocat) | `github_agent` card, Thinking Panel | https://github.com/logos |
| **Google** (G icon) | `gemini` model selector, `search_agent` (Google fallback) | https://about.google/brand-resource-center/ |
| **Gmail** | `email_agent` card (when IMAP server is gmail) | Google Brand Resources |
| **Google Calendar** | `calendar_agent` card | Google Brand Resources |
| **Twitter / X** | `social_media_agent` card (twitter platform) | https://about.x.com/en/who-we-are/brand-toolkit |
| **LinkedIn** | `social_media_agent` card (linkedin platform), `auth_agent` | https://brand.linkedin.com/ |
| **Slack** | `api_discovery_agent` (Slack webhook examples) | https://slack.com/media-kit |
| **DuckDuckGo** | `search_agent` card (duckduckgo backend) | https://duckduckgo.com/press |
| **Wikipedia** | `search_agent` card (wikipedia backend) | https://commons.wikimedia.org/wiki/File:Wikipedia-logo-v2.svg |
| **arXiv** | `search_agent` card (arxiv backend) | https://arxiv.org |
| **Docker** | `code_executor_agent` card, Health Monitor | https://www.docker.com/company/newsroom/media-resources/ |
| **Ollama** | Settings model selector, Health Monitor | https://ollama.com |
| **Meta (Llama)** | Model selector for `llama3.1`, `llama3.2` | https://about.meta.com/brand/resources/ |
| **Alibaba (Qwen)** | Model selector for `qwen3-vl`, `qwen3.5` | Qwen project branding |
| **Google DeepMind (Gemma)** | Model selector for `gemma4` | Google Brand Resources |
| **Apify** | `external_service_agent` card | https://apify.com/press |
| **Bright Data** | `external_service_agent` card | https://brightdata.com |
| **SQLite** | `sql_db_agent` card | https://www.sqlite.org/ |
| **Python** | `code_executor_agent` card, general | https://www.python.org/community/logos/ |
| **OpenAI Whisper** | `audio_transcription_agent` card | OpenAI brand |

---

## 19. Design Tokens & Theme

### Color Palette (Dark Mode — Primary)
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#0A0A0F` | Main background |
| `--bg-secondary` | `#12121A` | Sidebar, cards |
| `--bg-tertiary` | `#1A1A28` | Elevated surfaces, modals |
| `--bg-input` | `#1E1E2E` | Input fields |
| `--text-primary` | `#E8E8ED` | Primary text |
| `--text-secondary` | `#8888A0` | Secondary/muted text |
| `--text-tertiary` | `#555570` | Disabled text, placeholders |
| `--accent` | `#3B82F6` | Primary accent (Electric Blue) |
| `--accent-hover` | `#2563EB` | Accent on hover |
| `--accent-subtle` | `rgba(59, 130, 246, 0.1)` | Accent backgrounds |
| `--success` | `#22C55E` | Success states |
| `--warning` | `#EAB308` | Warning states |
| `--error` | `#EF4444` | Error states |
| `--info` | `#3B82F6` | Info states |
| `--border` | `rgba(255, 255, 255, 0.06)` | Subtle borders |
| `--border-active` | `rgba(255, 255, 255, 0.12)` | Active/hovered borders |
| `--glass` | `rgba(255, 255, 255, 0.03)` | Glassmorphism surfaces |

### Color Palette (Light Mode)
| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-primary` | `#FAFAFA` | Main background |
| `--bg-secondary` | `#FFFFFF` | Sidebar, cards |
| `--bg-tertiary` | `#F5F5F5` | Elevated surfaces |
| `--bg-input` | `#EFEFEF` | Input fields |
| `--text-primary` | `#1A1A2E` | Primary text |
| `--text-secondary` | `#6B7280` | Secondary text |

### Typography
| Token | Value |
|-------|-------|
| `--font-primary` | `'Inter', system-ui, -apple-system, sans-serif` |
| `--font-mono` | `'JetBrains Mono', 'Fira Code', monospace` |
| `--font-size-xs` | `0.75rem` (12px) |
| `--font-size-sm` | `0.875rem` (14px) |
| `--font-size-base` | `1rem` (16px) |
| `--font-size-lg` | `1.125rem` (18px) |
| `--font-size-xl` | `1.5rem` (24px) |
| `--font-size-2xl` | `2rem` (32px) |

### Spacing
| Token | Value |
|-------|-------|
| `--space-xs` | `4px` |
| `--space-sm` | `8px` |
| `--space-md` | `16px` |
| `--space-lg` | `24px` |
| `--space-xl` | `32px` |
| `--space-2xl` | `48px` |

### Radius
| Token | Value |
|-------|-------|
| `--radius-sm` | `6px` |
| `--radius-md` | `10px` |
| `--radius-lg` | `16px` |
| `--radius-xl` | `24px` |
| `--radius-full` | `9999px` |

### Shadows
| Token | Value |
|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.5)` |
| `--shadow-glow` | `0 0 20px rgba(59, 130, 246, 0.15)` |

### Animations
| Token | Value | Usage |
|-------|-------|-------|
| `--transition-fast` | `150ms ease` | Hover states, toggles |
| `--transition-normal` | `250ms ease` | Panel open/close |
| `--transition-slow` | `400ms ease` | Page transitions |
| `--animation-pulse` | `pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite` | Loading indicators |
| `--animation-slide-in` | `slideIn 300ms ease-out` | New messages appearing |
| `--animation-fade-in` | `fadeIn 200ms ease` | Toast notifications |

---

## 20. Future Considerations (v2)

These features are **not** in v1 but should be architecturally accounted for so they can be added later without major refactoring:

| Feature | Description | Architecture Impact |
|---------|-------------|---------------------|
| **Council of Models** | Multiple LLMs debate internally before executing | New `/api/council` endpoint; new `council_orchestrator.py` |
| **Voice Input** | Microphone button for speech-to-text | Web Speech API; no backend change needed |
| **Multi-User Support** | Session isolation per user | Auth middleware; session tokens; user-scoped `archive/` directories |
| **Plugin Marketplace** | Install community-built agents | Agent hot-reloading; `agents/__init__.py` already supports auto-discovery |
| **Workflow Builder** | Visual drag-and-drop agent chaining | New `/workflows` page; DAG editor; saved workflow JSON schemas |
| **Mobile Responsive** | Full mobile support | CSS breakpoints; touch-friendly targets (48px minimum) |
| **PWA Support** | Installable as a desktop/mobile app | `manifest.json`; service worker for offline shell |
| **Webhook Triggers** | External events trigger Swarm tasks | New `POST /api/webhook` endpoint; event queue |
| **Scheduled Tasks** | Cron-like recurring agent runs | Backend scheduler (APScheduler); new `/schedules` page |
| **Real-Time Collaboration** | Multiple users see the same chat | WebSocket rooms; conflict resolution |

---

> **This document is a living reference.** Every new feature, button, screen, or edge case discovered during development must be added here before it is implemented. Nothing is built without being spec'd first.
