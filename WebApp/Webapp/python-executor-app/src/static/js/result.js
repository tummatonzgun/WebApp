document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggleTable');
    const tableSection = document.querySelector('.table-section');
    const searchInput = document.getElementById('searchInput');
    const controlsSection = document.getElementById('controlsSection');
    
    // Initialize basic functionality
    init();
    
    function init() {
        setupBasicEvents();
        if (tableSection) {
            showTable();
        }
        enhanceTable();
        showControls(); // แสดงช่องค้นหา
    }
    
    function setupBasicEvents() {
        // Toggle table button
        if (toggleBtn) {
            toggleBtn.addEventListener('click', function() {
                const isVisible = tableSection.style.display !== 'none';
                toggleTable(!isVisible);
            });
        }
        
        // Enhanced search with real-time feedback
        if (searchInput) {
            searchInput.addEventListener('input', debounce(simpleSearch, 300));
            searchInput.addEventListener('focus', function() {
                this.style.borderColor = '#007bff';
                this.style.boxShadow = '0 0 0 3px rgba(0,123,255,0.1)';
            });
            searchInput.addEventListener('blur', function() {
                this.style.borderColor = '#dee2e6';
                this.style.boxShadow = 'none';
            });
        }
        
        // Clear filters button
        const clearBtn = document.getElementById('clearFiltersBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', clearSearch);
        }
        
        // Row click for details
        const table = document.querySelector('.result-table');
        if (table) {
            table.addEventListener('click', function(e) {
                const row = e.target.closest('tr');
                if (row && row.parentElement.tagName === 'TBODY') {
                    selectRow(row);
                }
            });
        }
    }
    
    function showControls() {
        if (controlsSection) {
            controlsSection.style.display = 'block';
        }
    }
    
    function toggleTable(show) {
        if (!tableSection) return;
        
        if (show) {
            tableSection.style.display = 'block';
            tableSection.classList.add('active');
            if (controlsSection) {
                controlsSection.style.display = 'block';
            }
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> ซ่อนตาราง';
            }
        } else {
            tableSection.style.display = 'none';
            tableSection.classList.remove('active');
            if (controlsSection) {
                controlsSection.style.display = 'none';
            }
            if (toggleBtn) {
                toggleBtn.innerHTML = '<i class="fas fa-eye"></i> แสดงตาราง';
            }
        }
    }
    
    function showTable() {
        tableSection.style.display = 'block';
        tableSection.classList.add('active');
        if (controlsSection) {
            controlsSection.style.display = 'block';
        }
        if (toggleBtn) {
            toggleBtn.innerHTML = '<i class="fas fa-eye-slash"></i> ซ่อนตาราง';
        }
    }
    
    function enhanceTable() {
        const table = document.querySelector('.result-table');
        if (!table) return;
        
        // Make table responsive and scrollable
        table.style.width = '100%';
        table.style.tableLayout = 'auto';
        
        const tableArea = document.getElementById('tableArea');
        if (tableArea) {
            tableArea.style.overflowX = 'auto';
            tableArea.style.maxHeight = '600px';
            tableArea.style.overflowY = 'auto';
        }
        
        // Count rows and columns
        updateTableInfo();
        
        // Add hover effects
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.style.cursor = 'pointer';
        });
    }
    
    function updateTableInfo() {
        const table = document.querySelector('.result-table');
        if (!table) return;
        
        const rows = table.querySelectorAll('tbody tr');
        const cols = table.querySelectorAll('thead th');
        
        // Update info if elements exist
        const rowCount = document.getElementById('rowCount');
        const columnCount = document.getElementById('columnCount');
        
        if (rowCount) {
            rowCount.textContent = `ทั้งหมด ${rows.length} แถว`;
        }
        
        if (columnCount) {
            columnCount.textContent = `${cols.length} คอลัมน์`;
        }
    }
    
    function simpleSearch() {
        const searchTerm = searchInput.value.toLowerCase().trim();
        const rows = document.querySelectorAll('.result-table tbody tr');
        const totalRows = rows.length;
        let visibleCount = 0;
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const isMatch = !searchTerm || text.includes(searchTerm);
            
            if (isMatch) {
                row.style.display = '';
                visibleCount++;
                // Simple highlight
                if (searchTerm) {
                    highlightText(row, searchTerm);
                } else {
                    removeHighlight(row);
                }
            } else {
                row.style.display = 'none';
            }
        });
        
        // Update search result info
        updateSearchResult(searchTerm, visibleCount, totalRows);
    }
    
    function updateSearchResult(searchTerm, visibleCount, totalRows) {
        const searchResult = document.getElementById('searchResult');
        if (!searchResult) return;
        
        if (!searchTerm) {
            searchResult.textContent = 'กรุณาพิมพ์คำที่ต้องการค้นหา';
            searchResult.style.color = '#6c757d';
        } else if (visibleCount === 0) {
            searchResult.textContent = `ไม่พบข้อมูลที่ตรงกับ "${searchTerm}"`;
            searchResult.style.color = '#dc3545';
        } else {
            searchResult.textContent = `พบ ${visibleCount} รายการจาก ${totalRows} รายการทั้งหมด`;
            searchResult.style.color = '#28a745';
        }
    }
    
    function highlightText(row, term) {
        const cells = row.querySelectorAll('td');
        cells.forEach(cell => {
            let html = cell.innerHTML;
            // Remove old highlights
            html = html.replace(/<mark class="highlight">(.*?)<\/mark>/gi, '$1');
            // Add new highlights
            if (term) {
                const regex = new RegExp(`(${escapeRegExp(term)})`, 'gi');
                html = html.replace(regex, '<mark class="highlight">$1</mark>');
            }
            cell.innerHTML = html;
        });
    }
    
    function removeHighlight(row) {
        const highlights = row.querySelectorAll('.highlight');
        highlights.forEach(mark => {
            mark.outerHTML = mark.textContent;
        });
    }
    
    function clearSearch() {
        if (searchInput) {
            searchInput.value = '';
        }
        
        // Show all rows
        const rows = document.querySelectorAll('.result-table tbody tr');
        rows.forEach(row => {
            row.style.display = '';
            removeHighlight(row);
            row.classList.remove('selected');
        });
        
        // Reset search result
        const searchResult = document.getElementById('searchResult');
        if (searchResult) {
            searchResult.textContent = 'กรุณาพิมพ์คำที่ต้องการค้นหา';
            searchResult.style.color = '#6c757d';
        }
        
        showMessage('ล้างการค้นหาแล้ว');
    }
    
    function selectRow(row) {
        // Remove previous selection
        const selected = document.querySelector('.result-table tbody tr.selected');
        if (selected) {
            selected.classList.remove('selected');
        }
        
        // Add selection to current row
        row.classList.add('selected');
        
        // Show simple details
        showRowDetails(row);
    }
    
    function showRowDetails(row) {
        const cells = Array.from(row.cells);
        const headers = Array.from(document.querySelectorAll('.result-table th'));
        
        let details = '';
        cells.forEach((cell, index) => {
            if (headers[index]) {
                details += `${headers[index].textContent}: ${cell.textContent}\n`;
            }
        });
        
        // Show in modal
        showModal(details);
    }
    
    function showModal(content) {
        let modal = document.getElementById('detailModal');
        if (!modal) {
            modal = createSimpleModal();
        }
        
        modal.querySelector('.modal-body').textContent = content;
        modal.style.display = 'block';
        
        // Close handlers
        modal.querySelector('.close').onclick = () => modal.style.display = 'none';
        modal.onclick = (e) => {
            if (e.target === modal) modal.style.display = 'none';
        };
        
        // Close with Escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && modal.style.display === 'block') {
                modal.style.display = 'none';
            }
        });
    }
    
    function createSimpleModal() {
        const modal = document.createElement('div');
        modal.id = 'detailModal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>รายละเอียด</h3>
                    <span class="close">&times;</span>
                </div>
                <div class="modal-body"></div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    }
    
    function showMessage(message) {
        // Simple notification
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #007bff;
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 10000;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    // Utility functions
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }
    
    function escapeRegExp(string) {
        return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }
    
    // Export for global access
    window.ResultPage = {
        showMessage: showMessage,
        clearSearch: clearSearch
    };
});

// Enhanced CSS for search and highlighting
const simpleCSS = `
<style>
/* Search Container */
.search-container {
    margin-bottom: 20px;
}

#searchInput {
    width: 100%;
    padding: 12px 20px;
    border: 2px solid #dee2e6;
    border-radius: 8px;
    font-size: 16px;
    background: #f8f9fa;
    transition: all 0.3s ease;
    font-family: inherit;
}

#searchInput:focus {
    outline: none;
    border-color: #007bff;
    background: #fff;
    box-shadow: 0 0 0 3px rgba(0,123,255,0.1);
}

#searchInput::placeholder {
    color: #6c757d;
    font-style: italic;
}

.search-info {
    margin-top: 8px;
    font-size: 14px;
    text-align: center;
}

#searchResult {
    font-weight: 500;
}

/* Highlight */
.highlight {
    background: #fff3cd;
    color: #856404;
    padding: 2px 4px;
    border-radius: 3px;
    font-weight: bold;
    border: 1px solid #ffeaa7;
}

/* Table Selection */
.result-table tbody tr.selected {
    background: #e3f2fd !important;
    border-left: 4px solid #2196f3;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.result-table tbody tr:hover {
    background: #f5f5f5;
    transition: background 0.2s ease;
}

/* Modal */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    backdrop-filter: blur(2px);
}

.modal-content {
    background: white;
    margin: 10% auto;
    padding: 0;
    border-radius: 12px;
    width: 80%;
    max-width: 500px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    animation: modalSlide 0.3s ease;
}

@keyframes modalSlide {
    from {
        opacity: 0;
        transform: translateY(-30px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.modal-header {
    padding: 20px;
    background: #007bff;
    color: white;
    border-radius: 12px 12px 0 0;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-header h3 {
    margin: 0;
    font-size: 18px;
}

.modal-body {
    padding: 20px;
    white-space: pre-line;
    max-height: 300px;
    overflow-y: auto;
    line-height: 1.6;
}

.close {
    color: white;
    font-size: 24px;
    font-weight: bold;
    cursor: pointer;
    line-height: 1;
    padding: 5px;
    border-radius: 4px;
    transition: background 0.2s ease;
}

.close:hover {
    background: rgba(255,255,255,0.2);
}

/* Table Area */
#tableArea {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.result-table {
    margin: 0;
    width: 100%;
}

.result-table th {
    background: #f8f9fa;
    color: #495057;
    font-weight: 600;
    padding: 12px;
    border-bottom: 2px solid #dee2e6;
    position: sticky;
    top: 0;
    white-space: nowrap;
}

.result-table td {
    padding: 10px 12px;
    border-bottom: 1px solid #dee2e6;
    white-space: nowrap;
}

.result-table tbody tr:nth-child(even) {
    background: #f9f9f9;
}

/* Animations */
@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(100px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes slideOut {
    from {
        opacity: 1;
        transform: translateX(0);
    }
    to {
        opacity: 0;
        transform: translateX(100px);
    }
}

/* Responsive */
@media (max-width: 768px) {
    .controls-header {
        flex-direction: column;
        text-align: center;
    }
    
    .modal-content {
        width: 95%;
        margin: 5% auto;
    }
    
    #searchInput {
        font-size: 16px; /* Prevent zoom on iOS */
    }
}
</style>
`;

document.head.insertAdjacentHTML('beforeend', simpleCSS);