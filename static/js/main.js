document.addEventListener('DOMContentLoaded', function() {
    const convertBtn = document.getElementById('convertBtn');
    const threadUrl = document.getElementById('threadUrl');
    const loadingIndicator = document.getElementById('loadingIndicator');
    const errorAlert = document.getElementById('errorAlert');
    const resultCard = document.getElementById('resultCard');
    const threadText = document.getElementById('threadText');
    const copyBtn = document.getElementById('copyBtn');

    convertBtn.addEventListener('click', async function() {
        const url = threadUrl.value.trim();
        if (!url) {
            showError('Please enter a valid Twitter/X URL');
            return;
        }

        // Show loading, hide other elements
        loadingIndicator.classList.remove('d-none');
        errorAlert.classList.add('d-none');
        resultCard.classList.add('d-none');
        convertBtn.disabled = true;

        try {
            const response = await fetch('/process_thread', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url: url })
            });

            const data = await response.json();

            if (response.ok) {
                threadText.textContent = data.text;
                resultCard.classList.remove('d-none');
                if (data.cached) {
                    showError('Retrieved from cache', 'alert-info');
                }
            } else {
                showError(data.error || 'Failed to process thread');
            }
        } catch (error) {
            showError('An error occurred while processing the thread');
        } finally {
            loadingIndicator.classList.add('d-none');
            convertBtn.disabled = false;
        }
    });

    copyBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(threadText.textContent)
            .then(() => {
                copyBtn.textContent = 'Copied!';
                setTimeout(() => {
                    copyBtn.textContent = 'Copy Text';
                }, 2000);
            })
            .catch(() => {
                showError('Failed to copy text');
            });
    });

    function showError(message, className = 'alert-danger') {
        errorAlert.textContent = message;
        errorAlert.className = `alert mt-4 ${className}`;
        errorAlert.classList.remove('d-none');
    }
});
