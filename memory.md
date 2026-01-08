# SiparisAgent Project Memory

## Project Overview
**SiparisAgent** is a fridge detection and automatic grocery ordering system. It uses YOLO for object detection to identify items in a fridge photo, then uses LLM to intelligently order missing items from Getir (Turkish grocery delivery app).

**Repository:** `/Users/atakan/Desktop/Projeler/SiparisAgent`

---

## Architecture

### Core Components

| Component | Path | Description |
|-----------|------|-------------|
| **Server** | `server.py` | Flask web server with REST API |
| **Detector** | `detection/detector.py` | YOLO-based fridge content detection |
| **Getir Client** | `browser/getir_client.py` | Playwright browser automation for Getir |
| **Migros Client** | `browser/migros_client.py` | Playwright browser automation for Migros |
| **Akbal Client** | `browser/akbal_client.py` | Playwright browser automation for Akbal Market |
| **LLM Module** | `ai/openrouter.py` | OpenRouter API for product selection |
| **Database** | `db/database.py` | SQLite for history and preferences |
| **Settings** | `config/settings.py` | App configuration (URLs, paths, etc.) |
| **Frontend** | `static/index.html`, `app.js`, `style.css` | Web UI |

### Database Schema (`data/fridge.db`)
```sql
-- Fridge history table
CREATE TABLE fridge_history (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    detected_items TEXT NOT NULL,  -- JSON
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User preferences
CREATE TABLE preferences (
    id INTEGER PRIMARY KEY,
    custom_instructions TEXT,
    default_mode TEXT,
    preferred_provider TEXT DEFAULT 'getir',  -- 'getir', 'migros', or 'akbal'
    detection_threshold REAL DEFAULT 0.5      -- Confidence threshold (0.0-1.0)
);
```

---

## Features Implemented

### 1. Fridge Detection
- Upload fridge image (drag & drop, file picker, paste)
- YOLO detection with configurable confidence threshold (saved to DB)
- Detects: milk, eggs, cheese, water_bottle, tomato, cucumber, orange, lemon, butter
- **Bounding box visualization**: Toggle checkbox to show/hide detection boxes with labels and confidence scores on the image
- Color-coded boxes per product category

### 2. Smart Product Selection
- Uses OpenRouter API (Llama 3.1 405B) for intelligent product choice
- Preferences: cheapest, cheapest per unit, organic, popular brand
- Custom instructions text field
- Falls back to first product if LLM fails

### 3. Getir Integration
- Browser automation with Playwright
- Product search, scraping, and cart addition
- Smart product selection via LLM

### 3b. Migros Integration
- Browser automation with Playwright (same pattern as Getir)
- Product search at migros.com.tr
- Session persistence for login state
- Handles cookie popups and delivery method selection
- Provider selection UI in frontend (radio buttons)
- Preference saved to database and localStorage

### 3c. Akbal Market Integration
- Browser automation with Playwright
- Product search at akbalmarket.com (Magento 2 store)
- No login required - cart works without authentication
- Simpler flow: search → add to cart → checkout

### 4. History System
- Save fridge detections with custom dates
- View history in UI
- Delete individual records or clear all
- History persisted to SQLite

### 5. History Analysis
- "Analyze History" button
- LLM analyzes consumption patterns
- Suggests items to order based on what's missing from current fridge state
- Compares current inventory to previous entries

### 6. Turkish Language Support (i18n)
- Language picker (EN/TR) in header
- All UI text translated
- Language preference saved to localStorage

### 7. Custom Instructions Persistence
- Instructions saved to database on blur
- Loaded on page refresh

### 8. Detection Threshold Persistence
- Threshold slider value saved to database on change
- Loaded on page refresh

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serve frontend |
| POST | `/detect` | Detect items in image (returns bboxes) |
| POST | `/order` | Order items via AI suggestions |
| GET | `/history` | Get all history records |
| POST | `/history` | Add history record |
| DELETE | `/history/<id>` | Delete specific record |
| DELETE | `/history/clear` | Clear all history |
| POST | `/analyze-history` | LLM analyzes history |
| GET | `/preferences` | Get user preferences |
| POST | `/preferences` | Save preferences |
| GET | `/translations` | Get item name translations |
| GET | `/expected` | Get expected items config |

---

## Key Implementation Details

### `ai/openrouter.py`
- Model: `meta-llama/llama-3.1-405b-instruct:free`
- `extract_json_array()`: Robust JSON extraction with bracket matching
- `call_openrouter_with_thinking()`: Handles both thinking and non-thinking models
- `analyze_history()`: Analyzes fridge history, suggests missing items
- `choose_product()`: Picks best product from search results

### `detection/detector.py`
- FridgeDetector class with YOLO model
- `detect()`: Returns both counts dict and full detection list with bounding boxes
- Detection objects include: class, name, confidence, bbox coordinates, image dimensions
- Used by frontend to draw annotations on canvas

### `db/database.py`
- SQLite database at `data/fridge.db`
- Tables: fridge_history, preferences
- `get_history_context()`: Formats history for LLM prompt
- `get_detection_threshold()`: Returns saved threshold value

### `static/app.js`
- History management (load, render, delete, save, clear)
- LLM analysis flow (analyze button, display suggestions)
- i18n with EN/TR translations
- localStorage for language persistence
- Preferences load/save (including threshold)
- **Canvas annotation system**: Draws bounding boxes with labels on detected image
- Color-coded detection boxes with confidence percentages

### `browser/getir_client.py`
- `add_product_by_index()`: Adds product at specific index with quantity support
- `add_product()`: Adds first product from search with quantity support
- `add_product_smart()`: Uses AI to select best product from search results
- **Critical quantity fix**: Uses XPath to scope plus button search to specific product's parent container, preventing wrong button clicks when adding quantity > 1 to products at index > 0
- Session persistence via `.auth/getir_session.json`

---

## Environment

### Dependencies
- Flask
- ultralytics (YOLO)
- playwright
- requests
- python-dotenv
- sqlite3 (builtin)

### Environment Variables (`.env`)
```
OPENROUTER_API_KEY=your_key_here
```

### Running the Server
```bash
cd /Users/atakan/Desktop/Projeler/SiparisAgent
source venv/bin/activate
python server.py
# Open http://localhost:5000
```

---

## Notes

- Eggs are sold in packages, so quantity is always 1 when ordering
- History analysis only suggests items that are completely missing from current fridge state
- Thinking model support exists but Llama is used for reliability
- Debug logging in terminal shows LLM prompts and responses
- Migros requires manual login first (session saved to `.auth/migros_session.json`)
- Akbal Market does not require login - cart works without authentication
- Provider preference persists across page reloads (stored in DB + localStorage)
- "Missing Items" section removed from UI - ordering now handled via AI suggestions only
- Detection threshold persists across sessions (stored in DB)

## Bug Fixes

### Quantity Addition Bug (Fixed 2025-12-22)
**Problem**: When adding quantity > 1 for products at index > 0, Playwright would click the wrong button (often a minus button from another product), causing items to be removed instead of incremented.

**Root Cause**: Code used `button[aria-label='counter'].nth(1)` globally across ALL counter buttons on the page, not scoped to the specific product.

**Solution**: Now uses XPath to find the product's parent container, then selects `.last` counter button within that scoped context (which is always the plus button after initial add).

---

*Last Updated: 2025-12-22*
