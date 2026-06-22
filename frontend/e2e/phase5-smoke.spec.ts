import { expect, test } from '@playwright/test';

test.describe('Phase 5 public dashboard smoke', () => {
  test('searches a community, selects it, and downloads a non-empty report', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('community-search')).toBeVisible();

    await page.getByTestId('community-search').fill('Anchorage');
    await page.getByTestId('sidebar-search-result').first().click();
    await expect(page.getByRole('heading', { name: 'Anchorage' })).toBeVisible();

    const downloadPromise = page.waitForEvent('download');
    await page.getByTestId('download-report').click();
    const download = await downloadPromise;
    const stream = await download.createReadStream();

    expect(download.suggestedFilename().toLowerCase()).toContain('anchorage');
    if (!stream) {
      throw new Error('Expected PDF download stream');
    }

    let bytes = 0;
    await new Promise<void>((resolve, reject) => {
      stream.on('data', chunk => {
        bytes += chunk.length;
      });
      stream.on('end', resolve);
      stream.on('error', reject);
    });
    expect(bytes).toBeGreaterThan(0);
  });

  test('scenario controls update the modeled impact summary and shareable URL state', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('scenario-button').click();
    await expect(page.getByTestId('scenario-panel')).toBeVisible();

    await page.getByLabel('Download threshold').evaluate(element => {
      const input = element as HTMLInputElement;
      input.value = '75';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });

    await expect(page.getByTestId('scenario-summary')).toBeVisible();
    await expect(page).toHaveURL(/scenario=1/);
    await expect(page).toHaveURL(/bd=75/);

    await page.getByTestId('season-selector').selectOption('winter');
    await expect(page).toHaveURL(/season=winter/);
  });

  test('pinned communities open the comparison panel', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('community-search')).toBeVisible();

    await page.getByTestId('community-search').fill('Anchorage');
    await page.getByRole('button', { name: 'Pin Anchorage' }).click();

    await page.getByTestId('community-search').fill('Bethel');
    await page.getByRole('button', { name: 'Pin Bethel' }).click();

    await expect(page.getByTestId('comparison-panel')).toBeVisible();
    await expect(page.getByText('Community Comparison')).toBeVisible();
  });
});
