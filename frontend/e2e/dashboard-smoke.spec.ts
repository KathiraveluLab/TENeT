import { stat } from 'node:fs/promises';
import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

async function setRangeValue(page: Page, label: string, value: string) {
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

  test('pinned communities open the comparison panel with aligned metrics and deltas', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('community-search')).toBeVisible();

    await page.getByTestId('community-search').fill('Anchorage');
    await page.getByRole('button', { name: 'Pin Anchorage' }).click();

    await page.getByTestId('community-search').fill('Bethel');
    await page.getByRole('button', { name: 'Pin Bethel' }).click();

    const comparisonPanel = page.getByTestId('comparison-panel');
    await expect(comparisonPanel).toBeVisible();
    await expect(comparisonPanel.getByText('Community Comparison')).toBeVisible();
    await expect(comparisonPanel.getByText('2 pinned communities')).toBeVisible();
    await expect(comparisonPanel.getByText('Telehealth status')).toBeVisible();
    await expect(comparisonPanel.getByText('Affordability')).toBeVisible();
    await expect(comparisonPanel.getByText('Clinic support')).toBeVisible();
    await expect(comparisonPanel.getByText('Download')).toBeVisible();
    await expect(comparisonPanel.getByText('Cost burden')).toBeVisible();
    await expect(comparisonPanel.getByText('Desert score')).toBeVisible();
    await expect(comparisonPanel.getByText(/vs group avg/).first()).toBeVisible();
  });

  test('shareable URL restores community selection, season, scenario thresholds, and pins', async ({ page }) => {
    await page.goto('/?region=AK-ANCHORAGE&season=winter&scenario=1&bd=75&pins=AK-ANCHORAGE,AK-BETHEL');

    await expect(page.getByRole('heading', { name: 'Anchorage' })).toBeVisible();
    await expect(page.getByTestId('season-selector')).toHaveValue('winter');
    await expect(page.getByTestId('scenario-panel')).toBeVisible();
    await expect(page.getByLabel('Download threshold')).toHaveValue('75');
    await expect(page.getByTestId('scenario-summary')).toBeVisible();

    const comparisonPanel = page.getByTestId('comparison-panel');
    await expect(comparisonPanel).toBeVisible();
    await expect(comparisonPanel.getByText('2 pinned communities')).toBeVisible();
    await expect(comparisonPanel.getByRole('button', { name: 'Select Anchorage' })).toBeVisible();
    await expect(comparisonPanel.getByRole('button', { name: 'Select Bethel' })).toBeVisible();
  });
});
