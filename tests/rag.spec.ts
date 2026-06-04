/// <reference types="node" />
/**
 * Open WebUI RAG Functional Tests
 * Tests document upload, indexing, and RAG retrieval quality
 */
import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as dotenv from 'dotenv';

// Load .env from project root
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const ADMIN_EMAIL = process.env.TEST_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.TEST_ADMIN_PASSWORD;

console.log(`Using Test Email: ${ADMIN_EMAIL ? ADMIN_EMAIL.substring(0, 3) + '...' : 'UNDEFINED'}`);
const TEST_KB_NAME = `RAG_Test_${Date.now()}`;
const TEST_FILE_NAME = 'TCVN7722-2-3_2007_904224.docx';
const FIXTURES_DIR = path.resolve(__dirname, 'fixtures');
const TEST_FILE_PATH = path.join(FIXTURES_DIR, TEST_FILE_NAME);
const TEST_MODEL = 'chat-deepseek-v4-flash';
const LATENCY_THRESHOLD_MS = 15000;

// Helper function to login
async function loginAsAdmin(page: any) {
    console.log('Navigating to login page...');
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    // Fill credentials
    await page.getByPlaceholder(/email/i).fill(ADMIN_EMAIL);
    await page.getByPlaceholder(/password/i).fill(ADMIN_PASSWORD);

    console.log('Clicking sign in...');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for successful login URL transition
    await page.waitForURL(url => !url.pathname.includes('/auth'), { timeout: 30000 });
    console.log('Login successful, navigated to:', page.url());

    console.log('Login confirmed.');
}

// Helper to create a Knowledge Base
async function createKnowledgeBase(page: any, name: string) {
    console.log(`Creating Knowledge Base: ${name}`);
    await page.goto('/workspace/knowledge');
    await page.waitForLoadState('networkidle');
    
    // Click "New Knowledge" link (from snapshot)
    const createBtn = page.getByRole('link', { name: /new knowledge/i }).first();
    await createBtn.waitFor({ state: 'visible' });
    await createBtn.click();

    // Fill KB details using exact snapshot text
    await page.getByPlaceholder(/Name your knowledge base/i).fill(name);
    await page.getByPlaceholder(/Describe your knowledge base and objectives/i).fill('Automated Test KB');

    // Save/Create using exact snapshot text
    const saveBtn = page.getByRole('button', { name: /Create Knowledge/i }).first();
    await saveBtn.click();
    
    // Wait for redirect - it might go to the list or directly into the new KB
    await page.waitForURL(/.*\/workspace\/knowledge(\/.*)?$/, { timeout: 10000 });
}

// Helper to upload document to KB
async function uploadToKB(page: any, kbName: string, filePath: string) {
    console.log(`Uploading document to ${kbName}: ${path.basename(filePath)}`);
    
    // If not already in a specific KB view, navigate to it
    if (!page.url().match(/\/workspace\/knowledge\/[a-zA-Z0-9-]+/)) {
        await page.goto('/workspace/knowledge');
        await page.waitForLoadState('networkidle');
        
        // Find our KB in the list and click it
        const kbItem = page.getByRole('button').filter({ hasText: kbName }).first();
        await kbItem.click();
        await page.waitForLoadState('networkidle');
    }

    // Wait for the specific KB view to load
    await page.waitForURL(/\/workspace\/knowledge\/[a-zA-Z0-9-]+/, { timeout: 15000 });
    await page.waitForLoadState('networkidle');

    console.log('Looking for file input...');
    const fileInput = page.locator('input[type="file"]');
    
    // Try the direct file input approach first (fastest and most reliable)
    await fileInput.waitFor({ state: 'attached', timeout: 10000 });
    console.log('Found hidden file input, setting files directly...');
    await fileInput.setInputFiles(filePath);

    // Wait for the document to appear in the list by looking for its filename
    console.log(`Waiting for ${TEST_FILE_NAME} to appear in the UI...`);
    await page.getByText(TEST_FILE_NAME).first().waitFor({ state: 'visible', timeout: 45000 });
}

// Helper to wait for indexing
async function waitForIndexing(page: any) {
    console.log('Waiting for indexing to complete...');
    
    // 1. Give the UI a moment to register the upload and start indexing
    await page.waitForTimeout(2000);
    
    // 2. Wait up to 3 minutes for the status to clear
    const timeout = 180000; 
    const start = Date.now();
    let isIndexing = true;

    while (Date.now() - start < timeout && isIndexing) {
        // Look for common Open WebUI processing indicators near the file
        // Sometimes it's text like "Pending", "Processing", or a loading spinner
        const processingText = await page.locator('text=/pending|processing|uploading|indexing/i').count();
        const spinners = await page.locator('.animate-spin, svg.animate-spin').count();
        
        // Also check if the document has a success/ready indicator (e.g. file size appears, or green check)
        // This varies by version, but usually spinners disappear when done.
        
        if (processingText === 0 && spinners === 0) {
            // Need to double check because UI might flicker
            await page.waitForTimeout(2000);
            const checkAgainText = await page.locator('text=/pending|processing|uploading|indexing/i').count();
            const checkAgainSpinners = await page.locator('.animate-spin, svg.animate-spin').count();
            
            if (checkAgainText === 0 && checkAgainSpinners === 0) {
                console.log('Indexing indicators cleared. Assuming indexing is complete.');
                isIndexing = false;
            }
        } else {
            console.log(`Still indexing... (Text: ${processingText}, Spinners: ${spinners})`);
            await page.waitForTimeout(5000);
        }
    }

    if (isIndexing) {
        console.warn('Warning: Indexing wait timed out after 3 minutes. Proceeding anyway, but RAG may fail.');
    }
    
    // Final buffer before moving to chat
    await page.waitForTimeout(3000);
}

// Helper to delete KB
async function deleteKnowledgeBase(page: any, kbName: string) {
    if (page.isClosed()) return;
    
    try {
        console.log(`Deleting Knowledge Base: ${kbName}`);
        await page.goto('/workspace/knowledge');
        await page.waitForLoadState('networkidle');
        
        // Find KB item
        const kbItem = page.locator('div, tr').filter({ hasText: kbName }).first();
        if (await kbItem.count() > 0) {
            // Click menu/options
            const menuBtn = kbItem.getByRole('button', { name: /more|options/i }).or(kbItem.locator('button')).last();
            await menuBtn.click();
            
            const deleteBtn = page.getByRole('button', { name: /delete/i });
            await deleteBtn.click();
            
            // Confirm delete
            const confirmBtn = page.getByRole('button', { name: /confirm|delete/i }).last();
            await confirmBtn.click();
            await page.waitForTimeout(1000);
        }
    } catch (e) {
        console.log(`Cleanup of ${kbName} suppressed or failed: ${e.message}`);
    }
}

test.describe('RAG End-to-End Pipeline', () => {

    test('Full RAG Lifecycle: Create -> Upload -> Index -> Query', async ({ page }) => {
        // Increase timeout to 0 (unlimited) for this specific test because local reranking is very slow
        test.setTimeout(0);

        try {
            // 1. Login
            console.log('Logging in as admin...');
            await loginAsAdmin(page);
            console.log('Login successful.');

            // 2. Create Knowledge Base
            await createKnowledgeBase(page, TEST_KB_NAME);
            console.log('Knowledge Base created.');

            // 3. Upload Document
            await uploadToKB(page, TEST_KB_NAME, TEST_FILE_PATH);
            console.log('Document uploaded.');

            // 4. Wait for Indexing
            await waitForIndexing(page);

            // 5. Query and Verify
            console.log('Performing RAG query...');
            await page.goto('/');
            await page.waitForTimeout(3000);

            // Wait for chat to load
            await page.waitForLoadState('networkidle');

            // Select model if needed
            console.log('Selecting model...');
            const modelSelector = page.locator('#model-selector-0-button');
                                      
            if (await modelSelector.count() > 0) {
                await modelSelector.click();
                // Wait for dropdown and search input
                await page.waitForTimeout(500);
                
                // Type the model name to filter the list
                console.log(`Searching for model: ${TEST_MODEL}`);
                await page.keyboard.type(TEST_MODEL);
                await page.waitForTimeout(1000); // Wait for filtering

                // Press Enter to select the top result, or click the explicit match
                const modelOption = page.getByText(TEST_MODEL, { exact: false }).last();
                if (await modelOption.isVisible()) {
                    await modelOption.click();
                } else {
                    await page.keyboard.press('Enter');
                }
                await page.waitForTimeout(500);
            } else {
                console.log('Model selector not found, assuming model is already selected.');
            }

            // Type query using KB reference by typing # then selecting
            const chatInput = page.locator('#chat-input');
            
            // Wait for chat input to be ready
            await chatInput.waitFor({ state: 'visible', timeout: 15000 });
            await chatInput.click();

            // Type # to trigger knowledge selection
            console.log('Typing # to trigger knowledge selection...');
            await page.keyboard.type('#');
            
            // Wait for the dropdown and click our KB
            const kbDropdownItem = page.locator('.mention-list, [role="listbox"]').getByText(TEST_KB_NAME).first()
                                      .or(page.getByText(TEST_KB_NAME, { exact: false }).last()); // Fallback if no specific listbox
                                      
            await kbDropdownItem.waitFor({ state: 'visible', timeout: 10000 });
            await kbDropdownItem.click();

            // Now append the actual question
            const query = `Tiêu chuẩn TCVN 7722-2-3 : 2007 áp dụng cho những loại đèn điện nào và với mức điện áp tối đa là bao nhiêu?`;
            const startTime = Date.now();
            
            // Since we clicked a tag, focus might be lost, click again and type
            await chatInput.click();
            await page.keyboard.type(` ${query}`);
            
            console.log('Submitting query...');
            await page.keyboard.press('Enter');

            // Wait for response to finish generating
            // In Open WebUI, action buttons like "Copy" or "Edit" appear under the message AFTER generation is complete.
            // We use a 5-minute timeout because local reranker can take a long time.
            console.log('Waiting for response to complete (looking for message action buttons, timeout: 5 minutes)...');
            
            // Wait for the copy button of the last assistant message
            const actionButton = page.getByRole('button', { name: /^Copy$/i }).last().or(page.locator('button[aria-label="Copy"]').last());
            await actionButton.waitFor({ state: 'visible', timeout: 300000 });

            const endTime = Date.now();
            const latency = endTime - startTime;
            console.log(`RAG Query Latency: ${latency}ms`);

            // Extract text and verify
            // Based on DOM inspection: The text is inside <div id="response-content-container"> -> <ul dir="auto"> -> <li>
            const messageContainer = page.locator('[id^="response-content-container"], .response-content').last();
            
            // Wait for the text to actually be rendered and non-empty
            console.log('Extracting and verifying response text...');
            await expect(async () => {
                const text = await messageContainer.innerText();
                if (text.trim().length < 20) {
                    throw new Error('Response text is still empty or too short');
                }
            }).toPass({ timeout: 15000 });

            const responseText = await messageContainer.innerText();
            console.log(`\n--- LLM Response ---\n${responseText}\n--------------------\n`);

            // Check for ALL critical facts using flexible keywords (ensure coverage)
            const expectedFacts = [
                /chiếu sáng/i,
                /đường phố|công cộng/i,
                /đường hầm/i,
                /2,5\s*m/i,
                /1000\s*V/i
            ];

            for (const fact of expectedFacts) {
                expect(responseText).toMatch(fact);
            }

            console.log('All expected facts found in the response.');

            // Check for citations (Open WebUI uses <sup>, buttons, or just text like "1 Source")
            console.log('Verifying citations...');
            const hasCitationText = /source|trích dẫn/i.test(responseText) || responseText.includes(TEST_FILE_NAME);
            const citationElements = await page.locator('.assistant-message').last().locator('sup, .citation, .source-link, [data-testid="citation"], button:has-text("Source")').count();
            
            expect(hasCitationText || citationElements > 0).toBeTruthy();
            console.log('Citation verified successfully.');
        } finally {
            // Cleanup
            await deleteKnowledgeBase(page, TEST_KB_NAME);
        }
    });
});
