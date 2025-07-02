/* Enhanced Lookup Last Type JavaScript */

document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const uploadArea = document.querySelector('.upload-area');
    const form = document.getElementById('lookupForm');
    const fileInfo = document.querySelector('.file-info');
    const submitBtn = document.querySelector('.submit-btn');
    const lookupLoading = document.getElementById('lookupLoading');
    
    let isSubmitting = false;
    
    // Initialize page
    initializePage();
    setupEventListeners();
    
    function initializePage() {
        // Reset form state
        if (fileInfo) fileInfo.classList.remove('show');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.remove('enabled');
        }
        
        // Initialize DataTable if table exists
        if (document.querySelector('.result-table')) {
            $('.result-table').DataTable({
                "pageLength": 25,
                "lengthMenu": [ [10, 25, 50, 100, -1], [10, 25, 50, 100, "ทั้งหมด"] ],
                "language": {
                    "search": "ค้นหา:",
                    "lengthMenu": "แสดง _MENU_ รายการต่อหน้า",
                    "info": "แสดง _START_ ถึง _END_ จาก _TOTAL_ รายการ",
                    "infoEmpty": "ไม่พบข้อมูล",
                    "infoFiltered": "(กรองจากทั้งหมด _MAX_ รายการ)",
                    "paginate": {
                        "first": "หน้าแรก",
                        "last": "หน้าสุดท้าย",
                        "next": "ถัดไป",
                        "previous": "ก่อนหน้า"
                    },
                    "emptyTable": "ไม่มีข้อมูลในตาราง",
                    "zeroRecords": "ไม่พบข้อมูลที่ตรงกัน"
                },
                "responsive": true,
                "order": [],
                "columnDefs": [
                    { "orderable": true, "targets": "_all" }
                ],
                "scrollX": true,
                "scrollY": "400px",
                "scrollCollapse": true
            });
        }
    }
    
    function setupEventListeners() {
        // File input change event
        if (fileInput) {
            fileInput.addEventListener('change', handleFileSelect);
        }
        
        // Upload area events
        if (uploadArea) {
            setupDragAndDrop();
            
            // Click to upload
            uploadArea.addEventListener('click', function(e) {
                if (e.target === uploadArea || 
                    e.target.classList.contains('upload-icon') || 
                    e.target.classList.contains('upload-text') || 
                    e.target.classList.contains('upload-subtext') ||
                    e.target.classList.contains('upload-content')) {
                    fileInput.click();
                }
            });
        }
        
        // Form submission
        if (form) {
            form.addEventListener('submit', handleFormSubmit);
        }
    }
    
    function handleFileSelect(e) {
        const file = e.target.files[0];
        
        if (file) {
            // Validate file type
            if (!validateFileType(file)) {
                showMessage('กรุณาเลือกไฟล์ Excel (.xlsx, .xls) เท่านั้น', 'error');
                clearFileInput();
                return;
            }
            
            // Validate file size (50MB limit)
            if (!validateFileSize(file)) {
                showMessage('ขนาดไฟล์ใหญ่เกินไป (สูงสุด 50MB)', 'error');
                clearFileInput();
                return;
            }
            
            // Display file information
            displayFileInfo(file);
            enableSubmitButton();
            showMessage(`เลือกไฟล์สำเร็จ: ${file.name}`, 'success');
            
        } else {
            hideFileInfo();
            disableSubmitButton();
        }
    }
    
    function validateFileType(file) {
        const allowedTypes = [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', // .xlsx
            'application/vnd.ms-excel' // .xls
        ];
        const allowedExtensions = ['.xlsx', '.xls'];
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        
        return allowedTypes.includes(file.type) || allowedExtensions.includes(fileExtension);
    }
    
    function validateFileSize(file) {
        const maxSize = 50 * 1024 * 1024; // 50MB in bytes
        return file.size <= maxSize;
    }
    
    function displayFileInfo(file) {
        if (!fileInfo) return;
        
        const fileSize = formatFileSize(file.size);
        
        fileInfo.innerHTML = `
            <div class="selected-file">
                <div class="file-icon">
                    <i class="fas fa-file-excel"></i>
                </div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${fileSize}</div>
                </div>
                <div class="file-status">
                    <i class="fas fa-check-circle"></i>
                    พร้อมอัปโหลด
                </div>
            </div>
        `;
        
        fileInfo.classList.add('show');
        uploadArea.classList.add('file-selected');
    }
    
    function hideFileInfo() {
        if (fileInfo) {
            fileInfo.classList.remove('show');
            uploadArea.classList.remove('file-selected');
        }
    }
    
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    function enableSubmitButton() {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.classList.add('enabled');
        }
    }
    
    function disableSubmitButton() {
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.classList.remove('enabled');
        }
    }
    
    function handleFormSubmit(e) {
        if (isSubmitting) {
            e.preventDefault();
            return false;
        }
        
        const file = fileInput.files[0];
        if (!file) {
            e.preventDefault();
            showMessage('กรุณาเลือกไฟล์ก่อน', 'error');
            return false;
        }
        
        // Start loading state
        isSubmitting = true;
        submitBtn.classList.add('loading');
        
        if (lookupLoading) {
            lookupLoading.style.display = 'block';
            lookupLoading.classList.add('show');
        }
        
        // Let form submit naturally
        return true;
    }
    
    function setupDragAndDrop() {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
            document.body.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        // Highlight drop area when item is dragged over it
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, highlight, false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, unhighlight, false);
        });
        
        // Handle dropped files
        uploadArea.addEventListener('drop', handleDrop, false);
        
        function highlight(e) {
            uploadArea.classList.add('dragover');
        }
        
        function unhighlight(e) {
            uploadArea.classList.remove('dragover');
        }
        
        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            
            if (files.length > 0) {
                fileInput.files = files;
                const event = new Event('change', { bubbles: true });
                fileInput.dispatchEvent(event);
            }
        }
    }
    
    function showMessage(message, type = 'info') {
        // Use global showAlert if available
        if (window.showAlert) {
            window.showAlert(message, type);
            return;
        }
        
        // Fallback implementation
        const messageDiv = document.createElement('div');
        messageDiv.className = `alert-message ${type}-message`;
        
        let icon = 'fas fa-info-circle';
        switch(type) {
            case 'success': icon = 'fas fa-check-circle'; break;
            case 'error': icon = 'fas fa-times-circle'; break;
            case 'warning': icon = 'fas fa-exclamation-triangle'; break;
        }
        
        messageDiv.innerHTML = `<i class="${icon}"></i> ${message}`;
        
        // Insert at top of main container
        const mainContainer = document.querySelector('.main-container');
        if (mainContainer) {
            mainContainer.insertBefore(messageDiv, mainContainer.firstChild);
        }
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            messageDiv.style.opacity = '0';
            setTimeout(() => messageDiv.remove(), 300);
        }, 5000);
    }
    
    function clearFileInput() {
        if (fileInput) {
            fileInput.value = '';
            hideFileInfo();
            disableSubmitButton();
        }
    }
    
    // Error handling
    window.addEventListener('error', function(e) {
        isSubmitting = false;
        if (submitBtn) submitBtn.classList.remove('loading');
        if (lookupLoading) {
            lookupLoading.style.display = 'none';
            lookupLoading.classList.remove('show');
        }
        showMessage('เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง', 'error');
    });
    
    // Handle back button
    window.addEventListener('beforeunload', function() {
        isSubmitting = false;
        if (submitBtn) submitBtn.classList.remove('loading');
        if (lookupLoading) {
            lookupLoading.style.display = 'none';
            lookupLoading.classList.remove('show');
        }
    });
});

// Global utility functions for lookup page
function downloadResult(url) {
    window.location.href = url;
}

function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showMessage('คัดลอกข้อมูลแล้ว', 'success');
    }).catch(() => {
        showMessage('ไม่สามารถคัดลอกข้อมูลได้', 'error');
    });
}

// Export functions for external use
window.LookupLastType = {
    showMessage: function(message, type) {
        showMessage(message, type);
    },
    downloadResult: downloadResult,
    copyToClipboard: copyToClipboard
};