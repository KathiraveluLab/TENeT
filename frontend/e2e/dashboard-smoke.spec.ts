import { stat } from 'node:fs/promises';
import { expect, test } from '@playwright/test';

async function setRangeValue(page, label: string, value: string) {
  await page.getByLabel(label).evaluate((element, nextValue) => {
    const input = element as HTMLInputElement;
    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set;
    nativeSetter?.call(input, nextValue);
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }, value);
}

test.describe('Public dashboard smoke', () => {
  test('searches a community, selects it, and downloads a non-empty report', async ({ page }, testInfo) => {
    await page.goto('/');
    await expect(page.getByTestId('community-search')).toBeVisible();

    await page.getByTestId('community-search').fill('Anchorage');
    await page.getByTestId('sidebar-search-result').first().click();
    await expect(page.getByRole('heading', { name: 'Anchorage' })).toBeVisible();

    const downloadPromise = page.waitForEvent('download');
    await page.getByTestId('download-report').click();
    const download = await downloadPromise;
    const filename = download.suggestedFilename();

    expect(filename.toLowerCase()).toContain('anchorage');

    const outputPath = testInfo.outputPath(filename);
    await download.saveAs(outputPath);

    const { size } = await stat(outputPath);
    expect(size).toBeGreaterThan(0);
  });

  test('scenario controls update the modeled impact summary and shareable URL state', async ({ page }) => {
    await page.goto('/');
    await page.getByTestId('scenario-button').click();
    await expect(page.getByTestId('scenario-panel')).toBeVisible();

    await setRangeValue(page, 'Download threshold', '75');

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
