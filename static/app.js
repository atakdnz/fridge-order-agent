// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const previewSection = document.getElementById('preview-section');
const previewImage = document.getElementById('preview-image');
const analyzeBtn = document.getElementById('analyze-btn');
const resultsSection = document.getElementById('results-section');
const detectedList = document.getElementById('detected-list');
const status = document.getElementById('status');
const modal = document.getElementById('modal');
const modalItems = document.getElementById('modal-items');
const modalCancel = document.getElementById('modal-cancel');
const modalConfirm = document.getElementById('modal-confirm');
const thresholdSlider = document.getElementById('threshold');
const thresholdValue = document.getElementById('threshold-value');
const useAiCheckbox = document.getElementById('use-ai');
const preferenceSelect = document.getElementById('preference');
const customInstructionsWrapper = document.getElementById('custom-instructions-wrapper');
const customInstructions = document.getElementById('custom-instructions');
const historyDateInput = document.getElementById('history-date');
const saveHistoryBtn = document.getElementById('save-history-btn');
const historyList = document.getElementById('history-list');
const clearHistoryBtn = document.getElementById('clear-history-btn');
const analyzeHistoryBtn = document.getElementById('analyze-history-btn');
const aiSuggestionsSection = document.getElementById('ai-suggestions');
const suggestionsList = document.getElementById('suggestions-list');
const orderSuggestionsBtn = document.getElementById('order-suggestions-btn');
const aiThinkingContent = document.getElementById('ai-thinking-content');
const aiThinkingDetails = document.getElementById('ai-thinking-details');
const providerRadios = document.querySelectorAll('input[name="provider"]');
const modalConfirmText = document.getElementById('modal-confirm-text');
const annotationCanvas = document.getElementById('annotation-canvas');
const showMasksCheckbox = document.getElementById('show-masks');

// State
let currentImage = null;
let missingProducts = [];
let lastDetectedItems = {};  // Raw detection results for saving to history
let lastDetections = [];     // Full detection info with bboxes for canvas
let aiSuggestedItems = [];   // AI suggested items to order
let itemTranslations = {};  // Class name -> Turkish translations
let currentProvider = 'getir';  // Current ordering provider

// Color palette for different classes
const classColors = {
    milk: '#3498db',
    eggs: '#f39c12',
    cheese: '#f1c40f',
    yogurt: '#9b59b6',
    butter: '#e67e22',
    water_bottle: '#1abc9c',
    soda: '#e74c3c',
    juice: '#2ecc71',
    tomato: '#c0392b',
    cucumber: '#27ae60',
    pepper: '#d35400',
    apple: '#e74c3c',
    orange: '#f39c12',
    lemon: '#f1c40f',
    salami: '#8e44ad',
    sausage: '#e74c3c',
    chicken: '#f5cba7',
    fish: '#5dade2',
    cake: '#ff69b4',
    chocolate: '#8b4513',
    lettuce: '#2ecc71',
    carrot: '#e67e22',
    banana: '#f4d03f'
};

// Get color for a class (with fallback)
function getClassColor(className) {
    return classColors[className] || '#5865f2';
}

// Set default date to today
historyDateInput.valueAsDate = new Date();

// Load item translations from server
async function loadTranslations() {
    try {
        const response = await fetch('/translations');
        const data = await response.json();
        if (data.success) {
            itemTranslations = data.translations;
        }
    } catch (error) {
        console.error('Failed to load translations:', error);
    }
}

// Load preferences from server
async function loadPreferences() {
    try {
        const response = await fetch('/preferences');
        const data = await response.json();
        if (data.success && data.preferences) {
            customInstructions.value = data.preferences.custom_instructions || '';
            // Load provider preference
            currentProvider = data.preferences.preferred_provider || 'getir';
            setProviderRadio(currentProvider);
            // Load threshold preference
            if (data.preferences.detection_threshold !== undefined) {
                const thresholdPercent = Math.round(data.preferences.detection_threshold * 100);
                thresholdSlider.value = thresholdPercent;
                thresholdValue.textContent = thresholdPercent + '%';
            }
        }
    } catch (error) {
        console.error('Failed to load preferences:', error);
    }
}

// Set the provider radio button
function setProviderRadio(provider) {
    providerRadios.forEach(radio => {
        radio.checked = (radio.value === provider);
    });
}

// Get the selected provider
function getSelectedProvider() {
    for (const radio of providerRadios) {
        if (radio.checked) return radio.value;
    }
    return 'getir';
}

// Save provider preference
async function saveProviderPreference(provider) {
    try {
        await fetch('/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preferred_provider: provider })
        });
        localStorage.setItem('siparisagent_provider', provider);
    } catch (error) {
        console.error('Failed to save provider preference:', error);
    }
}

// Provider selection change handler
providerRadios.forEach(radio => {
    radio.addEventListener('change', () => {
        currentProvider = radio.value;
        saveProviderPreference(currentProvider);
    });
});

// Save preferences when custom instructions changes
customInstructions.addEventListener('blur', async () => {
    try {
        await fetch('/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ custom_instructions: customInstructions.value })
        });
    } catch (error) {
        console.error('Failed to save preferences:', error);
    }
});

// Threshold slider - update display and save to database
thresholdSlider.addEventListener('input', () => {
    thresholdValue.textContent = thresholdSlider.value + '%';
});

// Save threshold when slider change is complete (mouseup/touchend)
thresholdSlider.addEventListener('change', async () => {
    const threshold = thresholdSlider.value / 100;
    try {
        await fetch('/preferences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ detection_threshold: threshold })
        });
    } catch (error) {
        console.error('Failed to save threshold:', error);
    }
});

// Upload Zone Events
uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('dragover');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('dragover');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleImage(file);
    }
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleImage(file);
});

// Paste support
document.addEventListener('paste', (e) => {
    const items = e.clipboardData.items;
    for (let item of items) {
        if (item.type.startsWith('image/')) {
            const file = item.getAsFile();
            handleImage(file);
            break;
        }
    }
});

// Handle uploaded image
function handleImage(file) {
    currentImage = file;
    const url = URL.createObjectURL(file);
    previewImage.src = url;
    previewSection.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    status.classList.add('hidden');
    // Clear previous annotations
    lastDetections = [];
    clearCanvas();
}

// Clear the annotation canvas
function clearCanvas() {
    const ctx = annotationCanvas.getContext('2d');
    ctx.clearRect(0, 0, annotationCanvas.width, annotationCanvas.height);
}

// Draw annotations on canvas
function drawAnnotations() {
    if (!lastDetections.length || !showMasksCheckbox.checked) {
        clearCanvas();
        return;
    }

    // Wait for image to load and get its displayed dimensions
    const imgRect = previewImage.getBoundingClientRect();
    const displayWidth = previewImage.clientWidth;
    const displayHeight = previewImage.clientHeight;

    // Set canvas size to match displayed image
    annotationCanvas.width = displayWidth;
    annotationCanvas.height = displayHeight;

    const ctx = annotationCanvas.getContext('2d');
    ctx.clearRect(0, 0, displayWidth, displayHeight);

    // Get original image dimensions from first detection
    if (!lastDetections[0]) return;
    const origWidth = lastDetections[0].image_width;
    const origHeight = lastDetections[0].image_height;

    // Calculate scale factors
    const scaleX = displayWidth / origWidth;
    const scaleY = displayHeight / origHeight;

    // Draw each detection
    lastDetections.forEach(det => {
        const color = getClassColor(det.class);
        const bbox = det.bbox;

        // Scale coordinates
        const x1 = bbox.x1 * scaleX;
        const y1 = bbox.y1 * scaleY;
        const x2 = bbox.x2 * scaleX;
        const y2 = bbox.y2 * scaleY;
        const width = x2 - x1;
        const height = y2 - y1;

        // Draw bounding box
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x1, y1, width, height);

        // Draw semi-transparent fill
        ctx.fillStyle = color + '20';  // 20 = ~12% opacity
        ctx.fillRect(x1, y1, width, height);

        // Draw label background
        const label = `${det.name} ${Math.round(det.confidence * 100)}%`;
        ctx.font = 'bold 12px -apple-system, sans-serif';
        const textMetrics = ctx.measureText(label);
        const textWidth = textMetrics.width + 8;
        const textHeight = 18;

        ctx.fillStyle = color;
        ctx.fillRect(x1, y1 - textHeight, textWidth, textHeight);

        // Draw label text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(label, x1 + 4, y1 - 5);
    });
}

// Toggle annotations on checkbox change
showMasksCheckbox.addEventListener('change', drawAnnotations);

// Redraw when image loads (for proper sizing)
previewImage.addEventListener('load', () => {
    if (lastDetections.length > 0) {
        drawAnnotations();
    }
});

// Redraw on window resize
window.addEventListener('resize', () => {
    if (lastDetections.length > 0) {
        drawAnnotations();
    }
});

// Analyze button
analyzeBtn.addEventListener('click', async () => {
    if (!currentImage) return;

    showStatus('🔍 Analyzing fridge...', 'loading');

    const formData = new FormData();
    formData.append('image', currentImage);
    formData.append('confidence', thresholdSlider.value / 100);

    try {
        const response = await fetch('/detect', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            displayResults(data);
            showStatus('✅ Analysis complete!', 'success');
        } else {
            showStatus('❌ ' + (data.error || 'Analysis failed'), 'error');
        }
    } catch (error) {
        showStatus('❌ Error: ' + error.message, 'error');
    }
});

// Display results
function displayResults(data) {
    // Save raw detected items for history
    lastDetectedItems = {};
    data.detected.forEach(item => {
        lastDetectedItems[item.class || item.name] = item.count;
    });

    // Save full detections for canvas drawing
    lastDetections = data.detections || [];

    // Show detected items
    detectedList.innerHTML = '';
    if (data.detected.length === 0) {
        detectedList.innerHTML = '<li>No items detected</li>';
    } else {
        data.detected.forEach(item => {
            const li = document.createElement('li');
            const colorDot = `<span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${getClassColor(item.class)};margin-right:6px;"></span>`;
            li.innerHTML = `${colorDot}${item.name} × ${item.count}`;
            detectedList.appendChild(li);
        });
    }

    // Set missing products for ordering (handled by AI now)
    missingProducts = data.missing || [];

    resultsSection.classList.remove('hidden');

    // Draw bounding boxes on canvas
    drawAnnotations();
}

// Update modal confirmation text based on provider
function updateModalText() {
    const provider = getSelectedProvider();
    const providerNames = {
        'getir': 'Getir',
        'migros': 'Migros',
        'akbal': 'Akbal Market'
    };
    const providerName = providerNames[provider] || 'Getir';
    if (currentLang === 'tr') {
        modalConfirmText.textContent = `Aşağıdaki ürünler ${providerName}'den sipariş edilsin mi?`;
    } else {
        modalConfirmText.textContent = `Order the following items on ${providerName}?`;
    }
}

// Modal cancel
modalCancel.addEventListener('click', () => {
    modal.classList.add('hidden');
});

// Modal confirm - place order
modalConfirm.addEventListener('click', async () => {
    modal.classList.add('hidden');
    showStatus('🛒 Starting order...', 'loading');

    try {
        // Build preference string - combine mode with custom instructions
        let pref = preferenceSelect.value;
        const customText = customInstructions.value.trim();
        if (customText) {
            pref = pref + '. Additional: ' + customText;
        }

        const response = await fetch('/order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                products: missingProducts,
                use_ai: useAiCheckbox.checked,
                preference: pref
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('🌐 Browser opened! Complete checkout there.', 'success');
        } else {
            showStatus('❌ ' + (data.error || 'Order failed'), 'error');
        }
    } catch (error) {
        showStatus('❌ Error: ' + error.message, 'error');
    }
});

// Status helper
function showStatus(message, type) {
    status.textContent = message;
    status.className = 'status ' + type;
    status.classList.remove('hidden');
}

// ============ History Functions ============

// Keep track of current language
let currentLang = 'en';

async function loadHistory() {
    try {
        const response = await fetch('/history');
        const data = await response.json();

        if (data.success && data.history) {
            renderHistory(data.history);
        }
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

function renderHistory(history) {
    if (history.length === 0) {
        const emptyMsg = currentLang === 'tr'
            ? 'Henüz geçmiş yok. Bir resim yükleyin ve geçmişe kaydedin.'
            : 'No history yet. Upload an image and save to history.';
        historyList.innerHTML = `<p class="history-empty">${emptyMsg}</p>`;
        return;
    }

    historyList.innerHTML = history.map(record => {
        const noItemsMsg = currentLang === 'tr' ? 'Ürün yok' : 'No items';
        const itemsStr = Object.entries(record.items)
            .map(([k, v]) => {
                // Use Turkish translation if available and in TR mode
                const name = (currentLang === 'tr' && itemTranslations[k]) ? itemTranslations[k] : k;
                return `${name} ×${v}`;
            })
            .join(', ');

        return `
            <div class="history-card" data-id="${record.id}">
                <div class="history-card-info">
                    <div class="history-card-date">📅 ${record.date}</div>
                    <div class="history-card-items">${itemsStr || noItemsMsg}</div>
                </div>
                <button class="history-card-delete" onclick="deleteHistory(${record.id})">🗑️</button>
            </div>
        `;
    }).join('');
}

async function deleteHistory(id) {
    try {
        const response = await fetch(`/history/${id}`, { method: 'DELETE' });
        if (response.ok) {
            loadHistory();  // Refresh list
        }
    } catch (error) {
        console.error('Failed to delete:', error);
    }
}

// Save to history button
saveHistoryBtn.addEventListener('click', async () => {
    if (Object.keys(lastDetectedItems).length === 0) {
        showStatus('❌ No detection to save. Analyze an image first.', 'error');
        return;
    }

    const date = historyDateInput.value;
    if (!date) {
        showStatus('❌ Please select a date.', 'error');
        return;
    }

    try {
        const response = await fetch('/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date, items: lastDetectedItems })
        });

        if (response.ok) {
            showStatus('✅ Saved to history!', 'success');
            loadHistory();  // Refresh list
        }
    } catch (error) {
        showStatus('❌ Failed to save: ' + error.message, 'error');
    }
});

// Clear all history
clearHistoryBtn.addEventListener('click', async () => {
    if (!confirm('Delete all history records?')) return;

    try {
        await fetch('/history/clear', { method: 'DELETE' });
        loadHistory();
        aiSuggestionsSection.classList.add('hidden');
        showStatus('🗑️ History cleared', 'success');
    } catch (error) {
        console.error('Failed to clear:', error);
    }
});

// Analyze History with AI
analyzeHistoryBtn.addEventListener('click', async () => {
    showStatus('🧠 Analyzing history with AI...', 'loading');

    try {
        const response = await fetch('/analyze-history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const data = await response.json();

        if (data.success && data.suggestions) {
            aiSuggestedItems = data.suggestions;
            displaySuggestions(data.suggestions, data.thinking);
            showStatus('✅ AI analysis complete!', 'success');
        } else {
            // Show thinking even if no suggestions (only if available)
            if (data.thinking && data.thinking.trim()) {
                aiThinkingContent.textContent = data.thinking;
                aiThinkingDetails.style.display = 'block';
                aiThinkingDetails.open = true;
            } else {
                aiThinkingDetails.style.display = 'none';
            }
            showStatus('❌ ' + (data.error || 'Analysis failed'), 'error');
        }
    } catch (error) {
        showStatus('❌ Error: ' + error.message, 'error');
    }
});

// Display AI suggestions
function displaySuggestions(suggestions, thinking = '') {
    suggestionsList.innerHTML = '';

    // Display thinking process (hide if empty)
    if (thinking && thinking.trim()) {
        aiThinkingContent.textContent = thinking;
        aiThinkingDetails.open = false;  // Collapsed by default
        aiThinkingDetails.style.display = 'block';
    } else {
        aiThinkingDetails.style.display = 'none';
    }

    if (suggestions.length === 0) {
        suggestionsList.innerHTML = '<li>No items to order</li>';
        aiSuggestionsSection.classList.add('hidden');
        return;
    }

    suggestions.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.name} × ${item.quantity}`;
        suggestionsList.appendChild(li);
    });

    aiSuggestionsSection.classList.remove('hidden');
}

// Order AI suggestions
orderSuggestionsBtn.addEventListener('click', () => {
    if (aiSuggestedItems.length === 0) {
        showStatus('❌ No items to order', 'error');
        return;
    }

    // Set missingProducts to AI suggestions and show modal
    missingProducts = aiSuggestedItems;
    modalItems.innerHTML = '';
    aiSuggestedItems.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.name} × ${item.quantity}`;
        modalItems.appendChild(li);
    });
    updateModalText();
    modal.classList.remove('hidden');
});

// ============ Internationalization (i18n) ============

const translations = {
    en: {
        subtitle: "Fridge Detection & Auto-Order Test",
        drop_image: "Drop fridge image here",
        click_select: "or click to select • paste from clipboard",
        confidence: "Detection Confidence:",
        ai_selection: "🤖 AI Product Selection",
        pref_smart: "🧠 Smart (AI decides)",
        pref_cheapest: "Cheapest",
        pref_unit: "Cheapest per unit",
        pref_organic: "Organic/Natural",
        pref_brand: "Popular brand",
        custom_label: "📝 Additional Instructions (optional):",
        provider_label: "🏪 Order From:",
        analyze_btn: "🔍 Analyze Fridge",
        detected_title: "✅ Detected Items",
        missing_title: "❌ Missing Items",
        history_date_label: "📅 Date for history:",
        save_history: "💾 Save to History",
        order_btn: "🛒 Order Missing Items",
        history_title: "📊 Fridge History",
        loading_history: "Loading history...",
        clear_history: "🗑️ Clear All History",
        confirm_order: "🛒 Confirm Order",
        confirm_text: "Order the following items on Getir?",
        confirm_text_migros: "Order the following items on Migros?",
        cancel: "Cancel",
        order_now: "Order Now",
        analyze_history: "🧠 Analyze History with AI",
        ai_suggestions_title: "🤖 AI Suggestions",
        order_suggestions: "🛒 Order These Items",
        // Status messages
        status_analyzing: "🔍 Analyzing fridge...",
        status_analysis_complete: "✅ Analysis complete!",
        status_ai_analyzing: "🧠 Analyzing history with AI...",
        status_ai_complete: "✅ AI analysis complete!",
        status_saved: "✅ Saved to history!",
        status_cleared: "🗑️ History cleared",
        status_ordering: "🛒 Starting order...",
        status_browser_opened: "🌐 Browser opened! Complete checkout there.",
        status_no_detection: "❌ No detection to save. Analyze an image first.",
        status_select_date: "❌ Please select a date.",
        status_no_items: "❌ No items to order",
        no_items_to_order: "No items to order",
        ai_thinking_title: "🧠 AI Thinking Process",
        show_masks: "📦 Show Boxes & Labels"
    },
    tr: {
        subtitle: "Buzdolabı Algılama ve Otomatik Sipariş",
        drop_image: "Buzdolabı fotoğrafını buraya bırakın",
        click_select: "veya seçmek için tıklayın • panodan yapıştırın",
        confidence: "Algılama Güveni:",
        ai_selection: "🤖 Yapay Zeka Ürün Seçimi",
        pref_smart: "🧠 Akıllı (YZ karar verir)",
        pref_cheapest: "En ucuz",
        pref_unit: "Birim fiyatı en ucuz",
        pref_organic: "Organik/Doğal",
        pref_brand: "Popüler marka",
        custom_label: "📝 Ek Talimatlar (isteğe bağlı):",
        custom_placeholder: "örn: Pınar veya Sütaş marka tercih ederim, katkı maddeli ürünlerden kaçın, büyük boy seç...",
        provider_label: "🏪 Sipariş Ver:",
        analyze_btn: "🔍 Buzdolabını Analiz Et",
        detected_title: "✅ Algılanan Ürünler",
        missing_title: "❌ Eksik Ürünler",
        history_date_label: "📅 Geçmiş tarihi:",
        save_history: "💾 Geçmişe Kaydet",
        order_btn: "🛒 Eksikleri Sipariş Ver",
        history_title: "📊 Buzdolabı Geçmişi",
        loading_history: "Geçmiş yükleniyor...",
        clear_history: "🗑️ Tüm Geçmişi Temizle",
        confirm_order: "🛒 Siparişi Onayla",
        confirm_text: "Aşağıdaki ürünler Getir'den sipariş edilsin mi?",
        confirm_text_migros: "Aşağıdaki ürünler Migros'tan sipariş edilsin mi?",
        cancel: "İptal",
        order_now: "Sipariş Ver",
        analyze_history: "🧠 Geçmişi YZ ile Analiz Et",
        ai_suggestions_title: "🤖 YZ Önerileri",
        order_suggestions: "🛒 Bunları Sipariş Et",
        // Status messages
        status_analyzing: "🔍 Buzdolabı analiz ediliyor...",
        status_analysis_complete: "✅ Analiz tamamlandı!",
        status_ai_analyzing: "🧠 Geçmiş YZ ile analiz ediliyor...",
        status_ai_complete: "✅ YZ analizi tamamlandı!",
        status_saved: "✅ Geçmişe kaydedildi!",
        status_cleared: "🗑️ Geçmiş temizlendi",
        status_ordering: "🛒 Sipariş başlatılıyor...",
        status_browser_opened: "🌐 Tarayıcı açıldı! Ödemeyi orada tamamlayın.",
        status_no_detection: "❌ Kaydedilecek algılama yok. Önce bir resim analiz edin.",
        status_select_date: "❌ Lütfen bir tarih seçin.",
        status_no_items: "❌ Sipariş edilecek ürün yok",
        no_items_to_order: "Sipariş edilecek ürün yok",
        ai_thinking_title: "🧠 YZ Düşünme Süreci",
        show_masks: "📦 Kutuları ve Etiketleri Göster"
    }
};

// Helper to get translated string
function t(key) {
    return translations[currentLang][key] || translations['en'][key] || key;
}

function updateLanguage(lang) {
    currentLang = lang;

    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (translations[lang][key]) {
            if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                element.placeholder = translations[lang][key];
            } else {
                element.textContent = translations[lang][key];
            }
        }
    });

    // Handle separate placeholder keys if needed (like for textarea)
    const customArea = document.getElementById('custom-instructions');
    if (translations[lang].custom_placeholder) {
        customArea.placeholder = translations[lang].custom_placeholder;
    }

    // Update buttons state
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
    });

    // Refresh history to show correct empty message if needed
    loadHistory();

    // Save language preference to localStorage
    localStorage.setItem('siparisagent_lang', lang);
}

// Language switch buttons
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const lang = btn.getAttribute('data-lang');
        updateLanguage(lang);
    });
});

// Initialize on page load
loadTranslations();
loadPreferences();
loadHistory();

// Load saved language preference
const savedLang = localStorage.getItem('siparisagent_lang');
if (savedLang && (savedLang === 'en' || savedLang === 'tr')) {
    updateLanguage(savedLang);
}

