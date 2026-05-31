document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const statusArea = document.getElementById('statusArea');
    const fileNameDisplay = document.getElementById('fileNameDisplay');
    const progressContainer = document.getElementById('progressContainer');
    const successContainer = document.getElementById('successContainer');
    const errorContainer = document.getElementById('errorContainer');
    const errorMessage = document.getElementById('errorMessage');
    const statusText = document.getElementById('statusText');
    const downloadBtn = document.getElementById('downloadBtn');
    const resetBtn = document.getElementById('resetBtn');

    let pollingInterval = null;

    // Check for existing task in localStorage on load
    const activeTaskId = localStorage.getItem('pdfTaskId');
    const activeFileName = localStorage.getItem('pdfTaskFileName');

    if (activeTaskId) {
        showStatusArea(activeFileName || 'Document.pdf');
        pollStatus(activeTaskId);
    }

    // Event Listeners for Drag and Drop
    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        if (e.dataTransfer.files.length > 0) {
            handleFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    resetBtn.addEventListener('click', (e) => {
        e.preventDefault();
        resetUI();
    });

    function showStatusArea(filename) {
        uploadArea.style.display = 'none';
        statusArea.style.display = 'block';
        fileNameDisplay.textContent = filename;
        
        progressContainer.style.display = 'flex';
        successContainer.style.display = 'none';
        errorContainer.style.display = 'none';
    }

    function resetUI() {
        localStorage.removeItem('pdfTaskId');
        localStorage.removeItem('pdfTaskFileName');
        
        uploadArea.style.display = 'block';
        statusArea.style.display = 'none';
        fileInput.value = '';
        
        if (pollingInterval) clearInterval(pollingInterval);
    }

    function showError(msg) {
        progressContainer.style.display = 'none';
        successContainer.style.display = 'none';
        errorContainer.style.display = 'flex';
        errorMessage.textContent = msg;
        
        localStorage.removeItem('pdfTaskId');
        localStorage.removeItem('pdfTaskFileName');
    }

    function showSuccess(taskId) {
        progressContainer.style.display = 'none';
        errorContainer.style.display = 'none';
        successContainer.style.display = 'flex';
        
        downloadBtn.href = `/api/download/${taskId}`;
        
        // We leave the task ID in local storage so if they refresh they still see it,
        // unless you want to clear it upon success. 
        // We'll leave it so they can always re-download until they hit "Convert Another".
    }

    async function handleFile(file) {
        if (file.type !== 'application/pdf') {
            alert('Please upload a valid PDF file.');
            return;
        }

        showStatusArea(file.name);
        statusText.textContent = "Uploading...";

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Upload failed');
            }

            // Save to localStorage
            localStorage.setItem('pdfTaskId', data.task_id);
            localStorage.setItem('pdfTaskFileName', file.name);

            // Start polling
            pollStatus(data.task_id);

        } catch (err) {
            showError(err.message);
        }
    }

    function pollStatus(taskId) {
        statusText.textContent = "Processing PDF...";
        
        // Clear any existing interval
        if (pollingInterval) clearInterval(pollingInterval);

        // Poll every 3 seconds
        pollingInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/status/${taskId}`);
                const data = await res.json();

                if (res.status === 404) {
                    clearInterval(pollingInterval);
                    showError('Task not found. It may have expired on the server.');
                    return;
                }

                if (data.status === 'completed') {
                    clearInterval(pollingInterval);
                    showSuccess(taskId);
                } else if (data.status === 'failed') {
                    clearInterval(pollingInterval);
                    showError(data.error || 'Conversion failed.');
                }
            } catch (err) {
                console.error("Polling error:", err);
            }
        }, 3000);
    }
});
