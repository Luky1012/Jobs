// Main JavaScript for LinkedIn Job Application Automation

// Initialize tooltips and popovers
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    var popoverList = popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
});

// Match score visualization
function initMatchScoreCharts() {
    var matchScoreElements = document.querySelectorAll('.match-score-chart');
    
    matchScoreElements.forEach(function(element) {
        var score = parseInt(element.getAttribute('data-score'));
        var ctx = element.getContext('2d');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [score, 100 - score],
                    backgroundColor: [
                        getScoreColor(score),
                        '#e0e0e0'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: '80%',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        enabled: false
                    },
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // Add score text in the center
        var scoreText = document.createElement('div');
        scoreText.className = 'match-score-text';
        scoreText.textContent = score + '%';
        scoreText.style.position = 'absolute';
        scoreText.style.top = '50%';
        scoreText.style.left = '50%';
        scoreText.style.transform = 'translate(-50%, -50%)';
        scoreText.style.fontSize = '16px';
        scoreText.style.fontWeight = 'bold';
        
        element.parentNode.style.position = 'relative';
        element.parentNode.appendChild(scoreText);
    });
}

// Get color based on score
function getScoreColor(score) {
    if (score >= 90) {
        return '#5CB85C'; // Excellent - Green
    } else if (score >= 70) {
        return '#00A0DC'; // Good - LinkedIn Blue
    } else if (score >= 50) {
        return '#F5A623'; // Fair - Orange
    } else {
        return '#D64242'; // Poor - Red
    }
}

// Initialize dashboard charts
function initDashboardCharts() {
    var applicationChartElement = document.getElementById('applicationChart');
    if (applicationChartElement) {
        var dates = JSON.parse(applicationChartElement.getAttribute('data-dates'));
        var counts = JSON.parse(applicationChartElement.getAttribute('data-counts'));
        
        new Chart(applicationChartElement, {
            type: 'line',
            data: {
                labels: dates,
                datasets: [{
                    label: 'Applications',
                    data: counts,
                    backgroundColor: 'rgba(0, 119, 181, 0.2)',
                    borderColor: '#0077B5',
                    borderWidth: 2,
                    tension: 0.3,
                    pointBackgroundColor: '#0077B5'
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    }
    
    var matchDistributionElement = document.getElementById('matchDistributionChart');
    if (matchDistributionElement) {
        var excellent = parseInt(matchDistributionElement.getAttribute('data-excellent'));
        var good = parseInt(matchDistributionElement.getAttribute('data-good'));
        var fair = parseInt(matchDistributionElement.getAttribute('data-fair'));
        var poor = parseInt(matchDistributionElement.getAttribute('data-poor'));
        
        new Chart(matchDistributionElement, {
            type: 'pie',
            data: {
                labels: ['Excellent (90%+)', 'Good (70-89%)', 'Fair (50-69%)', 'Poor (<50%)'],
                datasets: [{
                    data: [excellent, good, fair, poor],
                    backgroundColor: [
                        '#5CB85C',
                        '#00A0DC',
                        '#F5A623',
                        '#D64242'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

// Wizard form validation
function validateWizardForm(formId) {
    var form = document.getElementById(formId);
    if (!form) return true;
    
    if (!form.checkValidity()) {
        event.preventDefault();
        event.stopPropagation();
        form.classList.add('was-validated');
        return false;
    }
    
    return true;
}

// LinkedIn profile analysis
function analyzeProfile() {
    var analyzeButton = document.getElementById('analyzeProfileBtn');
    var progressBar = document.getElementById('analysisProgress');
    var resultContainer = document.getElementById('analysisResults');
    
    if (!analyzeButton || !progressBar || !resultContainer) return;
    
    analyzeButton.disabled = true;
    progressBar.style.width = '0%';
    progressBar.parentElement.classList.remove('d-none');
    resultContainer.classList.add('d-none');
    
    // Simulate analysis progress
    var progress = 0;
    var interval = setInterval(function() {
        progress += 5;
        progressBar.style.width = progress + '%';
        progressBar.setAttribute('aria-valuenow', progress);
        
        if (progress >= 100) {
            clearInterval(interval);
            setTimeout(function() {
                progressBar.parentElement.classList.add('d-none');
                resultContainer.classList.remove('d-none');
                analyzeButton.disabled = false;
            }, 500);
        }
    }, 200);
    
    // In a real implementation, this would make an AJAX call to the server
    fetch('/grok/analyze-profile', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        // Handle response
        console.log('Profile analysis complete', data);
    })
    .catch(error => {
        console.error('Error analyzing profile:', error);
        analyzeButton.disabled = false;
        progressBar.parentElement.classList.add('d-none');
    });
}

// Job matching
function matchJob(jobId) {
    var matchButton = document.getElementById('matchJobBtn-' + jobId);
    if (!matchButton) return;
    
    matchButton.disabled = true;
    matchButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Matching...';
    
    // In a real implementation, this would make an AJAX call to the server
    fetch('/grok/match-job', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_id: jobId })
    })
    .then(response => response.json())
    .then(data => {
        // Handle response
        console.log('Job matching complete', data);
        window.location.reload();
    })
    .catch(error => {
        console.error('Error matching job:', error);
        matchButton.disabled = false;
        matchButton.innerHTML = 'Retry Match';
    });
}

// Apply to job
function applyToJob(jobId) {
    var applyButton = document.getElementById('applyJobBtn-' + jobId);
    if (!applyButton) return;
    
    applyButton.disabled = true;
    applyButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Applying...';
    
    // In a real implementation, this would make an AJAX call to the server
    fetch('/grok/apply-job', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ job_id: jobId })
    })
    .then(response => response.json())
    .then(data => {
        // Handle response
        console.log('Job application complete', data);
        window.location.reload();
    })
    .catch(error => {
        console.error('Error applying to job:', error);
        applyButton.disabled = false;
        applyButton.innerHTML = 'Retry Application';
    });
}

// Initialize page-specific functions
document.addEventListener('DOMContentLoaded', function() {
    // Initialize match score charts if they exist
    if (document.querySelector('.match-score-chart')) {
        initMatchScoreCharts();
    }
    
    // Initialize dashboard charts if they exist
    if (document.getElementById('applicationChart') || document.getElementById('matchDistributionChart')) {
        initDashboardCharts();
    }
    
    // Initialize profile analysis button if it exists
    var analyzeButton = document.getElementById('analyzeProfileBtn');
    if (analyzeButton) {
        analyzeButton.addEventListener('click', analyzeProfile);
    }
    
    // Initialize job match buttons
    document.querySelectorAll('[id^="matchJobBtn-"]').forEach(function(button) {
        var jobId = button.id.replace('matchJobBtn-', '');
        button.addEventListener('click', function() {
            matchJob(jobId);
        });
    });
    
    // Initialize job apply buttons
    document.querySelectorAll('[id^="applyJobBtn-"]').forEach(function(button) {
        var jobId = button.id.replace('applyJobBtn-', '');
        button.addEventListener('click', function() {
            applyToJob(jobId);
        });
    });
});
