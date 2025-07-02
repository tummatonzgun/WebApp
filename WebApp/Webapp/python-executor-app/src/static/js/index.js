/**
 * Index Page JavaScript - Simplified Version
 * Compatible with current HTML structure
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Index page loaded');
    
    // ลองหา elements หลายวิธี
    const elements = {
        fileInput: document.getElementById('fileInput') || document.querySelector('input[type="file"]'),
        funcSelect: document.getElementById('funcSelect') || document.querySelector('select[name="func_name"]'),
        mainForm: document.getElementById('mainForm') || document.querySelector('form'),
        lookupLastTypeLink: document.getElementById('lookupLastTypeLink'),
        loading: document.getElementById('loading'),
        showTableCheckbox: document.getElementById('showTable')
    };

    // Additional elements for folder functionality
    const folderElements = {
        uploadMethodRadio: document.getElementById('uploadMethod'),
        folderMethodRadio: document.getElementById('folderMethod'),
        uploadSection: document.getElementById('uploadSection'),
        folderSection: document.getElementById('folderSection'),
        folderSelect: document.getElementById('folderSelect'),
        refreshFoldersBtn: document.getElementById('refreshFolders'),
        fileListContainer: document.getElementById('fileListContainer'),
        fileList: document.getElementById('fileList'),
        selectAllBtn: document.getElementById('selectAllFiles'),
        clearSelectionBtn: document.getElementById('clearSelection'),
        selectedFilesInput: document.getElementById('selectedFiles'),
        selectedFolderInput: document.getElementById('selectedFolder')
    };

    // Global variables for folder functionality
    let currentFolderFiles = [];
    let selectedFiles = new Set();
    let supportedExtensions = [];

    console.log('=== Elements Found ===');
    console.log('fileInput:', !!elements.fileInput, elements.fileInput);
    console.log('funcSelect:', !!elements.funcSelect, elements.funcSelect);
    console.log('mainForm:', !!elements.mainForm, elements.mainForm);
    console.log('=== Folder Elements ===');
    console.log('uploadMethodRadio:', !!folderElements.uploadMethodRadio);
    console.log('folderMethodRadio:', !!folderElements.folderMethodRadio);
    console.log('folderSelect:', !!folderElements.folderSelect);

    // Configuration
    const config = {
        functionsRequiringLookup: ['PNP_CHANG_TYPE'],
        maxFileSize: 50 * 1024 * 1024,
        allowedFileTypes: ['.xlsx', '.xls', '.csv', '.txt']
    };

    // ข้อมูลคำแนะนำไฟล์สำหรับแต่ละฟังก์ชัน
    const fileGuidanceData = {
        "Singulation": {
            "LOGVIEW": {
                acceptedFiles: ["TXT","txt"],
                description: "ไฟล์ข้อมูล Singulation",
                example: "MC 12.txt"
            }
        },
        "Pick & Place": {
            "PNP_CHANG_TYPE": {
                acceptedFiles: ["Excel (.xlsx, .xls)", "CSV (.csv)"],
                description: "ไฟล์ข้อมูล Pick & Place ที่มีคอลั่ม assy_pack_type, bom_no ของแต่ละเดือน",
                example: "ตัวอย่าง: WF size Apr1-Apr30'23 (UTL1)"
            }
        },
        "DA": {
            "DIE_ATTACK_AUTO_UPH": {
                acceptedFiles: ["Excel (.xlsx, .xls)", "CSV (.csv)"],
                description: "ไฟล์ข้อมูล Die Attack Auto UPH",
                example: "ตัวอย่าง: die_attack_data.xlsx"
            }
        },
        "WB": {
            "lookup_last_type": {
                acceptedFiles: ["Excel (.xlsx, .xls)"],
                description: "ไฟล์ BOM ที่มีคอลัมน์ Part Number และ Last Type",
                example: "ตัวอย่าง: BOM_list.xlsx"
            }
        }
    };

    // ถ้าไม่เจอ funcSelect ให้สร้างขึ้นมาใหม่
    if (!elements.funcSelect && elements.mainForm) {
        console.log('Creating funcSelect element...');
        createFuncSelectElement();
    }

    function createFuncSelectElement() {
        // หา container ที่เหมาะสม
        let container = document.querySelector('.form-group');
        if (!container && elements.mainForm) {
            container = elements.mainForm;
        }

        if (container) {
            const selectHTML = `
                <div class="form-group">
                    <label for="funcSelect">
                        <i class="fas fa-cogs"></i> เลือกฟังก์ชัน:
                    </label>
                    <select name="func_name" id="funcSelect" class="form-control" required>
                        <option value="">เลือกฟังก์ชัน</option>
                    </select>
                </div>
            `;
            
            container.insertAdjacentHTML('beforeend', selectHTML);
            elements.funcSelect = document.getElementById('funcSelect');
            console.log('✅ Created funcSelect element:', elements.funcSelect);
        }
    }

    // Check if required elements exist
    if (!elements.fileInput || !elements.funcSelect || !elements.mainForm) {
        console.error('Required DOM elements not found');
        console.log('fileInput:', !!elements.fileInput);
        console.log('funcSelect:', !!elements.funcSelect);
        console.log('mainForm:', !!elements.mainForm);
        
        // ลองอีกครั้งหลังจาก delay
        setTimeout(() => {
            elements.funcSelect = document.getElementById('funcSelect') || document.querySelector('select[name="func_name"]');
            if (elements.funcSelect) {
                console.log('✅ Found funcSelect after delay');
                init();
            }
        }, 500);
        return;
    }

    // Initialize
    init();

    function init() {
        setupEventListeners();
        restoreFormState();
        console.log('Index page initialized successfully');
    }

    function setupEventListeners() {
        // Form submission
        if (elements.mainForm) {
            elements.mainForm.addEventListener('submit', handleFormSubmit);
        }

        // Function selection
        if (elements.funcSelect) {
            elements.funcSelect.addEventListener('change', handleFunctionChange);
        }

        // File input changes
        if (elements.fileInput) {
            elements.fileInput.addEventListener('change', handleFileChange);
        }

        // จัดการการคลิกปุ่ม operation
        document.querySelectorAll('.operation-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const operation = this.dataset.operation;
                console.log('Operation button clicked:', operation);
                
                // ลบ active class จากปุ่มอื่น
                document.querySelectorAll('.operation-btn').forEach(b => b.classList.remove('active'));
                
                // เพิ่ม active class ให้ปุ่มที่เลือก
                this.classList.add('active');
                
                // อัปเดต hidden input
                const selectedOperationInput = document.getElementById('selectedOperation');
                if (selectedOperationInput) {
                    selectedOperationInput.value = operation;
                }
                
                // อัปเดต function select
                updateFunctionSelect(operation);
            });
        });

        // Input method selection - ตรวจสอบว่า element มีอยู่ก่อน
        if (folderElements.uploadMethodRadio && folderElements.folderMethodRadio) {
            folderElements.uploadMethodRadio.addEventListener('change', handleInputMethodChange);
            folderElements.folderMethodRadio.addEventListener('change', handleInputMethodChange);
        } else {
            console.log('Upload/folder method radios not found');
        }

        // Folder operations - ตรวจสอบว่า element มีอยู่ก่อน
        if (folderElements.refreshFoldersBtn) {
            folderElements.refreshFoldersBtn.addEventListener('click', loadAvailableFolders);
            // Load folders on page load
            loadAvailableFolders();
        }
        
        if (folderElements.folderSelect) {
            folderElements.folderSelect.addEventListener('change', handleFolderSelection);
        }
        
        if (folderElements.selectAllBtn) {
            folderElements.selectAllBtn.addEventListener('click', selectAllSupportedFiles);
        }
        
        if (folderElements.clearSelectionBtn) {
            folderElements.clearSelectionBtn.addEventListener('click', clearFileSelection);
        }
    }

    // ===== EVENT HANDLERS =====

    function handleInputMethodChange() {
        console.log('Input method changed');
        
        if (!folderElements.uploadMethodRadio || !folderElements.folderMethodRadio || 
            !folderElements.uploadSection || !folderElements.folderSection) {
            console.log('Some input method elements missing');
            return;
        }
        
        if (folderElements.uploadMethodRadio.checked) {
            folderElements.uploadSection.style.display = 'block';
            folderElements.folderSection.style.display = 'none';
            clearFileSelection();
        } else {
            folderElements.uploadSection.style.display = 'none';
            folderElements.folderSection.style.display = 'block';
            if (elements.fileInput) {
                elements.fileInput.value = '';
            }
        }
        saveFormState();
    }

    function updateFunctionSelect(operation) {
        console.log('=== updateFunctionSelect ===');
        console.log('Operation:', operation);
        console.log('funcSelect element:', elements.funcSelect);
        
        if (!elements.funcSelect) {
            console.error('❌ funcSelect element not found!');
            // ลองหาใหม่
            elements.funcSelect = document.getElementById('funcSelect') || document.querySelector('select[name="func_name"]');
            if (!elements.funcSelect) {
                console.error('❌ Still cannot find funcSelect element');
                return;
            }
        }
        
        // Clear current options
        elements.funcSelect.innerHTML = '<option value="">เลือกฟังก์ชัน</option>';
        
        // Get functions for selected operation
        if (fileGuidanceData[operation]) {
            console.log('✅ Found functions for operation:', Object.keys(fileGuidanceData[operation]));
            Object.keys(fileGuidanceData[operation]).forEach(funcName => {
                const option = document.createElement('option');
                option.value = funcName;
                option.textContent = funcName;
                elements.funcSelect.appendChild(option);
                console.log('Added function option:', funcName);
            });
            console.log(`✅ Added ${Object.keys(fileGuidanceData[operation]).length} functions`);
        } else {
            console.log('❌ No functions found for operation:', operation);
            console.log('Available operations:', Object.keys(fileGuidanceData));
        }
        
        // Update supported extensions for folder method
        updateSupportedExtensions();
        
        saveFormState();
    }

    function updateSupportedExtensions() {
        const selectedOperation = document.getElementById('selectedOperation') ? document.getElementById('selectedOperation').value : '';
        const selectedFunction = elements.funcSelect ? elements.funcSelect.value : '';
        
        supportedExtensions = [];
        
        if (selectedOperation && selectedFunction && fileGuidanceData[selectedOperation] && fileGuidanceData[selectedOperation][selectedFunction]) {
            const guidance = fileGuidanceData[selectedOperation][selectedFunction];
            
            // Extract file extensions from acceptedFiles
            guidance.acceptedFiles.forEach(fileType => {
                if (fileType.includes('TXT') || fileType.includes('txt')) {
                    supportedExtensions.push('.txt');
                }
                if (fileType.includes('.xlsx')) {
                    supportedExtensions.push('.xlsx');
                }
                if (fileType.includes('.xls')) {
                    supportedExtensions.push('.xls');
                }
                if (fileType.includes('.csv')) {
                    supportedExtensions.push('.csv');
                }
            });
        }
        
        console.log('Supported extensions:', supportedExtensions);
        
        // Refresh file list if folder is selected
        if (folderElements.folderMethodRadio && folderElements.folderMethodRadio.checked && 
            folderElements.folderSelect && folderElements.folderSelect.value) {
            loadFolderFiles(folderElements.folderSelect.value);
        }
    }

    function handleFunctionChange() {
        const selectedFunction = elements.funcSelect.value;
        console.log('Function selected:', selectedFunction);

        toggleLookupLink(selectedFunction);
        updateSupportedExtensions();
        saveFormState();
    }

    function handleFormSubmit(e) {
        console.log('Form submitted');
        
        // Check if using folder method
        if (folderElements.folderMethodRadio && folderElements.folderMethodRadio.checked) {
            // Validate folder selection
            if (!folderElements.folderSelect || !folderElements.folderSelect.value) {
                e.preventDefault();
                alert('กรุณาเลือกโฟลเดอร์ก่อน');
                return;
            }

            if (selectedFiles.size === 0) {
                e.preventDefault();
                alert('กรุณาเลือกไฟล์อย่างน้อย 1 ไฟล์');
                return;
            }

            // Show loading and continue
            if (elements.loading) {
                elements.loading.style.display = 'block';
            }
            saveFormState();
            return;
        }
        
        // Original validation for upload method
        if (!elements.funcSelect.value) {
            e.preventDefault();
            alert('กรุณาเลือกฟังก์ชันก่อน');
            return;
        }

        if (!elements.fileInput.files.length) {
            e.preventDefault();
            alert('กรุณาเลือกไฟล์ก่อน');
            return;
        }

        if (elements.loading) {
            elements.loading.style.display = 'block';
        }
        
        saveFormState();
    }

    // ===== FOLDER FUNCTIONS =====

    async function loadAvailableFolders() {
        console.log('🔄 Loading available folders...');
        
        if (!folderElements.refreshFoldersBtn || !folderElements.folderSelect) {
            console.log('❌ Required folder elements not found');
            return;
        }

        try {
            folderElements.refreshFoldersBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> กำลังโหลด...';
            folderElements.refreshFoldersBtn.disabled = true;

            const response = await fetch('/api/folders');
            const data = await response.json();

            console.log('📊 Folders response:', data);

            folderElements.folderSelect.innerHTML = '<option value="">-- เลือกโฟลเดอร์ --</option>';
            
            if (data.success && data.folders) {
                data.folders.forEach(folder => {
                    const option = document.createElement('option');
                    option.value = folder.path;
                    option.textContent = folder.name;
                    folderElements.folderSelect.appendChild(option);
                });
                console.log(`✅ Loaded ${data.folders.length} folders`);
            } else {
                console.error('❌ Failed to load folders:', data.message);
            }

        } catch (error) {
            console.error('❌ Error loading folders:', error);
        } finally {
            folderElements.refreshFoldersBtn.innerHTML = '<i class="fas fa-sync-alt"></i> รีเฟรช';
            folderElements.refreshFoldersBtn.disabled = false;
        }
    }

    async function handleFolderSelection() {
        const selectedFolder = folderElements.folderSelect ? folderElements.folderSelect.value : '';
        console.log('📂 Folder selected:', selectedFolder);
        
        if (selectedFolder) {
            await loadFolderFiles(selectedFolder);
            if (folderElements.fileListContainer) {
                folderElements.fileListContainer.style.display = 'block';
            }
            if (folderElements.selectedFolderInput) {
                folderElements.selectedFolderInput.value = selectedFolder;
            }
        } else {
            if (folderElements.fileListContainer) {
                folderElements.fileListContainer.style.display = 'none';
            }
            clearFileSelection();
        }
    }

    async function loadFolderFiles(folderPath) {
        console.log('📁 Loading files from folder:', folderPath);
        
        if (!folderElements.fileList) {
            console.error('❌ File list element not found');
            return;
        }

        try {
            folderElements.fileList.innerHTML = `
                <div class="loading-files">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>กำลังโหลดไฟล์...</p>
                </div>
            `;

            const response = await fetch(`/api/folder-files?path=${encodeURIComponent(folderPath)}`);
            const data = await response.json();

            if (data.success && data.files) {
                currentFolderFiles = data.files;
                console.log(`✅ Found ${currentFolderFiles.length} files`);
                renderFileList();
            } else {
                console.error('❌ Failed to load files:', data.message);
                folderElements.fileList.innerHTML = `
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>${data.message || 'ไม่สามารถโหลดไฟล์ในโฟลเดอร์ได้'}</p>
                    </div>
                `;
            }

        } catch (error) {
            console.error('❌ Error loading folder files:', error);
            folderElements.fileList.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>เกิดข้อผิดพลาดในการโหลดไฟล์</p>
                </div>
            `;
        }
    }

    function renderFileList() {
        if (!folderElements.fileList) return;

        if (currentFolderFiles.length === 0) {
            folderElements.fileList.innerHTML = `
                <div class="empty-folder">
                    <i class="fas fa-folder-open"></i>
                    <p>ไม่พบไฟล์ในโฟลเดอร์นี้</p>
                </div>
            `;
            return;
        }

        folderElements.fileList.innerHTML = '';
        
        currentFolderFiles.forEach(file => {
            const isSupported = isFileSupported(file.name);
            const fileItem = createFileItem(file, isSupported);
            folderElements.fileList.appendChild(fileItem);
        });

        updateSelectionSummary();
    }

    function createFileItem(file, isSupported) {
        const fileItem = document.createElement('div');
        fileItem.className = `file-item ${isSupported ? '' : 'disabled'}`;
        
        const fileExtension = file.name.split('.').pop().toLowerCase();
        const fileIcon = getFileIconClass(fileExtension);
        
        fileItem.innerHTML = `
            <input type="checkbox" class="file-checkbox" 
                   ${isSupported ? '' : 'disabled'} 
                   data-file="${file.name}"
                   ${selectedFiles.has(file.name) ? 'checked' : ''}>
            <div class="file-info">
                <div class="file-icon ${fileExtension}">
                    <i class="${fileIcon}"></i>
                </div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
                <div class="file-status ${isSupported ? 'supported' : 'unsupported'}">
                    ${isSupported ? 'รองรับ' : 'ไม่รองรับ'}
                </div>
            </div>
        `;

        if (isSupported) {
            const checkbox = fileItem.querySelector('.file-checkbox');
            checkbox.addEventListener('change', handleFileSelection);
            fileItem.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    checkbox.checked = !checkbox.checked;
                    handleFileSelection({ target: checkbox });
                }
            });
        }

        return fileItem;
    }

    function getFileIconClass(extension) {
        const iconMap = {
            'txt': 'fas fa-file-alt',
            'xlsx': 'fas fa-file-excel',
            'xls': 'fas fa-file-excel',
            'csv': 'fas fa-file-csv'
        };
        return iconMap[extension] || 'fas fa-file';
    }

    function isFileSupported(filename) {
        if (supportedExtensions.length === 0) return true;
        
        const fileExtension = '.' + filename.split('.').pop().toLowerCase();
        return supportedExtensions.includes(fileExtension);
    }

    function handleFileSelection(event) {
        const filename = event.target.dataset.file;
        const isChecked = event.target.checked;

        if (isChecked) {
            selectedFiles.add(filename);
        } else {
            selectedFiles.delete(filename);
        }

        const fileItem = event.target.closest('.file-item');
        if (isChecked) {
            fileItem.classList.add('selected');
        } else {
            fileItem.classList.remove('selected');
        }

        updateSelectedFilesInput();
        updateSelectionSummary();
    }

    function selectAllSupportedFiles() {
        currentFolderFiles.forEach(file => {
            if (isFileSupported(file.name)) {
                selectedFiles.add(file.name);
            }
        });
        
        document.querySelectorAll('.file-checkbox:not([disabled])').forEach(checkbox => {
            checkbox.checked = true;
            checkbox.closest('.file-item').classList.add('selected');
        });

        updateSelectedFilesInput();
        updateSelectionSummary();
    }

    function clearFileSelection() {
        selectedFiles.clear();
        
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.closest('.file-item').classList.remove('selected');
        });

        updateSelectedFilesInput();
        updateSelectionSummary();
    }

    function updateSelectedFilesInput() {
        if (folderElements.selectedFilesInput) {
            folderElements.selectedFilesInput.value = Array.from(selectedFiles).join(',');
        }
    }

    function updateSelectionSummary() {
        if (!folderElements.fileListContainer) return;

        const existingSummary = document.querySelector('.selection-summary');
        if (existingSummary) {
            existingSummary.remove();
        }

        if (selectedFiles.size > 0) {
            const summary = document.createElement('div');
            summary.className = 'selection-summary';
            summary.innerHTML = `
                <div class="selection-count">
                    <i class="fas fa-check-circle"></i>
                    เลือกแล้ว: ${selectedFiles.size} ไฟล์
                </div>
            `;
            folderElements.fileListContainer.appendChild(summary);
        }
    }

    // ===== UTILITY FUNCTIONS =====

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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
        saveFormState();
    }

    function saveFormState() {
        try {
            const state = {
                selectedFunction: elements.funcSelect ? elements.funcSelect.value : '',
                selectedOperation: document.getElementById('selectedOperation') ? document.getElementById('selectedOperation').value : '',
                inputMethod: folderElements.uploadMethodRadio ? (folderElements.uploadMethodRadio.checked ? 'upload' : 'folder') : 'upload'
            };
            localStorage.setItem('formState', JSON.stringify(state));
        } catch (e) {
            console.log('Could not save form state:', e);
        }
    }

    function restoreFormState() {
        try {
            const state = JSON.parse(localStorage.getItem('formState') || '{}');
            
            if (state.selectedOperation) {
                const operationBtn = document.querySelector(`[data-operation="${state.selectedOperation}"]`);
                if (operationBtn) {
                    operationBtn.click();
                }
            }
            
            if (state.selectedFunction && elements.funcSelect) {
                elements.funcSelect.value = state.selectedFunction;
                handleFunctionChange();
            }

            if (state.inputMethod && folderElements.uploadMethodRadio && folderElements.folderMethodRadio) {
                if (state.inputMethod === 'folder') {
                    folderElements.folderMethodRadio.checked = true;
                } else {
                    folderElements.uploadMethodRadio.checked = true;
                }
                handleInputMethodChange();
            }
        } catch (e) {
            console.log('Could not restore form state:', e);
        }
    }
});
