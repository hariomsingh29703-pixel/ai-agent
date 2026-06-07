const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function runTest() {
  console.log('🚀 Starting Playwright test...');
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // 1. Navigate to signup
    console.log('Navigating to signup page...');
    await page.goto('http://localhost:3010/signup');
    await page.waitForLoadState('networkidle');

    // 2. Fill registration details
    const timestamp = Date.now();
    const testEmail = `testuser_${timestamp}@example.com`;
    console.log(`Registering new user with email: ${testEmail}`);
    
    await page.fill('#firstName', 'Test');
    await page.fill('#lastName', 'User');
    await page.fill('#email', testEmail);
    await page.fill('#password', 'Password123!');
    await page.fill('#confirmPassword', 'Password123!');
    await page.check('#terms');
    
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ url: '**/onboarding' })
    ]);
    console.log('✓ Registered successfully! Redirected to onboarding.');

    // 3. Fill onboarding form
    await page.fill('#goals', 'Automated test of the AI Agent skill');
    await Promise.all([
      page.click('button[type="submit"]'),
      page.waitForNavigation({ url: 'http://localhost:3010/' })
    ]);
    console.log('✓ Onboarding completed! Redirected to dashboard.');

    // 4. Grant permissions in the overlay modal
    console.log('Waiting for permission overlay modal...');
    await page.waitForSelector('#perm-overlay');
    
    // Toggle both files and terminal permissions
    console.log('Activating files and terminal permissions...');
    await page.click('#toggle-files');
    await page.click('#toggle-terminal');
    
    // Click "Grant Selected ✓"
    await page.click('.btn-primary:has-text("Grant Selected")');
    await page.waitForSelector('#perm-overlay', { state: 'hidden' });
    console.log('✓ Permissions granted successfully.');

    // Get session/workspace path info from workspace path element
    const wsPathText = await page.textContent('#ws-path');
    console.log(`✓ Workspace path: ${wsPathText}`);

    // 5. Send chat message to AI Agent
    const testPrompt = "Write a python file named hello_world.py that prints 'Hello from Antigravity test!' and save it";
    console.log(`Sending message to AI agent: "${testPrompt}"`);
    await page.fill('#user-input', testPrompt);
    await page.click('#send-btn');

    // Wait for the agent to finish thinking (spinner disappears and send button is enabled)
    console.log('Waiting for AI agent to respond (this might take a few seconds)...');
    await page.waitForSelector('#loading', { state: 'hidden', timeout: 60000 });
    await page.waitForSelector('#send-btn:enabled', { timeout: 60000 });
    console.log('✓ AI agent finished execution.');

    // Print all chat messages
    const messages = await page.locator('.msg').allInnerTexts();
    console.log('\n--- Chat History ---');
    messages.forEach(msg => console.log(msg));
    console.log('--------------------\n');

    // 6. Verify the file listed in the workspace panel
    console.log('Verifying workspace file list in the UI...');
    await page.waitForSelector('.f-item:has-text("hello_world.py")', { timeout: 10000 });
    console.log('✓ "hello_world.py" is visible in the UI workspace panel.');

    // Take screenshot of final state
    const screenshotsDir = path.join(__dirname, 'screenshots');
    if (!fs.existsSync(screenshotsDir)) {
      fs.mkdirSync(screenshotsDir, { recursive: true });
    }
    const screenshotPath = path.join(screenshotsDir, 'test_final.png');
    await page.screenshot({ path: screenshotPath });
    console.log(`✓ Final screenshot saved to ${screenshotPath}`);

    // 7. Verify the file exists on disk
    console.log('Checking physical file existence on disk...');
    // Since workspace is per session inside the workspace/session_* directory
    const wsFilesDir = path.join(__dirname, 'workspace');
    const sessions = fs.readdirSync(wsFilesDir).filter(f => f.startsWith('session_'));
    
    let fileFound = false;
    for (const sessionDir of sessions) {
      const filePath = path.join(wsFilesDir, sessionDir, 'hello_world.py');
      if (fs.existsSync(filePath)) {
        const fileContent = fs.readFileSync(filePath, 'utf-8');
        console.log(`✓ Found file at ${filePath}`);
        console.log(`File Content:\n${fileContent}`);
        fileFound = true;
        break;
      }
    }

    if (fileFound) {
      console.log('🎉 ALL TESTS PASSED SUCCESSFULLY! The application works perfectly.');
    } else {
      throw new Error('hello_world.py was not found on disk in any session folder!');
    }

  } catch (error) {
    console.error('❌ Test failed with error:', error);
    try {
      const errorScreenshot = path.join(__dirname, 'screenshots', 'error.png');
      await page.screenshot({ path: errorScreenshot });
      console.log(`Saved failure screenshot to ${errorScreenshot}`);
    } catch (e) {
      console.error('Could not take failure screenshot:', e);
    }
    process.exit(1);
  } finally {
    await browser.close();
  }
}

runTest();
