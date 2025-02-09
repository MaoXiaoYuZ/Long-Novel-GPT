export function fallbackCopyToClipboard(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    
    // Ensure textarea is outside the viewport
    textArea.style.position = 'fixed';
    textArea.style.left = '-999999px';
    textArea.style.top = '-999999px';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
    } catch (err) {
        console.error('Copy failed:', err);
        throw err;
    }
    
    document.body.removeChild(textArea);
}

export function copyToClipboard(text, onSuccess, onError) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text)
            .then(() => onSuccess && onSuccess())
            .catch(err => {
                console.error('Copy failed:', err);
                try {
                    fallbackCopyToClipboard(text);
                    onSuccess && onSuccess();
                } catch (err) {
                    onError && onError();
                }
            });
    } else {
        try {
            fallbackCopyToClipboard(text);
            onSuccess && onSuccess();
        } catch (err) {
            console.error('Clipboard API not supported');
            onError && onError();
        }
    }
} 