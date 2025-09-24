# Hawaii State Budget Explorer

This is a single-page application for exploring the Hawaii State Budget for Fiscal Year 2026. The application is designed to be embedded in Squarespace or hosted independently.

## Features

- Interactive department budget explorer
- Responsive design for all devices
- Interactive charts and data visualizations
- Client-side routing for smooth navigation
- Easy to deploy and maintain

## Deployment Options

### 1. GitHub Pages (Recommended)

1. Create a new GitHub repository
2. Push the contents of this folder to the `main` branch
3. Go to Repository Settings → Pages
4. Select "Deploy from branch" and choose `main`
5. Your site will be available at `https://[your-username].github.io/[repository-name]/`

### 2. Netlify (Easiest)

1. Drag and drop this folder to [Netlify Drop](https://app.netlify.com/drop)
2. Your site will be deployed instantly
3. Customize the site name in Netlify settings

### 3. Custom Hosting

1. Upload all files to your web server
2. Ensure your server is configured to serve `index.html` for all routes (SPA fallback)
3. Access your site at your domain

## Embedding in Squarespace

1. In your Squarespace editor, add a new "Code Block"
2. Paste the following code, replacing the URL with your deployment URL:

```html
<div id="budget-explorer">
  <iframe 
    src="https://your-deployment-url.com/" 
    style="width: 100%; border: none; min-height: 800px;"
    id="budget-iframe"
    onload="resizeIframe(this)">
  </iframe>
</div>

<script>
function resizeIframe(iframe) {
  function resize() {
    const height = iframe.contentWindow.document.documentElement.scrollHeight;
    iframe.style.height = height + 'px';
  }
  
  // Initial resize
  resize();
  
  // Listen for resize events from the iframe
  window.addEventListener('message', function(e) {
    if (e.data && e.data.type === 'setHeight') {
      iframe.style.height = e.data.height + 'px';
    }
  });
  
  // Optional: Handle window resize
  window.addEventListener('resize', function() {
    // Reset height to auto to get new content height
    iframe.style.height = 'auto';
    // Small delay to allow content to reflow
    setTimeout(resize, 100);
  });
}
</script>
```

## Development

1. Clone the repository
2. Start a local server (e.g., `python3 -m http.server 8000`)
3. Open `http://localhost:8000` in your browser

## Data Updates

To update the budget data:

1. Update the data in the `js/app.js` file
2. Update any chart configurations as needed
3. Deploy the updated files

## License

This project is open source and available under the MIT License.
