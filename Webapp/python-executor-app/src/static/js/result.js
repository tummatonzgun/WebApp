document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggleTable');
    const tableSection = document.querySelector('.table-section');
    const searchInput = document.getElementById('searchInput');
    const dropdownFilters = document.getElementById('dropdownFilters');
    let resultTable = null;
    let originalData = [];
    
    // Initialize page
    initializePage();
    setupEventListeners();
    setupTableFeatures();
    
    function initializePage() {
        // Initialize DataTable if table exists
        if (document.querySelector('.result-table')) {
            initializeDataTable();
        }
        
        // Set initial table visibility
        if (tableSection) {
            const isTableVisible = localStorage.getItem('tableVisible') !== 'false';
            toggleTableVisibility(isTableVisible);
        }
        
        // Initialize dropdown filters
        initializeFilters();
        
        // Show statistics
        updateStatistics();
    }
    
    function initializeDataTable() {
        const table = document.querySelector('.result-table');
        if (!table) return;
        
        // Store original data
        storeOriginalData();
        
        // Initialize DataTable with enhanced features
        resultTable = $(table).DataTable({
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
                "zeroRecords": "ไม่พบข้อมูลที่ตรงกัน",
                "loadingRecords": "กำลังโหลดข้อมูล...",
                "processing": "กำลังประมวลผล..."
            },
            "responsive": true,
            "order": [],
            "columnDefs": [
                { "orderable": true, "targets": "_all" },
                { "searchable": true, "targets": "_all" }
            ],
            "dom": '<"top"lf>rt<"bottom"ip><"clear">',
            "scrollX": true,
            "scrollY": "400px",
            "scrollCollapse": true,
            "fixedColumns": {
                "leftColumns": 1
            },
            "buttons": [
                {
                    extend: 'excel',
                    text: '<i class="fas fa-file-excel"></i> Excel',
                    className: 'btn btn-success',
                    exportOptions: {
                        columns: ':visible'
                    }
                },
                {
                    extend: 'csv',
                    text: '<i class="fas fa-file-csv"></i> CSV',
                    className: 'btn btn-info'
                },
                {
                    extend: 'copy',
                    text: '<i class="fas fa-copy"></i> คัดลอก',
                    className: 'btn btn-secondary'
                }
            ]
        });
        
        // Add export buttons
        resultTable.buttons().container()
            .appendTo('.controls-header');
    }
    
    function storeOriginalData() {
        const table = document.querySelector('.result-table tbody');
        if (table) {
            originalData = Array.from(table.querySelectorAll('tr')).map(row => ({
                element: row.cloneNode(true),
                data: Array.from(row.cells).map(cell => cell.textContent.trim())
            }));
        }
    }
    
    function setupEventListeners() {
        // Toggle table button
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function() {
                const isVisible = tableSection.classList.contains('active');
                toggleTableVisibility(!isVisible);
            });
        }
        
        // Search input
        if (searchInput) {
            searchInput.addEventListener('input', debounce(handleSearch, 300));
            searchInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    handleSearch();
                }
            });
        }
        
        // Dropdown filters
        if (dropdownFilters) {
            dropdownFilters.addEventListener('change', handleFilterChange);
        }
        
        // Download button clicks
        document.querySelectorAll('.download-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                const url = this.href;
                if (url) {
                    showMessage('กำลังดาวน์โหลดไฟล์...', 'info');
                    trackDownload(url);
                }
            });
        });
        
        // Back button
        document.querySelectorAll('.nav-btn').forEach(btn => {
            if (btn.textContent.includes('กลับ')) {
                btn.addEventListener('click', function(e) {
                    e.preventDefault();
                    if (confirm('คุณต้องการกลับไปหน้าหลักใช่หรือไม่?')) {
                        window.location.href = this.href;
                    }
                });
            }
        });
    }
    
    function setupTableFeatures() {
        // Add row click functionality
        if (resultTable) {
            $('.result-table tbody').on('click', 'tr', function() {
                if ($(this).hasClass('selected')) {
                    $(this).removeClass('selected');
                } else {
                    $('.result-table tbody tr.selected').removeClass('selected');
                    $(this).addClass('selected');
                }
                
                // Show row details
                showRowDetails(this);
            });
        }
        
        // Add double-click to copy
        if (document.querySelector('.result-table')) {
            document.querySelector('.result-table').addEventListener('dblclick', function(e) {
                const cell = e.target.closest('td');
                if (cell) {
                    copyToClipboard(cell.textContent.trim());
                    highlightCell(cell);
                }
            });
        }
        
        // Add column sorting indicators
        enhanceColumnSorting();
    }
    
    function toggleTableVisibility(show) {
        if (!tableSection) return;
        
        if (show) {
            tableSection.classList.add('active');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> ซ่อนตาราง';
            }
            localStorage.setItem('tableVisible', 'true');
            
            // Recalculate DataTable columns if needed
            if (resultTable) {
                setTimeout(() => {
                    resultTable.columns.adjust();
                    resultTable.responsive.recalc();
                }, 300);
            }
        } else {
            tableSection.classList.remove('active');
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fas fa-eye"></i> แสดงตาราง';
            }
            localStorage.setItem('tableVisible', 'false');
        }
    }
    
    function handleSearch() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        
        if (resultTable) {
            // Use DataTable search
            resultTable.search(searchTerm).draw();
        } else {
            // Manual search for non-DataTable
            manualSearch(searchTerm);
        }
        
        // Update search statistics
        updateSearchStatistics(searchTerm);
        
        // Save search term
        sessionStorage.setItem('lastSearch', searchTerm);
    }
    
    function manualSearch(searchTerm) {
        const rows = document.querySelectorAll('.result-table tbody tr');
        let visibleCount = 0;
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const isMatch = !searchTerm || text.includes(searchTerm);
            
            row.style.display = isMatch ? '' : 'none';
            
            if (isMatch) {
                visibleCount++;
                if (searchTerm) {
                    highlightSearchTerm(row, searchTerm);
                } else {
                    removeSearchHighlight(row);
                }
            }
        });
        
        updateResultCount(visibleCount, rows.length);
    }
    
    function highlightSearchTerm(row, term) {
        const cells = row.querySelectorAll('td');
        cells.forEach(cell => {
            let content = cell.innerHTML;
            
            // Remove existing highlights
            content = content.replace(/<mark class="search-highlight">(.*?)<\/mark>/gi, '$1');
            
            // Add new highlights
            if (term) {
                const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi');
                content = content.replace(regex, '<mark class="search-highlight">$1</mark>');
            }
            
            cell.innerHTML = content;
        });
    }
    
    function removeSearchHighlight(row) {
        const highlights = row.querySelectorAll('.search-highlight');
        highlights.forEach(highlight => {
            highlight.outerHTML = highlight.textContent;
        });
    }
    
    function handleFilterChange(e) {
        const select = e.target;
        const column = select.dataset.column;
        const value = select.value;
        
        if (resultTable && column) {
            if (value === '') {
                // Clear filter
                resultTable.column(column).search('').draw();
            } else {
                // Apply filter
                resultTable.column(column).search(value, true, false).draw();
            }
        }
        
        updateFilterStatistics();
    }
    
    function initializeFilters() {
        if (!dropdownFilters || !resultTable) return;
        
        // Generate filter dropdowns for specific columns
        const filterColumns = [1, 2, 3]; // Adjust based on your table structure
        
        filterColumns.forEach(columnIndex => {
            if (resultTable.column(columnIndex).data().length > 0) {
                createColumnFilter(columnIndex);
            }
        });
    }
    
    function createColumnFilter(columnIndex) {
        const column = resultTable.column(columnIndex);
        const uniqueValues = column.data().unique().sort();
        
        if (uniqueValues.length > 1 && uniqueValues.length < 50) {
            const select = document.createElement('select');
            select.className = 'form-control';
            select.dataset.column = columnIndex;
            
            // Add default option
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = `ทั้งหมด (${column.header().textContent})`;
            select.appendChild(defaultOption);
            
            // Add unique values
            uniqueValues.each(function(value) {
                if (value && value.trim()) {
                    const option = document.createElement('option');
                    option.value = value;
                    option.textContent = value;
                    select.appendChild(option);
                }
            });
            
            dropdownFilters.appendChild(select);
        }
    }
    
    function showRowDetails(row) {
        const cells = Array.from(row.cells);
        const headers = Array.from(document.querySelectorAll('.result-table th'));
        
        let detailsHTML = '<div class="row-details"><h4>รายละเอียดแถว</h4>';
        
        cells.forEach((cell, index) => {
            if (headers[index]) {
                detailsHTML += `
                    <div class="detail-item">
                        <strong>${headers[index].textContent}:</strong>
                        <span>${cell.textContent}</span>
                    </div>
                `;
            }
        });
        
        detailsHTML += '</div>';
        
        // Show in modal or side panel
        showModal('รายละเอียด', detailsHTML);
    }
    
    function showModal(title, content) {
        // Create modal if it doesn't exist
        let modal = document.getElementById('detailModal');
        if (!modal) {
            modal = createModal();
        }
        
        modal.querySelector('.modal-title').textContent = title;
        modal.querySelector('.modal-body').innerHTML = content;
        modal.style.display = 'block';
        
        // Close modal handlers
        modal.querySelector('.close').onclick = () => modal.style.display = 'none';
        window.onclick = (e) => {
            if (e.target === modal) modal.style.display = 'none';
        };
    }
    
    function createModal() {
        const modal = document.createElement('div');
        modal.id = 'detailModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title"></h3>
                    <span class="close">&times;</span>
                </div>
                <div class="modal-body"></div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }
    
    function highlightCell(cell) {
        cell.style.background = '#fff3cd';
        setTimeout(() => {
            cell.style.background = '';
        }, 1000);
    }
    
    function copyToClipboard(text) {
        navigator.clipboard.writeText(text).then(() => {
            showMessage('คัดลอกข้อมูลแล้ว', 'success');
        }).catch(() => {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            showMessage('คัดลอกข้อมูลแล้ว', 'success');
        });
    }
    
    function updateStatistics() {
        if (!resultTable) return;
        
        const info = resultTable.page.info();
        const statsCards = document.querySelectorAll('.stat-card');
        
        statsCards.forEach(card => {
            const type = card.dataset.type;
            switch(type) {
                case 'total':
                    card.querySelector('.stat-number').textContent = info.recordsTotal;
                    break;
                case 'filtered':
                    card.querySelector('.stat-number').textContent = info.recordsDisplay;
                    break;
                case 'pages':
                    card.querySelector('.stat-number').textContent = Math.ceil(info.recordsDisplay / info.length);
                    break;
            }
        });
    }
    
    function updateSearchStatistics(searchTerm) {
        if (searchTerm) {
            const matches = resultTable ? resultTable.page.info().recordsDisplay : 
                           document.querySelectorAll('.result-table tbody tr:not([style*="display: none"])').length;
            showMessage(`พบ ${matches} รายการที่ตรงกับ "${searchTerm}"`, 'info');
        }
    }
    
    function updateFilterStatistics() {
        if (resultTable) {
            const info = resultTable.page.info();
            const filterCount = document.querySelectorAll('#dropdownFilters select').length;
            const activeFilters = Array.from(document.querySelectorAll('#dropdownFilters select'))
                .filter(select => select.value !== '').length;
            
            if (activeFilters > 0) {
                showMessage(`ใช้ตัวกรอง ${activeFilters}/${filterCount} แสดง ${info.recordsDisplay} รายการ`, 'info');
            }
        }
    }
    
    function updateResultCount(visible, total) {
        const countElement = document.getElementById('resultCount');
        if (countElement) {
            countElement.textContent = `แสดง ${visible} จาก ${total} รายการ`;
        }
    }
    
    function trackDownload(url) {
        // Track download analytics
        if (typeof gtag !== 'undefined') {
            gtag('event', 'download', {
                'file_url': url,
                'file_type': url.split('.').pop()
            });
        }
    }
    
    function enhanceColumnSorting() {
        if (!resultTable) return;
        
        document.querySelectorAll('.result-table th').forEach(th => {
            th.addEventListener('click', function() {
                const columnIndex = Array.from(this.parentNode.children).indexOf(this);
                const order = resultTable.order()[0];
                
                if (order && order[0] === columnIndex) {
                    // Show sort direction indicator
                    const direction = order[1] === 'asc' ? '↑' : '↓';
                    this.setAttribute('data-sort', direction);
                } else {
                    // Clear other indicators
                    document.querySelectorAll('.result-table th[data-sort]').forEach(header => {
                        header.removeAttribute('data-sort');
                    });
                }
            });
        });
    }
    
    function showMessage(message, type = 'info') {
        // Use the global showMessage function if available
        if (window.showAlert) {
            window.showAlert(message, type);
            return;
        }
        
        // Fallback implementation
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type}`;
        alertDiv.innerHTML = `<i class="fas fa-info-circle"></i> ${message}`;
        
        const container = document.querySelector('.main-container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            setTimeout(() => {
                alertDiv.style.opacity = '0';
                setTimeout(() => alertDiv.remove(), 300);
            }, 3000);
        }
    }
    
    // Utility functions
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Export table data functionality
    function exportTableData(format) {
        if (!resultTable) return;
        
        switch(format) {
            case 'excel':
                resultTable.button('.buttons-excel').trigger();
                break;
            case 'csv':
                resultTable.button('.buttons-csv').trigger();
                break;
            case 'copy':
                resultTable.button('.buttons-copy').trigger();
                break;
        }
    }
    
    // Auto-save search state
    window.addEventListener('beforeunload', function() {
        if (searchInput) {
            sessionStorage.setItem('lastSearch', searchInput.value);
        }
    });
    
    // Restore search state
    const lastSearch = sessionStorage.getItem('lastSearch');
    if (lastSearch && searchInput) {
        searchInput.value = lastSearch;
        handleSearch();
    }
    
    // Global exports
    window.ResultPage = {
        exportTableData: exportTableData,
        showMessage: showMessage,
        copyToClipboard: copyToClipboard,
        toggleTableVisibility: toggleTableVisibility
    };
});

// CSS for modal (add to result.css if not present)
const modalCSS = `
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0,0,0,0.5);
}

.modal-content {
    background-color: #fefefe;
    margin: 5% auto;
    padding: 0;
    border-radius: 15px;
    width: 80%;
    max-width: 600px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.3);
}

.modal-header {
    padding: 20px;
    background: linear-gradient(135deg, #667eea, #764ba2);
    color: white;
    border-radius: 15px 15px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-body {
    padding: 20px;
    max-height: 400px;
    overflow-y: auto;
}

.close {
    color: white;
    float: right;
    font-size: 28px;
    font-weight: bold;
    cursor: pointer;
}

.close:hover {
    opacity: 0.8;
}

.detail-item {
    margin-bottom: 10px;
    padding: 8px;
    border-bottom: 1px solid #eee;
}

.detail-item strong {
    display: inline-block;
    width: 150px;
    color: #495057;
}
`;

// Inject modal CSS
const style = document.createElement('style');
style.textContent = modalCSS;
document.head.appendChild(style);