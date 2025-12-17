// DOM Elements
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const previewSection = document.getElementById('preview-section');
const previewImage = document.getElementById('preview-image');
const analyzeBtn = document.getElementById('analyze-btn');
const resultsSection = document.getElementById('results-section');
const detectedList = document.getElementById('detected-list');
const missingList = document.getElementById('missing-list');
const orderBtn = document.getElementById('order-btn');
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

// State
let currentImage = null;
let missingProducts = [];

// Threshold slider
thresholdSlider.addEventListener('input', () => {
    thresholdValue.textContent = thresholdSlider.value + '%';
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
}

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
    // Show detected items
    detectedList.innerHTML = '';
    if (data.detected.length === 0) {
        detectedList.innerHTML = '<li>No items detected</li>';
    } else {
        data.detected.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.name} × ${item.count}`;
            detectedList.appendChild(li);
        });
    }

    // Show missing items
    missingList.innerHTML = '';
    missingProducts = data.missing;

    if (data.missing.length === 0) {
        missingList.innerHTML = '<li>All items present! 🎉</li>';
        orderBtn.classList.add('hidden');
    } else {
        data.missing.forEach(item => {
            const li = document.createElement('li');
            li.textContent = `${item.name} × ${item.quantity}`;
            missingList.appendChild(li);
        });
        orderBtn.classList.remove('hidden');
    }

    resultsSection.classList.remove('hidden');
}

// Order button - show confirmation modal
orderBtn.addEventListener('click', () => {
    modalItems.innerHTML = '';
    missingProducts.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.name} × ${item.quantity}`;
        modalItems.appendChild(li);
    });
    modal.classList.remove('hidden');
});

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
