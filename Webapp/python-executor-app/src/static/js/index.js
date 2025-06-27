/**
 * Index Page JavaScript - Simplified Version
 * Compatible with current HTML structure
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Index page loaded');
    
    // Get DOM elements
    const elements = {
        fileInput: document.getElementById('fileInput'),
        funcSelect: document.getElementById('funcSelect'),
        mainForm: document.getElementById('mainForm'),
        lookupLastTypeLink: document.getElementById('lookupLastTypeLink'),
        loading: document.getElementById('loading'),
        showTableCheckbox: document.getElementById('showTable')
    };

    // Check if required elements exist
    if (!elements.fileInput || !elements.funcSelect || !elements.mainForm) {
        console.error('Required DOM elements not found');
        return;
    }

    // Configuration
    const config = {
        functionsRequiringLookup: ['PNP_CHANG_TYPE'],
        maxFileSize: 50 * 1024 * 1024, // 50MB
        allowedFileTypes: ['.xlsx', '.xls', '.csv', '.txt']
    };

    // Initialize
    init();

    function init() {
        setupEventListeners();
        restoreFormState();
        console.log('Index page initialized');
    }

    function setupEventListeners() {
        // Form submission
        elements.mainForm.addEventListener('submit', handleFormSubmit);

        // Function selection
        elements.funcSelect.addEventListener('change', handleFunctionChange);

        // File input changes
        elements.fileInput.addEventListener('change', handleFileChange);

        // Setup drag and drop
        setupDragAndDrop();

        // Form state changes
        if (elements.showTableCheckbox) {
            elements.showTableCheckbox.addEventListener('change', saveFormState);
        }
    }

    function handleFormSubmit(e) {
        console.log('Form submitted');
        
        // Basic validation
        if (!elements.funcSelect.value) {
            e.preventDefault();
            showMessage('กรุณาเลือกฟังก์ชันก่อน', 'error');
            return;
        }

        if (!elements.fileInput.files.length) {
            e.preventDefault();
            showMessage('กรุณาเลือกไฟล์ก่อน', 'error');
            return;
        }

        // Validate files
        const validation = validateFiles(elements.fileInput.files);
        if (!validation.isValid) {
            e.preventDefault();
            showMessage(validation.message, 'error');
            return;
        }

        // Show loading
        showLoading();
        saveFormState();
    }

    function handleFunctionChange() {
        const selectedFunction = elements.funcSelect.value;
        console.log('Function selected:', selectedFunction);

        // Toggle lookup link visibility
        toggleLookupLink(selectedFunction);
        saveFormState();

        if (selectedFunction) {
            showMessage(`เลือกฟังก์ชัน: ${selectedFunction}`, 'info');
        }
    }

    function toggleLookupLink(functionName) {
        if (!elements.lookupLastTypeLink) return;

        const shouldShow = config.functionsRequiringLookup.includes(functionName);
        
        if (shouldShow) {
            elements.lookupLastTypeLink.style.display = "inline-block";
        } else {
            elements.lookupLastTypeLink.style.display = "none";
        }
    }

    function handleFileChange() {
        const files = Array.from(elements.fileInput.files);
        console.log('Files selected:', files.length);

        if (files.length > 0) {
            // Basic validation
            const validation = validateFiles(files);
            
            if (validation.isValid) {
                updateFileDisplay(files);
                showMessage(`เลือกไฟล์สำเร็จ: ${files.length} ไฟล์`, 'success');
                
                // Visual feedback
                elements.fileInput.style.borderColor = '#28a745';
                elements.fileInput.style.background = '#f8fff8';
            } else {
                showMessage(validation.message, 'error');
                elements.fileInput.style.borderColor = '#dc3545';
            }
        } else {
            clearFileDisplay();
            elements.fileInput.style.borderColor = '';
            elements.fileInput.style.background = '';
        }

        saveFormState();
    }

    function validateFiles(files) {
        const { maxFileSize, allowedFileTypes } = config;

        for (let file of files) {
            // Check file size
            if (file.size > maxFileSize) {
                return {
                    isValid: false,
                    message: `ไฟล์ "${file.name}" มีขนาดใหญ่เกินไป (สูงสุด ${formatFileSize(maxFileSize)})`
                };
            }

            // Check file type
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            if (!allowedFileTypes.includes(fileExtension)) {
                return {
                    isValid: false,
                    message: `ไฟล์ "${file.name}" ไม่ใช่ประเภทที่รองรับ (${allowedFileTypes.join(', ')})`
                };
            }

            // Check for empty files
            if (file.size === 0) {
                return {
                    isValid: false,
                    message: `ไฟล์ "${file.name}" เป็นไฟล์ว่าง`
                };
            }
        }

        return { isValid: true };
    }

    function updateFileDisplay(files) {
        let fileDisplayArea = document.getElementById('fileDisplayArea');
        
        // Create display area if it doesn't exist
        if (!fileDisplayArea) {
            fileDisplayArea = createFileDisplayArea();
        }

        if (files.length > 0) {
            fileDisplayArea.innerHTML = generateFileListHTML(files);
            fileDisplayArea.style.display = 'block';
        } else {
            fileDisplayArea.style.display = 'none';
        }
    }

    function createFileDisplayArea() {
        const fileDisplayArea = document.createElement('div');
        fileDisplayArea.id = 'fileDisplayArea';
        fileDisplayArea.className = 'file-display-area';
        fileDisplayArea.style.cssText = `
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        `;
        elements.fileInput.parentNode.appendChild(fileDisplayArea);
        return fileDisplayArea;
    }

    function generateFileListHTML(files) {
        let html = '<div style="font-weight: 600; margin-bottom: 10px; color: #495057;"><i class="fas fa-file-check"></i> ไฟล์ที่เลือก:</div>';
        
        files.forEach((file, index) => {
            const fileSize = formatFileSize(file.size);
            const fileIcon = getFileIcon(file.name);
            
            html += `
                <div style="display: flex; align-items: center; padding: 8px 0; border-bottom: 1px solid #dee2e6;">
                    <i class="${fileIcon}" style="margin-right: 10px; color: #28a745;"></i>
                    <div style="flex: 1;">
                        <div style="font-weight: 500;">${file.name}</div>
                        <div style="font-size: 0.9em; color: #6c757d;">${fileSize}</div>
                    </div>
                    <button type="button" onclick="removeFile(${index})" style="
                        background: #dc3545; 
                        color: white; 
                        border: none; 
                        border-radius: 50%; 
                        width: 24px; 
                        height: 24px; 
                        cursor: pointer;
                        font-size: 12px;
                    ">×</button>
                </div>
            `;
        });
        
        return html;
    }

    function clearFileDisplay() {
        const fileDisplayArea = document.getElementById('fileDisplayArea');
        if (fileDisplayArea) {
            fileDisplayArea.style.display = 'none';
        }
    }

    function setupDragAndDrop() {
        const { fileInput } = elements;
        
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            fileInput.addEventListener(eventName, preventDefaults, false);
        });

        // Highlight drop area
        ['dragenter', 'dragover'].forEach(eventName => {
            fileInput.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            fileInput.addEventListener(eventName, unhighlight, false);
        });

        // Handle file drop
        fileInput.addEventListener('drop', handleDrop, false);

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        function highlight(e) {
            fileInput.style.borderColor = '#667eea';
            fileInput.style.background = '#f0f4ff';
        }

        function unhighlight(e) {
            fileInput.style.borderColor = '';
            fileInput.style.background = '';
        }

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                handleFileChange();
            }
        }
    }

    function showLoading() {
        if (elements.loading) {
            elements.loading.style.display = 'block';
        }
        
        // Disable form
        const formContainer = document.querySelector('.form-container');
        if (formContainer) {
            formContainer.style.opacity = '0.5';
            formContainer.style.pointerEvents = 'none';
        }
    }

    function saveFormState() {
        const state = {
            selectedFunction: elements.funcSelect.value,
            showTable: elements.showTableCheckbox?.checked,
            timestamp: Date.now()
        };
        
        try {
            localStorage.setItem('indexFormState', JSON.stringify(state));
        } catch (error) {
            console.warn('Failed to save form state:', error);
        }
    }

    function restoreFormState() {
        try {
            const savedState = localStorage.getItem('indexFormState');
            if (!savedState) return;

            const state = JSON.parse(savedState);
            
            // Check if state is not too old (24 hours)
            if (Date.now() - state.timestamp > 24 * 60 * 60 * 1000) {
                localStorage.removeItem('indexFormState');
                return;
            }

            // Restore function selection
            if (state.selectedFunction && elements.funcSelect) {
                elements.funcSelect.value = state.selectedFunction;
                handleFunctionChange();
            }

            // Restore show table checkbox
            if (typeof state.showTable === 'boolean' && elements.showTableCheckbox) {
                elements.showTableCheckbox.checked = state.showTable;
            }

        } catch (error) {
            console.warn('Failed to restore form state:', error);
            localStorage.removeItem('indexFormState');
        }
    }

    // Utility functions
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const iconMap = {
            'xlsx': 'fas fa-file-excel',
            'xls': 'fas fa-file-excel',
            'csv': 'fas fa-file-csv',
            'txt': 'fas fa-file-alt'
        };
        return iconMap[ext] || 'fas fa-file';
    }

    function showMessage(message, type = 'info') {
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // Create simple alert message
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            padding: 15px 20px;
            border-radius: 8px;
            color: white;
            font-weight: 500;
            max-width: 400px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        `;
        
        // Set background color based on type
        const colors = {
            'info': '#17a2b8',
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107'
        };
        alertDiv.style.background = colors[type] || colors['info'];
        
        alertDiv.innerHTML = `<i class="fas fa-info-circle" style="margin-right: 8px;"></i>${message}`;
        
        document.body.appendChild(alertDiv);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            alertDiv.style.opacity = '0';
            setTimeout(() => alertDiv.remove(), 300);
        }, 4000);
    }

    // Global functions for HTML onclick events
    window.removeFile = function(index) {
        const dt = new DataTransfer();
        const files = Array.from(elements.fileInput.files);
        
        files.forEach((file, i) => {
            if (i !== index) {
                dt.items.add(file);
            }
        });
        
        elements.fileInput.files = dt.files;
        handleFileChange();
        showMessage('ลบไฟล์แล้ว', 'info');
    };

    // Expose functions for external access
    window.indexPageAPI = {
        showMessage: showMessage,
        validateFiles: validateFiles,
        getSelectedFiles: () => Array.from(elements.fileInput.files),
        getCurrentFunction: () => elements.funcSelect.value
    };
});