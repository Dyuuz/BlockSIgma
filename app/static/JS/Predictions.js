// Sample data for demonstration
const sampleData12hr = [
    {
        "asset_name": "1000CAT",
        "symbol": "1000CAT",
        "current_price": 0.00762,
        "price_at_predicted_time": 0.00928,
        "predicted_price": 0.00924992,
        "price_difference_currently": -17.888,
        "price_difference_at_predicted_time": -0.17,
        "current_status": false,
        "prediction_status": "Buy - Reached",
        "predicted_time": "July 23 25, 08:31 AM UTC+00",
        "expiry_time": "July 23 25, 08:31 PM UTC+00",
        "achievement": "Reached",
        "time_reached": "July 23 25, 08:36 AM UTC+00",
        "dynamic_tp": -0.153,
        "dynamic_sl": 12.834,
        "rrr": -0.01,
        "sl_status": false,
        "price_change_status": true
    },
    {
        "asset_name": "BTC",
        "symbol": "BTC",
        "current_price": 51234.56,
        "price_at_predicted_time": 52345.67,
        "predicted_price": 52500.00,
        "price_difference_currently": -2.1,
        "price_difference_at_predicted_time": -0.3,
        "current_status": true,
        "prediction_status": "Sell - Pending",
        "predicted_time": "July 24 25, 10:15 AM UTC+00",
        "expiry_time": "July 24 25, 10:15 PM UTC+00",
        "achievement": "Not Reached",
        "time_reached": null,
        "dynamic_tp": 1.5,
        "dynamic_sl": 8.2,
        "rrr": 0.18,
        "sl_status": false,
        "price_change_status": true
    },
    {
        "asset_name": "ETH",
        "symbol": "ETH",
        "current_price": 2987.65,
        "price_at_predicted_time": 3100.42,
        "predicted_price": 3125.00,
        "price_difference_currently": -4.2,
        "price_difference_at_predicted_time": -0.8,
        "current_status": true,
        "prediction_status": "Buy - Reached",
        "predicted_time": "July 22 25, 02:45 PM UTC+00",
        "expiry_time": "July 22 25, 02:45 AM UTC+00",
        "achievement": "Reached",
        "time_reached": "July 22 25, 03:10 PM UTC+00",
        "dynamic_tp": 2.1,
        "dynamic_sl": 6.7,
        "rrr": 0.31,
        "sl_status": false,
        "price_change_status": true
    },
    {
        "asset_name": "DOGE",
        "symbol": "DOGE",
        "current_price": 0.1234,
        "price_at_predicted_time": 0.1345,
        "predicted_price": 0.1350,
        "price_difference_currently": -8.2,
        "price_difference_at_predicted_time": -0.37,
        "current_status": false,
        "prediction_status": "Buy - Pending",
        "predicted_time": "July 25 25, 09:20 AM UTC+00",
        "expiry_time": "July 25 25, 09:20 PM UTC+00",
        "achievement": "Not Reached",
        "time_reached": null,
        "dynamic_tp": 1.2,
        "dynamic_sl": 9.5,
        "rrr": 0.13,
        "sl_status": false,
        "price_change_status": false
    }
];

const sampleData4hr = [
    {
        "asset_name": "1000CAT",
        "symbol": "1000CAT",
        "current_price": 0.00762,
        "price_at_predicted_time": 0.00781,
        "predicted_price": 0.00779802,
        "price_difference_currently": -2.433,
        "price_difference_at_predicted_time": -0.153,
        "current_status": false,
        "prediction_status": "No action",
        "predicted_time": "August 28 25, 02:42 AM UTC+00",
        "expiry_time": "August 28 25, 06:42 AM UTC+00",
        "achievement": "Reached",
        "time_reached": "August 29 25, 08:12 PM UTC+00",
        "interval": "4hr",
        "dynamic_tp": -0.138,
        "dynamic_sl": 1.402,
        "rrr": -0.1,
        "sl_status": false,
        "price_change_status": false
    },
    {
        "asset_name": "SOL",
        "symbol": "SOL",
        "current_price": 134.56,
        "price_at_predicted_time": 139.87,
        "predicted_price": 140.25,
        "price_difference_currently": -3.8,
        "price_difference_at_predicted_time": -0.27,
        "current_status": true,
        "prediction_status": "Buy - Pending",
        "predicted_time": "August 29 25, 04:30 AM UTC+00",
        "expiry_time": "August 29 25, 08:30 AM UTC+00",
        "achievement": "Not Reached",
        "time_reached": null,
        "interval": "4hr",
        "dynamic_tp": 1.8,
        "dynamic_sl": 5.3,
        "rrr": 0.34,
        "sl_status": false,
        "price_change_status": true
    },
    {
        "asset_name": "XRP",
        "symbol": "XRP",
        "current_price": 0.5678,
        "price_at_predicted_time": 0.5823,
        "predicted_price": 0.5841,
        "price_difference_currently": -2.5,
        "price_difference_at_predicted_time": -0.31,
        "current_status": false,
        "prediction_status": "Sell - Reached",
        "predicted_time": "August 27 25, 11:20 PM UTC+00",
        "expiry_time": "August 28 25, 03:20 AM UTC+00",
        "achievement": "Reached",
        "time_reached": "August 28 25, 12:05 AM UTC+00",
        "interval": "4hr",
        "dynamic_tp": -1.2,
        "dynamic_sl": 3.8,
        "rrr": -0.32,
        "sl_status": false,
        "price_change_status": true
    },
    {
        "asset_name": "ADA",
        "symbol": "ADA",
        "current_price": 0.4567,
        "price_at_predicted_time": 0.4678,
        "predicted_price": 0.4682,
        "price_difference_currently": -2.4,
        "price_difference_at_predicted_time": -0.09,
        "current_status": true,
        "prediction_status": "No action",
        "predicted_time": "August 30 25, 01:15 PM UTC+00",
        "expiry_time": "August 30 25, 05:15 PM UTC+00",
        "achievement": "Not Reached",
        "time_reached": null,
        "interval": "4hr",
        "dynamic_tp": 0.8,
        "dynamic_sl": 4.2,
        "rrr": 0.19,
        "sl_status": false,
        "price_change_status": false
    }
];

// DOM elements
const tabs = document.querySelectorAll('.tab');
const table12hr = document.getElementById('table-12hr');
const table4hr = document.getElementById('table-4hr');
const data12hr = document.getElementById('data-12hr');
const data4hr = document.getElementById('data-4hr');
const helpBtn = document.getElementById('helpBtn');
const helpModal = document.getElementById('helpModal');
const closeBtn = document.querySelector('.close-btn');
const searchInput = document.getElementById('searchInput');
const resetSearch = document.getElementById('resetSearch');
const refreshData = document.getElementById('refreshData');
const resultsInfo = document.getElementById('resultsInfo');
const refreshCountdown = document.getElementById('refreshCountdown');
const refreshIcon = document.getElementById('refreshIcon');
const predictionTimeLabel = document.getElementById('predictionTimeLabel');
const predictionTimeValue = document.getElementById('predictionTimeValue');
const expiryTimeLabel = document.getElementById('expiryTimeLabel');
const expiryTimeValue = document.getElementById('expiryTimeValue');

// State variables
let currentData12hr = [...sampleData12hr];
let currentData4hr = [...sampleData4hr];
let currentSortState12hr = {};
let currentSortState4hr = {};
let currentSearchTerm = '';
let refreshInterval;
let countdownInterval;
let countdown = 30;

// Initialize the dashboard
function initDashboard() {
    setupEventListeners();
    startAutoRefresh();
    fetchData();
    
    // Set initial prediction and expiry times for 12hr table
    updatePredictionTimes('12hr');
}

// Set up event listeners
function setupEventListeners() {
    // Tab switching
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            if (tab.dataset.tab === '12hr') {
                table12hr.style.display = 'block';
                table4hr.style.display = 'none';
                updateResultsInfo(currentData12hr, '12hr');
                updatePredictionTimes('12hr');
            } else {
                table12hr.style.display = 'none';
                table4hr.style.display = 'block';
                updateResultsInfo(currentData4hr, '4hr');
                updatePredictionTimes('4hr');
            }
        });
    });
    
    // Help modal functionality
    helpBtn.addEventListener('click', () => {
        helpModal.style.display = 'flex';
    });
    
    closeBtn.addEventListener('click', () => {
        helpModal.style.display = 'none';
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === helpModal) {
            helpModal.style.display = 'none';
        }
    });
    
    // Search functionality
    searchInput.addEventListener('input', (e) => {
        currentSearchTerm = e.target.value.toLowerCase().trim();
        performSearch();
    });
    
    // Reset search
    resetSearch.addEventListener('click', () => {
        searchInput.value = '';
        currentSearchTerm = '';
        performSearch();
    });
    
    // Refresh data
    refreshData.addEventListener('click', () => {
        manualRefresh();
    });
}

// Update prediction and expiry times based on active tab
function updatePredictionTimes(activeTab) {
    if (activeTab === '12hr') {
        predictionTimeLabel.textContent = "12hr Prediction Time:";
        expiryTimeLabel.textContent = "12hr Expiry Time:";
        // Use the first item's times as general times for the 12hr table
        predictionTimeValue.textContent = sampleData12hr[0].predicted_time;
        expiryTimeValue.textContent = sampleData12hr[0].expiry_time;
    } else {
        predictionTimeLabel.textContent = "4hr Prediction Time:";
        expiryTimeLabel.textContent = "4hr Expiry Time:";
        // Use the first item's times as general times for the 4hr table
        predictionTimeValue.textContent = sampleData4hr[0].predicted_time;
        expiryTimeValue.textContent = sampleData4hr[0].expiry_time;
    }
}

// Start auto-refresh timer
function startAutoRefresh() {
    // Clear any existing intervals
    clearInterval(refreshInterval);
    clearInterval(countdownInterval);
    
    // Reset countdown
    countdown = 30;
    refreshCountdown.textContent = countdown;
    
    // Start countdown timer
    countdownInterval = setInterval(() => {
        countdown--;
        refreshCountdown.textContent = countdown;
        
        if (countdown <= 0) {
            // Reset countdown
            countdown = 30;
            refreshCountdown.textContent = countdown;
            
            // Refresh data
            refreshDataNow();
        }
    }, 1000);
    
    // Start refresh interval (30 seconds)
    refreshInterval = setInterval(() => {
        refreshDataNow();
    }, 30000);
}

// Manual refresh triggered by user
function manualRefresh() {
    // Show refreshing animation
    refreshIcon.classList.add('refreshing');
    refreshCountdown.textContent = '0';
    
    // Refresh data
    refreshDataNow();
    
    // Restart the auto-refresh timer
    startAutoRefresh();
    
    // Remove animation after 1 second
    setTimeout(() => {
        refreshIcon.classList.remove('refreshing');
    }, 1000);
}

// Refresh data implementation
function refreshDataNow() {
    // Show loading state
    const activeTab = document.querySelector('.tab.active').dataset.tab;
    if (activeTab === '12hr') {
        data12hr.innerHTML = '<tr><td colspan="13"><div class="loading"><i class="fas fa-spinner fa-spin"></i>Refreshing data...</div></td></tr>';
    } else {
        data4hr.innerHTML = '<tr><td colspan="13"><div class="loading"><i class="fas fa-spinner fa-spin"></i>Refreshing data...</div></td></tr>';
    }
    
    // Simulate API call with slight data changes
    setTimeout(() => {
        // Create updated data with slight changes to simulate real-time updates
        const updatedData12hr = sampleData12hr.map(item => {
            const randomChange = (Math.random() - 0.5) * 0.1; // -5% to +5%
            return {
                ...item,
                current_price: item.current_price * (1 + randomChange),
                price_difference_currently: item.price_difference_currently * (1 + randomChange)
            };
        });
        
        const updatedData4hr = sampleData4hr.map(item => {
            const randomChange = (Math.random() - 0.5) * 0.1; // -5% to +5%
            return {
                ...item,
                current_price: item.current_price * (1 + randomChange),
                price_difference_currently: item.price_difference_currently * (1 + randomChange)
            };
        });
        
        // Update current data
        currentData12hr = [...updatedData12hr];
        currentData4hr = [...updatedData4hr];
        
        // Reapply search if there's an active search term
        if (currentSearchTerm) {
            performSearch();
        } else {
            // Reapply sorting
            if (Object.keys(currentSortState12hr).length > 0) {
                const key = Object.keys(currentSortState12hr)[0];
                currentData12hr = sortData([...updatedData12hr], key, currentSortState12hr[key]);
            }
            
            if (Object.keys(currentSortState4hr).length > 0) {
                const key = Object.keys(currentSortState4hr)[0];
                currentData4hr = sortData([...updatedData4hr], key, currentSortState4hr[key]);
            }
            
            // Render the updated data
            renderTableData(data12hr, currentData12hr);
            renderTableData(data4hr, currentData4hr);
        }
        
        // Update results info
        updateResultsInfo(activeTab === '12hr' ? currentData12hr : currentData4hr, activeTab);
    }, 800);
}

// Perform search across both tables
function performSearch() {
    if (!currentSearchTerm) {
        // If search is empty, show all data
        currentData12hr = [...sampleData12hr];
        currentData4hr = [...sampleData4hr];
        
        // Reapply sorting if needed
        if (Object.keys(currentSortState12hr).length > 0) {
            const key = Object.keys(currentSortState12hr)[0];
            currentData12hr = sortData([...sampleData12hr], key, currentSortState12hr[key]);
        }
        
        if (Object.keys(currentSortState4hr).length > 0) {
            const key = Object.keys(currentSortState4hr)[0];
            currentData4hr = sortData([...sampleData4hr], key, currentSortState4hr[key]);
        }
    } else {
        // Filter data based on search term
        currentData12hr = sampleData12hr.filter(item => 
            item.asset_name.toLowerCase().includes(currentSearchTerm) || 
            item.symbol.toLowerCase().includes(currentSearchTerm)
        );
        
        currentData4hr = sampleData4hr.filter(item => 
            item.asset_name.toLowerCase().includes(currentSearchTerm) || 
            item.symbol.toLowerCase().includes(currentSearchTerm)
        );
    }
    
    // Render the filtered data
    renderTableData(data12hr, currentData12hr);
    renderTableData(data4hr, currentData4hr);
    
    // Update results info
    const activeTab = document.querySelector('.tab.active').dataset.tab;
    updateResultsInfo(activeTab === '12hr' ? currentData12hr : currentData4hr, activeTab);
}

// Update results information
function updateResultsInfo(data, tableType) {
    const totalItems = tableType === '12hr' ? sampleData12hr.length : sampleData4hr.length;
    if (currentSearchTerm) {
        resultsInfo.textContent = `Showing ${data.length} of ${totalItems} results for "${currentSearchTerm}"`;
    } else {
        resultsInfo.textContent = `Showing all ${totalItems} results`;
    }
}

// Format number with commas and fixed decimals
function formatNumber(num, decimals = 4) {
    if (num === null || num === undefined) return 'N/A';
    return num.toLocaleString(undefined, {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}

// Format percentage
function formatPercentage(num) {
    if (num === null || num === undefined) return 'N/A';
    const value = num.toFixed(2);
    return `${num > 0 ? '+' : ''}${value}%`;
}

// Get status class
function getStatusClass(status) {
    if (status.includes('Buy')) return 'status-buy';
    if (status.includes('Sell')) return 'status-sell';
    return 'status-no-action';
}

// Render table data
function renderTableData(container, data) {
    if (!data || data.length === 0) {
        container.innerHTML = '<tr><td colspan="13" class="no-results">No matching results found</td></tr>';
        return;
    }
    
    container.innerHTML = '';
    
    data.forEach(item => {
        const row = document.createElement('tr');
        
        // Add achievement class if reached
        if (item.achievement === "Reached") {
            row.classList.add('achievement-reached');
        }
        
        row.innerHTML = `
            <td><strong>${item.asset_name}</strong><br><span style="color: #94a3b8; font-size: 0.9em;">${item.symbol}</span></td>
            <td>$${formatNumber(item.current_price)}</td>
            <td>$${formatNumber(item.predicted_price)}</td>
            <td><span class="value-change ${item.price_difference_currently < 0 ? 'negative' : 'positive'}">${formatPercentage(item.price_difference_currently)}</span></td>
            <td><span class="value-change ${item.price_difference_at_predicted_time < 0 ? 'negative' : 'positive'}">${formatPercentage(item.price_difference_at_predicted_time)}</span></td>
            <td><span class="${getStatusClass(item.prediction_status)}">${item.prediction_status}</span></td>
            <td>${item.predicted_time}</td>
            <td>${item.expiry_time}</td>
            <td><strong>${item.achievement}</strong></td>
            <td>${item.time_reached || 'N/A'}</td>
            <td><span class="${item.dynamic_tp < 0 ? 'negative' : 'positive'}">${formatPercentage(item.dynamic_tp)}</span></td>
            <td><span class="${item.dynamic_sl < 0 ? 'negative' : 'positive'}">${formatPercentage(item.dynamic_sl)}</span></td>
            <td><span class="${item.rrr < 0 ? 'negative' : 'positive'}">${formatNumber(item.rrr, 2)}</span></td>
        `;
        
        container.appendChild(row);
    });
}

// Sort data
function sortData(data, key, direction) {
    return [...data].sort((a, b) => {
        let valueA = a[key];
        let valueB = b[key];
        
        // Handle null/undefined values
        if (valueA === null || valueA === undefined) valueA = '';
        if (valueB === null || valueB === undefined) valueB = '';
        
        // Handle string comparison
        if (typeof valueA === 'string') {
            return direction === 'asc' 
                ? valueA.localeCompare(valueB)
                : valueB.localeCompare(valueA);
        }
        
        // Handle number comparison
        return direction === 'asc' ? valueA - valueB : valueB - valueA;
    });
}

// Initialize sort functionality
function initSorting(tableId, data, sortState) {
    const headers = document.querySelectorAll(`#${tableId} th`);
    let currentData = [...data];
    
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const key = header.dataset.sort;
            
            // Update sort state
            if (!sortState[key] || sortState[key] === 'desc') {
                sortState[key] = 'asc';
                header.querySelector('i').className = 'fas fa-sort-up';
            } else {
                sortState[key] = 'desc';
                header.querySelector('i').className = 'fas fa-sort-down';
            }
            
            // Reset other headers
            headers.forEach(h => {
                if (h !== header) {
                    h.querySelector('i').className = 'fas fa-sort';
                }
            });
            
            // Sort data and re-render
            currentData = sortData(data, key, sortState[key]);
            const container = tableId === 'table-12hr' ? data12hr : data4hr;
            renderTableData(container, currentData);
            
            // Update the current data reference
            if (tableId === 'table-12hr') {
                currentData12hr = currentData;
            } else {
                currentData4hr = currentData;
            }
            
            // Update results info
            const activeTab = document.querySelector('.tab.active').dataset.tab;
            updateResultsInfo(activeTab === '12hr' ? currentData12hr : currentData4hr, activeTab);
        });
    });
    
    return currentData;
}

// Simulate API fetch with timeout
function fetchData() {
    setTimeout(() => {
        // Render initial data
        renderTableData(data12hr, currentData12hr);
        renderTableData(data4hr, currentData4hr);
        
        // Initialize sorting
        currentData12hr = initSorting('table-12hr', currentData12hr, currentSortState12hr);
        currentData4hr = initSorting('table-4hr', currentData4hr, currentSortState4hr);
        
        // Update results info
        updateResultsInfo(currentData12hr, '12hr');
    }, 1000);
}

// Initialize the dashboard
initDashboard();