document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.share').forEach(button => {
        button.addEventListener('click', async () => {
            const url = button.getAttribute('data-url');
            if (navigator.share) {
                try {
                    await navigator.share({
                        title: 'Check out this awesome page!',
                        text: 'Here is a cool page you should see:',
                        url: url
                    });
                    console.log('Page shared successfully');
                } catch (error) {
                    console.error('Error sharing:', error);
                }
            } else {
                navigator.clipboard.writeText(url).then(() => {
                    console.log('URL copied successfully');
                }).catch(err => {
                    console.error('Failed to copy URL: ', err);
                });
            }
        });
    });
});