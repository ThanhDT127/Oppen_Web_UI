// Chart.js initialization and updates
import { formatTimestamp } from './utils.js';

export let costChart = null;
export let tokensChart = null;

// Initialize Chart.js charts
export function initCharts() {
    const chartConfig = {
        type: 'line',
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                },
                y: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: '#334155' }
                }
            }
        }
    };

    costChart = new Chart(
        document.getElementById('costChart').getContext('2d'),
        {
            ...chartConfig,
            data: {
                labels: [],
                datasets: [{
                    label: 'Cost (USD)',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            }
        }
    );

    tokensChart = new Chart(
        document.getElementById('tokensChart').getContext('2d'),
        {
            ...chartConfig,
            data: {
                labels: [],
                datasets: [{
                    label: 'Tokens',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            }
        }
    );
}

// Update charts with timeseries data from summary
export async function updateCharts(summaryData) {
    if (!summaryData || !summaryData.timeseries || !costChart || !tokensChart) {
        console.log('Charts not ready or no timeseries data available');
        return;
    }
    
    const timeseries = summaryData.timeseries;
    
    if (timeseries.length === 0) {
        // No data - show empty charts
        costChart.data.labels = [];
        costChart.data.datasets[0].data = [];
        costChart.update();
        
        tokensChart.data.labels = [];
        tokensChart.data.datasets[0].data = [];
        tokensChart.update();
        return;
    }
    
    // Extract labels and data from timeseries
    const labels = timeseries.map(bucket => {
        // Format timestamp for display (BE sends "ts" not "bucket_start")
        const date = new Date(bucket.ts);
        return date.toLocaleTimeString('en-US', { 
            hour: '2-digit', 
            minute: '2-digit',
            month: 'short',
            day: 'numeric'
        });
    });
    
    const costData = timeseries.map(bucket => bucket.cost_usd || 0);  // BE sends "cost_usd"
    const tokensData = timeseries.map(bucket => bucket.tokens_total || 0);
    
    // Update cost chart
    costChart.data.labels = labels;
    costChart.data.datasets[0].data = costData;
    costChart.update();
    
    // Update tokens chart
    tokensChart.data.labels = labels;
    tokensChart.data.datasets[0].data = tokensData;
    tokensChart.update();
}
