import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import Legend from './Legend';

describe('Legend', () => {
    it('renders discovery explanations for relevant metrics', () => {
        render(<Legend totalRegions={421} />);

        expect(screen.getByText('Discovery Legend')).toBeInTheDocument();
        expect(screen.getAllByText('Healthcare Desert Score').length).toBeGreaterThan(0);
        expect(screen.queryByText('Telehealth Status')).not.toBeInTheDocument();
        expect(screen.getByText('CAT Tiers')).toBeInTheDocument();
        expect(screen.getByText(/Tier 1:/i)).toBeInTheDocument();
        expect(screen.getByText(/Tier 2:/i)).toBeInTheDocument();
        expect(screen.getByText(/Tier 3:/i)).toBeInTheDocument();
        expect(screen.getByText(/Tier 4:/i)).toBeInTheDocument();
        expect(screen.queryByText(/FCC vs Ookla Gap/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Affordability Burden/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/Reliability/i)).not.toBeInTheDocument();
        expect(screen.getByText('421')).toBeInTheDocument();
    });

    it('includes accessible tooltip labels for plain-language definitions', () => {
        render(<Legend />);

        expect(screen.getByLabelText(/Healthcare Desert Score: A 0-100 need score/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/CAT Tier: Community Access Tier summarizes/i)).toBeInTheDocument();
    });

    it('opens on click and closes with Escape', () => {
        render(<Legend />);

        const trigger = screen.getByRole('button', { name: 'Open discovery legend' });
        const panel = document.querySelector('[role="region"][aria-label="Discovery legend"]') as HTMLElement;
        expect(panel).not.toBeVisible();

        fireEvent.click(trigger);
        expect(panel).toBeVisible();
        expect(trigger).toHaveAttribute('aria-expanded', 'true');

        fireEvent.keyDown(document, { key: 'Escape' });
        expect(panel).not.toBeVisible();
        expect(trigger).toHaveFocus();
    });
});
