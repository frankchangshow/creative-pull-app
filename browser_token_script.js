// Browser Token Extraction Script
// Run this in your browser console while on Savanna

console.log("🔍 Starting browser token extraction...");

function extractTokenFromBrowser() {
    console.log("📋 Checking localStorage...");
    
    // Check localStorage for tokens
    const localStorageKeys = Object.keys(localStorage);
    console.log("localStorage keys:", localStorageKeys);
    
    for (const key of localStorageKeys) {
        const value = localStorage.getItem(key);
        if (value && value.startsWith('eyJ') && value.length > 100) {
            console.log(`✅ Found JWT token in localStorage.${key}:`, value.substring(0, 50) + "...");
            return value;
        }
    }
    
    console.log("📋 Checking sessionStorage...");
    
    // Check sessionStorage for tokens
    const sessionStorageKeys = Object.keys(sessionStorage);
    console.log("sessionStorage keys:", sessionStorageKeys);
    
    for (const key of sessionStorageKeys) {
        const value = sessionStorage.getItem(key);
        if (value && value.startsWith('eyJ') && value.length > 100) {
            console.log(`✅ Found JWT token in sessionStorage.${key}:`, value.substring(0, 50) + "...");
            return value;
        }
    }
    
    console.log("📋 Checking cookies...");
    
    // Check cookies for tokens
    const cookies = document.cookie.split(';');
    for (const cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (value && value.startsWith('eyJ') && value.length > 100) {
            console.log(`✅ Found JWT token in cookie ${name}:`, value.substring(0, 50) + "...");
            return value;
        }
    }
    
    console.log("📋 Checking page content for tokens...");
    
    // Look for tokens in the page HTML
    const pageText = document.documentElement.outerHTML;
    const jwtPattern = /eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*/g;
    const matches = pageText.match(jwtPattern);
    
    if (matches) {
        for (const match of matches) {
            if (match.length > 100) {
                console.log("✅ Found JWT token in page content:", match.substring(0, 50) + "...");
                return match;
            }
        }
    }
    
    console.log("📋 Checking for token in JavaScript variables...");
    
    // Try to access common token variables
    try {
        if (window.accessToken && window.accessToken.startsWith('eyJ')) {
            console.log("✅ Found accessToken in window:", window.accessToken.substring(0, 50) + "...");
            return window.accessToken;
        }
        
        if (window.token && window.token.startsWith('eyJ')) {
            console.log("✅ Found token in window:", window.token.substring(0, 50) + "...");
            return window.token;
        }
        
        if (window.bearerToken && window.bearerToken.startsWith('eyJ')) {
            console.log("✅ Found bearerToken in window:", window.bearerToken.substring(0, 50) + "...");
            return window.bearerToken;
        }
        
        // Check for tokens in common frameworks
        if (window.angular && window.angular.element && window.angular.element(document.body).scope()) {
            const scope = window.angular.element(document.body).scope();
            if (scope.accessToken && scope.accessToken.startsWith('eyJ')) {
                console.log("✅ Found accessToken in Angular scope:", scope.accessToken.substring(0, 50) + "...");
                return scope.accessToken;
            }
        }
        
        if (window.Vue && window.Vue.prototype && window.Vue.prototype.$store) {
            const store = window.Vue.prototype.$store;
            if (store.state && store.state.auth && store.state.auth.token) {
                const token = store.state.auth.token;
                if (token.startsWith('eyJ')) {
                    console.log("✅ Found token in Vue store:", token.substring(0, 50) + "...");
                    return token;
                }
            }
        }
        
    } catch (e) {
        console.log("⚠️ Error checking JavaScript variables:", e.message);
    }
    
    console.log("📋 Checking for tokens in script tags...");
    
    // Look for tokens in script tags
    const scripts = document.querySelectorAll('script');
    for (const script of scripts) {
        if (script.textContent) {
            const jwtPattern = /eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*/g;
            const matches = script.textContent.match(jwtPattern);
            if (matches) {
                for (const match of matches) {
                    if (match.length > 100) {
                        console.log("✅ Found JWT token in script tag:", match.substring(0, 50) + "...");
                        return match;
                    }
                }
            }
        }
    }
    
    console.log("❌ No JWT token found in browser storage");
    return null;
}

function checkTokenValidity(token) {
    if (!token) return false;
    
    try {
        // Decode JWT payload
        const parts = token.split('.');
        if (parts.length !== 3) return false;
        
        const payload = JSON.parse(atob(parts[1]));
        const now = Math.floor(Date.now() / 1000);
        
        console.log("🔍 Token details:");
        console.log("   Issued at:", new Date(payload.iat * 1000));
        console.log("   Expires at:", new Date(payload.exp * 1000));
        console.log("   User:", payload.user);
        console.log("   Roles:", payload.roles);
        
        if (payload.exp && payload.exp > now) {
            console.log("✅ Token is valid!");
            return true;
        } else {
            console.log("⚠️ Token is expired!");
            return false;
        }
        
    } catch (e) {
        console.log("❌ Error checking token validity:", e.message);
        return false;
    }
}

// Main execution
console.log("🚀 Starting token extraction...");

const token = extractTokenFromBrowser();

if (token) {
    console.log("\n🎉 TOKEN FOUND!");
    console.log("Token:", token);
    console.log("\n📋 Copy this token to use in your app!");
    
    // Check if token is valid
    checkTokenValidity(token);
    
    // Make token easily copyable
    console.log("\n📋 COPY-PASTE READY:");
    console.log("=".repeat(50));
    console.log(token);
    console.log("=".repeat(50));
    
} else {
    console.log("\n❌ No token found");
    console.log("\n💡 Try these steps:");
    console.log("1. Refresh the Savanna page");
    console.log("2. Navigate to a different page and back");
    console.log("3. Check if you're fully logged in");
    console.log("4. Look for any login prompts");
}

console.log("\n✨ Token extraction complete!");

