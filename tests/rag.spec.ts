/// <reference types="node" />
/**
 * Open WebUI RAG Benchmark Suite
 * Dynamically runs test cases from YAML definition
 */
import { test, expect } from '@playwright/test';
import * as path from 'path';
import * as dotenv from 'dotenv';
import { loadBenchmark, BenchmarkCase, normalizeUnits } from './utils/benchmark-loader';

// Load .env from project root
dotenv.config({ path: path.resolve(__dirname, '../.env') });

const ADMIN_EMAIL = process.env.TEST_ADMIN_EMAIL;
const ADMIN_PASSWORD = process.env.TEST_ADMIN_PASSWORD;
const TEST_MODEL = 'chat-deepseek-v4-flash';

// Load Benchmark Config
const benchmark = loadBenchmark(path.resolve(__dirname, 'fixtures/rag_benchmark.yaml'));

// Results accumulator
const results: any[] = [];

// Helper function to login
async function loginAsAdmin(page: any) {
    console.log('Checking login status...');
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // If we see the user menu or chat input, we are likely already logged in
    const userMenu = page.locator('#user-menu-button');
    const chatInput = page.locator('#chat-input');
    if (await userMenu.isVisible() || await chatInput.isVisible()) {
        console.log('Already logged in.');
        return;
    }

    console.log('Navigating to login page...');
    await page.goto('/auth');
    await page.waitForLoadState('networkidle');

    await page.getByPlaceholder(/email/i).fill(ADMIN_EMAIL!);
    await page.getByPlaceholder(/password/i).fill(ADMIN_PASSWORD!);
    await page.getByRole('button', { name: /sign in/i }).click();

    await page.waitForURL(url => !url.pathname.includes('/auth'), { timeout: 30000 });
    console.log('Login confirmed.');
}

// Helper to create a Knowledge Base
async function createKnowledgeBase(page: any, name: string) {
    console.log(`Creating Knowledge Base: ${name}`);
    await page.goto('/workspace/knowledge');
    await page.waitForLoadState('networkidle');
    
    const createBtn = page.getByRole('link', { name: /new knowledge/i }).first()
                        .or(page.getByRole('button', { name: /new knowledge/i }).first());
    await createBtn.waitFor({ state: 'visible', timeout: 15000 });
    await createBtn.click();

    await page.getByPlaceholder(/Name your knowledge base/i).fill(name);
    await page.getByPlaceholder(/Describe your knowledge base and objectives/i).fill('Benchmark Suite KB');

    const saveBtn = page.getByRole('button', { name: /Create Knowledge/i }).first();
    await saveBtn.click();
    
    await page.waitForURL(/.*\/workspace\/knowledge(\/.*)?$/, { timeout: 20000 });
}

// Helper to upload documents to KB
async function uploadFilesToKB(page: any, kbName: string, files: {path: string, type: string}[]) {
    console.log(`Uploading ${files.length} documents to ${kbName}`);
    
    const projectRoot = path.resolve(__dirname, '..');

    // Ensure we are in the KB view
    if (!page.url().match(/\/workspace\/knowledge\/[a-zA-Z0-9-]+/)) {
        await page.goto('/workspace/knowledge');
        await page.waitForLoadState('networkidle');
        const kbItem = page.getByRole('button').filter({ hasText: kbName }).first();
        await kbItem.click();
    }

    await page.waitForURL(/\/workspace\/knowledge\/[a-zA-Z0-9-]+/, { timeout: 15000 });
    await page.waitForLoadState('networkidle');

    for (const file of files) {
        const absolutePath = path.resolve(projectRoot, file.path);
        const fileName = path.basename(absolutePath);
        console.log(`Uploading: ${fileName} from ${absolutePath}`);

        const fileInput = page.locator('input[type="file"]');
        await fileInput.waitFor({ state: 'attached', timeout: 15000 });
        await fileInput.setInputFiles(absolutePath);

        // Wait for the document to appear in the list
        await page.getByText(fileName).first().waitFor({ state: 'visible', timeout: 60000 });
    }
}

// Helper to wait for indexing
async function waitForIndexing(page: any) {
    console.log('Waiting for indexing to complete...');
    await page.waitForTimeout(3000);
    
    const timeout = 180000; 
    const start = Date.now();
    let isIndexing = true;

    while (Date.now() - start < timeout && isIndexing) {
        const errorToast = page.locator('.toast, .notification, [role="alert"]').filter({ hasText: /error|failed|could not|limit/i }).first();
        if (await errorToast.isVisible()) {
            const errorMsg = await errorToast.innerText();
            throw new Error(`Indexing process failed with UI error: ${errorMsg}`);
        }

        const processingText = await page.locator('text=/pending|processing|uploading|indexing/i').count();
        const spinners = await page.locator('.animate-spin, svg.animate-spin').count();
        
        if (processingText === 0 && spinners === 0) {
            await page.waitForTimeout(3000);
            const checkAgainText = await page.locator('text=/pending|processing|uploading|indexing/i').count();
            if (checkAgainText === 0) {
                console.log('Indexing complete.');
                isIndexing = false;
            }
        } else {
            await page.waitForTimeout(5000);
        }
    }

    if (isIndexing) throw new Error('Indexing timed out after 3 minutes');
}

// Helper to delete KB
async function deleteKnowledgeBase(page: any, kbName: string) {
    if (page.isClosed()) return;
    try {
        console.log(`Deleting Knowledge Base: ${kbName}`);
        await page.goto('/workspace/knowledge');
        await page.waitForLoadState('networkidle');
        const kbItem = page.locator('div, tr').filter({ hasText: kbName }).first();
        if (await kbItem.count() > 0) {
            const menuBtn = kbItem.getByRole('button', { name: /more|options/i }).or(kbItem.locator('button')).last();
            await menuBtn.click();
            await page.getByRole('button', { name: /delete/i }).click();
            await page.getByRole('button', { name: /confirm|delete/i }).last().click();
            await page.waitForTimeout(1000);
        }
    } catch (e) {
        console.log(`Cleanup failed: ${e.message}`);
    }
}

test.describe('RAG Benchmark Suite', () => {
    
    test.beforeAll(async () => {
        if (!ADMIN_EMAIL || !ADMIN_PASSWORD) {
            throw new Error('TEST_ADMIN_EMAIL and TEST_ADMIN_PASSWORD must be set in .env');
        }
    });

    test.afterAll(async () => {
        console.log('\n================================================================');
        console.log(`BENCHMARK SUMMARY: ${benchmark.name}`);
        console.log('================================================================');
        console.table(results);
        console.log('================================================================\n');
    });

    for (const testCase of benchmark.cases) {
        test(`Benchmark Case [${testCase.id}]: ${testCase.title}`, async ({ page }) => {
            test.setTimeout(0); // Unlimited timeout for reranker
            
            const startTime = Date.now();
            let status = 'FAILED';
            let latency = 0;
            let citationVerified = false;
            let kbName = '';

            try {
                // 1. Login
                await loginAsAdmin(page);

                // 2. Setup KB
                kbName = `Bench_${testCase.id}_${Date.now()}`;
                await createKnowledgeBase(page, kbName);

                // 3. Upload and Index
                await uploadFilesToKB(page, kbName, testCase.files);
                await waitForIndexing(page);

                // 4. Query
                await page.goto('/');
                await page.waitForLoadState('networkidle');

                // Select Model
                const modelSelector = page.locator('#model-selector-0-button');
                if (await modelSelector.count() > 0) {
                    await modelSelector.click();
                    await page.keyboard.type(TEST_MODEL);
                    await page.waitForTimeout(1000);
                    const modelOption = page.getByText(TEST_MODEL, { exact: false }).last();
                    if (await modelOption.isVisible()) await modelOption.click();
                    else await page.keyboard.press('Enter');
                    await page.waitForTimeout(500);
                }

                // KB Selection (#)
                const chatInput = page.locator('#chat-input');
                await chatInput.waitFor({ state: 'visible' });
                await chatInput.click();
                await page.keyboard.type('#');
                const kbDropdownItem = page.locator('.mention-list, [role="listbox"]').getByText(kbName).first()
                                          .or(page.getByText(kbName, { exact: false }).last());
                await kbDropdownItem.waitFor({ state: 'visible' });
                await kbDropdownItem.click();

                // Send Question
                await chatInput.click();
                await page.keyboard.type(` ${testCase.question}`);
                const querySubmitTime = Date.now();
                await page.keyboard.press('Enter');

                // 5. Wait for Response
                console.log('Waiting for LLM response...');
                const actionButton = page.getByRole('button', { name: /^Copy$/i }).last().or(page.locator('button[aria-label="Copy"]').last());
                await actionButton.waitFor({ state: 'visible', timeout: 300000 });
                
                latency = Date.now() - querySubmitTime;

                // 6. Verify Content
                const messageContainer = page.locator('[id^="response-content-container"], .response-content').last();
                await messageContainer.waitFor({ state: 'visible' });
                const rawResponseText = await messageContainer.innerText();
                const responseText = normalizeUnits(rawResponseText);
                
                for (const keyword of testCase.expected.answer_contains) {
                    const normalizedKeyword = normalizeUnits(keyword);
                    expect(responseText).toMatch(new RegExp(normalizedKeyword, 'i'));
                }

                // 7. Verify Citations
                citationVerified = testCase.expected.source_contains.some(src => rawResponseText.includes(src)) ||
                                   (await page.locator('.assistant-message').last().locator('sup, .citation, .source-link').count() > 0);
                
                if (benchmark.defaults.require_citation) {
                    expect(citationVerified).toBeTruthy();
                }

                status = 'PASSED';
            } catch (error) {
                console.error(`Case ${testCase.id} failed:`, error.message);
                
                // Log detailed LLM response for failed cases
                try {
                    const messageContainer = page.locator('[id^="response-content-container"], .response-content').last();
                    if (await messageContainer.isVisible()) {
                        const responseText = await messageContainer.innerText();
                        console.error(`--- FULL LLM RESPONSE FOR FAILED CASE [${testCase.id}] ---`);
                        console.error(responseText);
                        console.error('---------------------------------------------------------');
                    }
                } catch (logError) {
                    console.error('Could not retrieve LLM response for logging.');
                }

                status = `FAILED: ${error.message.substring(0, 50)}`;
                throw error;
            } finally {
                if (kbName) {
                    await deleteKnowledgeBase(page, kbName);
                }
                results.push({
                    ID: testCase.id,
                    Title: testCase.title,
                    Status: status,
                    Latency: `${(latency/1000).toFixed(1)}s`,
                    Citation: citationVerified ? 'Yes' : 'No'
                });
            }
        });
    }
});
