/**
 * Index Page JavaScript
 * Handles file upload and folder selection functionality
 */

class IndexPage {
    constructor() {
        this.elements = this.initializeElements();
        this.state = this.initializeState();
        this.config = this.initializeConfig();
        this.fileGuidanceData = this.initializeFileGuidanceData();
        
        this.logElementStatus();
        this.initialize();
    }

    // ===== INITIALIZATION =====
    
    initializeElements() {
        return {
            // Core elements
            fileInput: document.getElementById('fileInput') || document.querySelector('input[type="file"]'),
            funcSelect: document.getElementById('funcSelect') || document.querySelector('select[name="func_name"]'),
            mainForm: document.getElementById('mainForm') || document.querySelector('form'),
            lookupLastTypeLink: document.getElementById('lookupLastTypeLink'),
            loading: document.getElementById('loading'),
            showTableCheckbox: document.getElementById('showTable'),
            
            // Folder functionality elements
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
    }

    initializeState() {
        return {
            currentFolderFiles: [],
            selectedFiles: new Set(),
            supportedExtensions: []
        };
    }

    initializeConfig() {
        return {
            functionsRequiringLookup: ['PNP_CHANG_TYPE'],
            maxFileSize: 50 * 1024 * 1024, // 50MB
            allowedFileTypes: ['.xlsx', '.xls', '.csv', '.txt']
        };
    }

    initializeFileGuidanceData() {
        return {
            "Singulation": {
                "LOGVIEW": {
                    acceptedFiles: ["TXT", "txt"],
                    description: "ไฟล์ข้อมูล Singulation",
                    example: "MC 12.txt"
                }
            },
            "Pick & Place": {
                "PNP_CHANG_TYPE": {
                    acceptedFiles: ["Excel (.xlsx, .xls)", "CSV (.csv)"],
                    description: "ไฟล์ข้อมูล Pick & Place ที่มีคอลั่ม assy_pack_type, bom_no ของแต่ละเดือน",
                    example: "ตัวอย่าง: WF size Apr1-Apr30'23 (UTL1)"
                },
                "PNP_AUTO_UPH": {
                    acceptedFiles: ["Excel (.xlsx, .xls)", "CSV (.csv)"],
                    description: "ไฟล์ข้อมูล Pick & Place Auto UPH",
                    example: "ตัวอย่าง: pnp_data.xlsx"
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
                "WB_AUTO_UPH": {
                    acceptedFiles: ["Excel (.xlsx, .xls)", "CSV (.csv)"],
                    description: "ไฟล์ข้อมูล Wire Bond Auto UPH",
                    example: "ตัวอย่าง: wb_data.xlsx"
                }
            }
        };
    }

    logElementStatus() {
        console.log('=== Index Page Loaded ===');
        console.log('Core Elements:');
        console.log('  fileInput:', !!this.elements.fileInput);
        console.log('  funcSelect:', !!this.elements.funcSelect);
        console.log('  mainForm:', !!this.elements.mainForm);
        console.log('Folder Elements:');
        console.log('  uploadMethodRadio:', !!this.elements.uploadMethodRadio);
        console.log('  folderMethodRadio:', !!this.elements.folderMethodRadio);
        console.log('  folderSelect:', !!this.elements.folderSelect);
    }

    
    initialize() {
        // Check if required elements exist
        if (!this.elements.fileInput || !this.elements.funcSelect || !this.elements.mainForm) {
            console.error('Required DOM elements not found');
            this.createMissingElements();
            return;
        }

        this.setupEventListeners();
        this.restoreFormState();
        this.loadAvailableFolders();
        console.log('Index page initialized successfully');
    }

    createMissingElements() {
        // Create funcSelect if missing
        if (!this.elements.funcSelect && this.elements.mainForm) {
            console.log('Creating funcSelect element...');
            const container = this.elements.mainForm;
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
            this.elements.funcSelect = document.getElementById('funcSelect');
            console.log('✅ Created funcSelect element');
        }
    }

    // ===== EVENT LISTENERS =====

    setupEventListeners() {
        this.setupCoreEventListeners();
        this.setupOperationEventListeners();
        this.setupFolderEventListeners();
    }

    setupCoreEventListeners() {
        // Form submission
        if (this.elements.mainForm) {
            this.elements.mainForm.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Function selection
        if (this.elements.funcSelect) {
            this.elements.funcSelect.addEventListener('change', () => this.handleFunctionChange());
        }

        // File input changes
        if (this.elements.fileInput) {
            this.elements.fileInput.addEventListener('change', () => this.handleFileChange());
        }

        // Form state changes
        if (this.elements.showTableCheckbox) {
            this.elements.showTableCheckbox.addEventListener('change', () => this.saveFormState());
        }

        // Setup drag and drop
        this.setupDragAndDrop();
    }

    setupOperationEventListeners() {
        document.querySelectorAll('.operation-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleOperationClick(e));
        });
    }

    setupFolderEventListeners() {
        // Input method selection
        if (this.elements.uploadMethodRadio && this.elements.folderMethodRadio) {
            this.elements.uploadMethodRadio.addEventListener('change', () => this.handleInputMethodChange());
            this.elements.folderMethodRadio.addEventListener('change', () => this.handleInputMethodChange());
        }

        // Folder operations
        if (this.elements.refreshFoldersBtn) {
            this.elements.refreshFoldersBtn.addEventListener('click', () => this.loadAvailableFolders());
        }
        
        if (this.elements.folderSelect) {
            this.elements.folderSelect.addEventListener('change', () => this.handleFolderSelection());
        }
        
        if (this.elements.selectAllBtn) {
            this.elements.selectAllBtn.addEventListener('click', () => this.selectAllSupportedFiles());
        }
        
        if (this.elements.clearSelectionBtn) {
            this.elements.clearSelectionBtn.addEventListener('click', () => this.clearFileSelection());
        }
    }

    setupDragAndDrop() {
        const dropZone = this.elements.fileInput?.closest('.form-group');
        if (!dropZone) return;

        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });

        dropZone.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.elements.fileInput.files = files;
                this.handleFileChange();
            }
        });
    }
    // ===== EVENT HANDLERS =====

    handleOperationClick(event) {
        console.log('=== Operation Click Event ===');
        
        // Get the button element (handle both direct click and icon click)
        let button = event.target;
        if (!button.classList.contains('operation-btn')) {
            button = button.closest('.operation-btn');
        }
        
        if (!button) {
            console.error('❌ Could not find operation button');
            return;
        }
        
        const operation = button.dataset.operation;
        console.log('🎯 Operation button clicked:', operation);
        
        // Remove active class from other buttons
        document.querySelectorAll('.operation-btn').forEach(btn => {
            btn.classList.remove('active');
            console.log('Removed active from:', btn.dataset.operation);
        });
        
        // Add active class to clicked button
        button.classList.add('active');
        console.log('✅ Added active to:', operation);
        
        // Update hidden input
        const selectedOperationInput = document.getElementById('selectedOperation');
        if (selectedOperationInput) {
            selectedOperationInput.value = operation;
            console.log('📝 Updated hidden input value:', operation);
        } else {
            console.error('❌ selectedOperation input not found');
        }
        
        // Update function select
        console.log('🔄 Updating function select...');
        this.updateFunctionSelect(operation);
        
        console.log('=== Operation Click Complete ===');
    }

    handleInputMethodChange() {
        console.log('Input method changed');
        
        if (!this.elements.uploadMethodRadio || !this.elements.folderMethodRadio || 
            !this.elements.uploadSection || !this.elements.folderSection) {
            console.log('Some input method elements missing');
            return;
        }
        
        if (this.elements.uploadMethodRadio.checked) {
            this.elements.uploadSection.style.display = 'block';
            this.elements.folderSection.style.display = 'none';
            this.clearFileSelection();
        } else {
            this.elements.uploadSection.style.display = 'none';
            this.elements.folderSection.style.display = 'block';
            if (this.elements.fileInput) {
                this.elements.fileInput.value = '';
            }
        }
        this.saveFormState();
    }

    handleFunctionChange() {
        const selectedFunction = this.elements.funcSelect.value;
        console.log('Function selected:', selectedFunction);

        this.toggleLookupLink(selectedFunction);
        this.updateSupportedExtensions();
        this.saveFormState();

        if (selectedFunction) {
            this.showMessage(`เลือกฟังก์ชัน: ${selectedFunction}`, 'info');
        }
    }

    handleFileChange() {
        const files = Array.from(this.elements.fileInput.files);
        console.log('Files selected:', files.length);

        if (files.length > 0) {
            const validation = this.validateFiles(files);
            if (validation.isValid) {
                this.showMessage(`เลือกไฟล์แล้ว: ${files.length} ไฟล์`, 'success');
            } else {
                this.showMessage(validation.message, 'error');
            }
        } else {
            this.showMessage('ยกเลิกการเลือกไฟล์', 'info');
        }
        
        this.saveFormState();
    }

    handleFormSubmit(event) {
        console.log('Form submitted');
        
        // Check if using folder method
        if (this.elements.folderMethodRadio && this.elements.folderMethodRadio.checked) {
            if (!this.elements.folderSelect || !this.elements.folderSelect.value) {
                event.preventDefault();
                this.showMessage('กรุณาเลือกโฟลเดอร์ก่อน', 'error');
                return;
            }

            if (this.state.selectedFiles.size === 0) {
                event.preventDefault();
                this.showMessage('กรุณาเลือกไฟล์อย่างน้อย 1 ไฟล์', 'error');
                return;
            }

            this.showLoading();
            this.saveFormState();
            return;
        }
        
        // Original validation for upload method
        if (!this.elements.funcSelect.value) {
            event.preventDefault();
            this.showMessage('กรุณาเลือกฟังก์ชันก่อน', 'error');
            return;
        }

        if (!this.elements.fileInput.files.length) {
            event.preventDefault();
            this.showMessage('กรุณาเลือกไฟล์ก่อน', 'error');
            return;
        }

        const validation = this.validateFiles(this.elements.fileInput.files);
        if (!validation.isValid) {
            event.preventDefault();
            this.showMessage(validation.message, 'error');
            return;
        }

        this.showLoading();
        this.saveFormState();
    }

    // ===== FOLDER OPERATIONS =====

    async loadAvailableFolders() {
        console.log('🔄 Loading available folders...');
        
        if (!this.elements.refreshFoldersBtn || !this.elements.folderSelect) {
            console.log('❌ Required folder elements not found');
            return;
        }

        try {
            this.elements.refreshFoldersBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> กำลังโหลด...';
            this.elements.refreshFoldersBtn.disabled = true;

            const response = await fetch('/api/folders');
            const data = await response.json();

            console.log('📊 Folders response:', data);

            this.elements.folderSelect.innerHTML = '<option value="">-- เลือกโฟลเดอร์ --</option>';
            
            if (data.success && data.folders) {
                data.folders.forEach(folder => {
                    const option = document.createElement('option');
                    option.value = folder.path;
                    option.textContent = folder.name;
                    this.elements.folderSelect.appendChild(option);
                });
                console.log(`✅ Loaded ${data.folders.length} folders`);
            } else {
                console.error('❌ Failed to load folders:', data.message);
                this.showMessage('ไม่สามารถโหลดรายการโฟลเดอร์ได้', 'error');
            }

        } catch (error) {
            console.error('❌ Error loading folders:', error);
            this.showMessage('ไม่สามารถโหลดรายการโฟลเดอร์ได้', 'error');
        } finally {
            this.elements.refreshFoldersBtn.innerHTML = '<i class="fas fa-sync-alt"></i> รีเฟรช';
            this.elements.refreshFoldersBtn.disabled = false;
        }
    }

    async handleFolderSelection() {
        const selectedFolder = this.elements.folderSelect ? this.elements.folderSelect.value : '';
        console.log('📂 Folder selected:', selectedFolder);
        
        if (selectedFolder) {
            await this.loadFolderFiles(selectedFolder);
            if (this.elements.fileListContainer) {
                this.elements.fileListContainer.style.display = 'block';
            }
            if (this.elements.selectedFolderInput) {
                this.elements.selectedFolderInput.value = selectedFolder;
            }
        } else {
            if (this.elements.fileListContainer) {
                this.elements.fileListContainer.style.display = 'none';
            }
            this.clearFileSelection();
        }
    }

    async loadFolderFiles(folderPath) {
        console.log('📁 Loading files from folder:', folderPath);
        
        if (!this.elements.fileList) {
            console.error('❌ File list element not found');
            return;
        }

        try {
            this.elements.fileList.innerHTML = `
                <div class="loading-files">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>กำลังโหลดไฟล์...</p>
                </div>
            `;

            const response = await fetch(`/api/folder-files?path=${encodeURIComponent(folderPath)}`);
            const data = await response.json();

            if (data.success && data.files) {
                this.state.currentFolderFiles = data.files;
                console.log(`✅ Found ${this.state.currentFolderFiles.length} files`);
                this.renderFileList();
            } else {
                console.error('❌ Failed to load files:', data.message);
                this.elements.fileList.innerHTML = `
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>${data.message || 'ไม่สามารถโหลดไฟล์ในโฟลเดอร์ได้'}</p>
                    </div>
                `;
                this.showMessage(data.message || 'ไม่สามารถโหลดไฟล์ในโฟลเดอร์ได้', 'error');
            }

        } catch (error) {
            console.error('❌ Error loading folder files:', error);
            this.elements.fileList.innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>เกิดข้อผิดพลาดในการโหลดไฟล์</p>
                </div>
            `;
            this.showMessage('เกิดข้อผิดพลาดในการโหลดไฟล์', 'error');
        }
    }

    renderFileList() {
        if (!this.elements.fileList) return;

        if (this.state.currentFolderFiles.length === 0) {
            this.elements.fileList.innerHTML = `
                <div class="empty-folder">
                    <i class="fas fa-folder-open"></i>
                    <p>ไม่พบไฟล์ในโฟลเดอร์นี้</p>
                </div>
            `;
            return;
        }

        this.elements.fileList.innerHTML = '';
        
        this.state.currentFolderFiles.forEach(file => {
            const isSupported = this.isFileSupported(file.name);
            const fileItem = this.createFileItem(file, isSupported);
            this.elements.fileList.appendChild(fileItem);
        });

        this.updateSelectionSummary();
    }

    createFileItem(file, isSupported) {
        const fileItem = document.createElement('div');
        fileItem.className = `file-item ${isSupported ? '' : 'disabled'}`;
        
        const fileExtension = file.name.split('.').pop().toLowerCase();
        const fileIcon = this.getFileIconClass(fileExtension);
        
        fileItem.innerHTML = `
            <input type="checkbox" class="file-checkbox" 
                   ${isSupported ? '' : 'disabled'} 
                   data-file="${file.name}"
                   ${this.state.selectedFiles.has(file.name) ? 'checked' : ''}>
            <div class="file-info">
                <div class="file-icon ${fileExtension}">
                    <i class="${fileIcon}"></i>
                </div>
                <div class="file-details">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
                <div class="file-status ${isSupported ? 'supported' : 'unsupported'}">
                    ${isSupported ? 'รองรับ' : 'ไม่รองรับ'}
                </div>
            </div>
        `;

        if (isSupported) {
            const checkbox = fileItem.querySelector('.file-checkbox');
            checkbox.addEventListener('change', (e) => this.handleFileSelection(e));
            fileItem.addEventListener('click', (e) => {
                if (e.target.type !== 'checkbox') {
                    checkbox.checked = !checkbox.checked;
                    this.handleFileSelection({ target: checkbox });
                }
            });
        }

        return fileItem;
    }

    handleFileSelection(event) {
        const filename = event.target.dataset.file;
        const isChecked = event.target.checked;

        if (isChecked) {
            this.state.selectedFiles.add(filename);
        } else {
            this.state.selectedFiles.delete(filename);
        }

        const fileItem = event.target.closest('.file-item');
        if (isChecked) {
            fileItem.classList.add('selected');
        } else {
            fileItem.classList.remove('selected');
        }

        this.updateSelectedFilesInput();
        this.updateSelectionSummary();
    }

    selectAllSupportedFiles() {
        this.state.currentFolderFiles.forEach(file => {
            if (this.isFileSupported(file.name)) {
                this.state.selectedFiles.add(file.name);
            }
        });
        
        document.querySelectorAll('.file-checkbox:not([disabled])').forEach(checkbox => {
            checkbox.checked = true;
            checkbox.closest('.file-item').classList.add('selected');
        });

        this.updateSelectedFilesInput();
        this.updateSelectionSummary();
        this.showMessage(`เลือกไฟล์ทั้งหมด ${this.state.selectedFiles.size} ไฟล์`, 'success');
    }

    clearFileSelection() {
        this.state.selectedFiles.clear();
        
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.checked = false;
            checkbox.closest('.file-item').classList.remove('selected');
        });

        this.updateSelectedFilesInput();
        this.updateSelectionSummary();
    }

    updateSelectedFilesInput() {
        if (this.elements.selectedFilesInput) {
            this.elements.selectedFilesInput.value = Array.from(this.state.selectedFiles).join(',');
        }
    }

    updateSelectionSummary() {
        if (!this.elements.fileListContainer) return;

        const existingSummary = document.querySelector('.selection-summary');
        if (existingSummary) {
            existingSummary.remove();
        }

        if (this.state.selectedFiles.size > 0) {
            const summary = document.createElement('div');
            summary.className = 'selection-summary';
            summary.innerHTML = `
                <div class="selection-count">
                    <i class="fas fa-check-circle"></i>
                    เลือกแล้ว: ${this.state.selectedFiles.size} ไฟล์
                </div>
            `;
            this.elements.fileListContainer.appendChild(summary);
        }
    }

    // ===== UTILITY FUNCTIONS =====

    updateFunctionSelect(operation) {
        console.log('=== updateFunctionSelect ===');
        console.log('🎯 Operation:', operation);
        console.log('📋 funcSelect element:', this.elements.funcSelect);
        console.log('🗺️ Available operations:', Object.keys(this.fileGuidanceData));
        
        if (!this.elements.funcSelect) {
            console.error('❌ funcSelect element not found!');
            console.log('🔍 Trying to find funcSelect in DOM...');
            const funcSelectInDOM = document.getElementById('funcSelect');
            console.log('🔍 Found funcSelect in DOM:', !!funcSelectInDOM);
            if (funcSelectInDOM) {
                this.elements.funcSelect = funcSelectInDOM;
                console.log('✅ Updated funcSelect reference');
            } else {
                console.error('❌ funcSelect not found anywhere in DOM');
                return;
            }
        }
        
        // Clear current options
        this.elements.funcSelect.innerHTML = '<option value="">เลือกฟังก์ชัน</option>';
        console.log('🧹 Cleared existing options');
        
        // Get functions for selected operation
        if (this.fileGuidanceData[operation]) {
            const functions = Object.keys(this.fileGuidanceData[operation]);
            console.log('✅ Found functions for operation:', functions);
            
            functions.forEach(funcName => {
                const option = document.createElement('option');
                option.value = funcName;
                option.textContent = funcName;
                this.elements.funcSelect.appendChild(option);
                console.log('➕ Added function option:', funcName);
            });
            console.log(`✅ Added ${functions.length} functions to select`);
        } else {
            console.log('❌ No functions found for operation:', operation);
            console.log('📋 fileGuidanceData:', this.fileGuidanceData);
        }
        
        // Update supported extensions for folder method
        this.updateSupportedExtensions();
        this.saveFormState();
        console.log('=== updateFunctionSelect Complete ===');
    }

    updateSupportedExtensions() {
        const selectedOperation = document.getElementById('selectedOperation')?.value || '';
        const selectedFunction = this.elements.funcSelect?.value || '';
        
        this.state.supportedExtensions = [];
        
        if (selectedOperation && selectedFunction && 
            this.fileGuidanceData[selectedOperation] && 
            this.fileGuidanceData[selectedOperation][selectedFunction]) {
            
            const guidance = this.fileGuidanceData[selectedOperation][selectedFunction];
            
            // Extract file extensions from acceptedFiles
            guidance.acceptedFiles.forEach(fileType => {
                if (fileType.includes('TXT') || fileType.includes('txt')) {
                    this.state.supportedExtensions.push('.txt');
                }
                if (fileType.includes('.xlsx')) {
                    this.state.supportedExtensions.push('.xlsx');
                }
                if (fileType.includes('.xls')) {
                    this.state.supportedExtensions.push('.xls');
                }
                if (fileType.includes('.csv')) {
                    this.state.supportedExtensions.push('.csv');
                }
            });
        }
        
        console.log('Supported extensions:', this.state.supportedExtensions);
        
        // Refresh file list if folder is selected
        if (this.elements.folderMethodRadio?.checked && this.elements.folderSelect?.value) {
            this.loadFolderFiles(this.elements.folderSelect.value);
        }
    }

    validateFiles(files) {
        for (let file of files) {
            // Check file size
            if (file.size > this.config.maxFileSize) {
                return {
                    isValid: false,
                    message: `ไฟล์ ${file.name} มีขนาดใหญ่เกินไป (สูงสุด 50MB)`
                };
            }

            // Check file type
            const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
            if (!this.config.allowedFileTypes.includes(fileExtension)) {
                return {
                    isValid: false,
                    message: `ไฟล์ ${file.name} ไม่ใช่ประเภทที่รองรับ`
                };
            }
        }

        return { isValid: true };
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    getFileIconClass(extension) {
        const iconMap = {
            'txt': 'fas fa-file-alt',
            'xlsx': 'fas fa-file-excel',
            'xls': 'fas fa-file-excel',
            'csv': 'fas fa-file-csv'
        };
        return iconMap[extension] || 'fas fa-file';
    }

    isFileSupported(filename) {
        if (this.state.supportedExtensions.length === 0) return true;
        
        const fileExtension = '.' + filename.split('.').pop().toLowerCase();
        return this.state.supportedExtensions.includes(fileExtension);
    }

    toggleLookupLink(functionName) {
        if (!this.elements.lookupLastTypeLink) return;

        const shouldShow = this.config.functionsRequiringLookup.includes(functionName);
        
        if (shouldShow) {
            this.elements.lookupLastTypeLink.style.display = "inline-block";
        } else {
            this.elements.lookupLastTypeLink.style.display = "none";
        }
    }

    showLoading() {
        if (this.elements.loading) {
            this.elements.loading.style.display = 'block';
        }
    }

    showMessage(message, type = 'info') {
        console.log(`${type.toUpperCase()}: ${message}`);
        
        // Create message container if it doesn't exist
        let messageContainer = document.getElementById('messageContainer');
        if (!messageContainer) {
            messageContainer = document.createElement('div');
            messageContainer.id = 'messageContainer';
            messageContainer.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
            `;
            document.body.appendChild(messageContainer);
        }
        
        // Create message element
        const messageElement = document.createElement('div');
        messageElement.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible`;
        messageElement.style.cssText = `
            margin-bottom: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        `;
        messageElement.innerHTML = `
            ${message}
            <button type="button" class="btn-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        messageContainer.appendChild(messageElement);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (messageElement.parentElement) {
                messageElement.remove();
            }
        }, 5000);
    }

    // ===== STATE MANAGEMENT =====

    saveFormState() {
        try {
            const state = {
                selectedFunction: this.elements.funcSelect?.value || '',
                selectedOperation: document.getElementById('selectedOperation')?.value || '',
                inputMethod: this.elements.uploadMethodRadio?.checked ? 'upload' : 'folder',
                showTable: this.elements.showTableCheckbox?.checked ?? true
            };
            localStorage.setItem('formState', JSON.stringify(state));
        } catch (e) {
            console.log('Could not save form state:', e);
        }
    }

    restoreFormState() {
        try {
            const state = JSON.parse(localStorage.getItem('formState') || '{}');
            
            if (state.selectedOperation) {
                const operationBtn = document.querySelector(`[data-operation="${state.selectedOperation}"]`);
                if (operationBtn) {
                    operationBtn.click();
                }
            }
            
            if (state.selectedFunction && this.elements.funcSelect) {
                this.elements.funcSelect.value = state.selectedFunction;
                this.handleFunctionChange();
            }

            if (state.inputMethod && this.elements.uploadMethodRadio && this.elements.folderMethodRadio) {
                if (state.inputMethod === 'folder') {
                    this.elements.folderMethodRadio.checked = true;
                } else {
                    this.elements.uploadMethodRadio.checked = true;
                }
                this.handleInputMethodChange();
            }

            if (this.elements.showTableCheckbox && typeof state.showTable === 'boolean') {
                this.elements.showTableCheckbox.checked = state.showTable;
            }
        } catch (e) {
            console.log('Could not restore form state:', e);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    new IndexPage();
});
