# Ad Previewer Tool

A simple front-end tool that allows you to:
- Paste ad markup (HTML/JavaScript) for display ads
- Paste VAST tag URLs for video ads
- Preview the ads directly in the browser

## Features

- Toggle between display and video ad previews
- Render display ads with HTML/JavaScript
- Support for VAST tag URLs (basic implementation)
- Display ad dimensions and type information
- Sample ads for quick testing

## Running Locally

### Option 1: Using Node.js

If you have Node.js installed:

1. Open a terminal/command prompt
2. Navigate to the project directory
3. Run the server:
   ```
   node server.js
   ```
4. Open your browser and go to: http://localhost:3000

### Option 2: Using Python

If you have Python installed:

#### For Python 3:
```
python -m http.server 3000
```

#### For Python 2:
```
python -m SimpleHTTPServer 3000
```

Then open your browser and go to: http://localhost:3000

### Option 3: Using any local web server

You can use any local web server of your choice, such as:
- VS Code's Live Server extension
- XAMPP, WAMP, or MAMP
- Any other HTTP server that can serve static files

## Usage

1. Select the ad type (Display Ad or Video Ad (VAST))
2. Paste your ad markup or VAST tag URL in the text area
3. Click "Render Ad" to preview the ad
4. Use "Clear" to reset the preview
5. Try the sample ads using the green buttons

## Display Ad Example

```html
<div style="width:300px; height:250px; background-color:#007bff; color:white; display:flex; align-items:center; justify-content:center; font-weight:bold; border-radius:5px;">
    <div style="text-align:center;">
        <div style="font-size:24px;">SAMPLE AD</div>
        <div style="font-size:14px; margin-top:10px;">300x250 Display Banner</div>
    </div>
</div>
```

## VAST Tag Example

```
https://pubads.g.doubleclick.net/gampad/ads?sz=640x480&iu=/124319096/external/single_ad_samples&ciu_szs=300x250&impl=s&gdfp_req=1&env=vp&output=vast&unviewed_position_start=1&cust_params=deployment%3Ddevsite%26sample_ct%3Dlinear&correlator=
```

## Notes

- For full VAST support, you would typically need to integrate with a full VAST client library
- For security reasons, this tool uses basic isolation for display ads, but in a production environment, you would want to use iframes with proper sandboxing
- This is a development tool and not intended for production use

## Browser Compatibility

Tested on:
- Chrome (latest)
- Firefox (latest)
- Edge (latest)

## License

MIT # Trigger GitHub Actions build
 
