import jsPDF from 'jspdf';
import { ResearchProfile } from '../types/research';
import { DATA_UNAVAILABLE, formatResearchValue, formatStatusText } from './formatResearchValue';
import { telehealthNeedLabel } from '../components/sidebar/sidebarUtils';

const PAGE_WIDTH = 210;
const PAGE_HEIGHT = 297;
const MARGIN = 14;
const CONTENT_WIDTH = PAGE_WIDTH - MARGIN * 2;

const INK = '#151827';
const MUTED = '#6b7280';
const LINE = '#d7dde6';
const ROW = '#f8fafc';
const LABEL_BG = '#f0f2f5';
const BRAND = '#1d2848';
const GREEN = '#dff3e7';
const GREEN_TEXT = '#17643a';
const AMBER = '#fff3cf';
const AMBER_TEXT = '#8a5a00';
const RED = '#fee2e2';
const RED_TEXT = '#9f1239';
const BLUE = '#e7efff';
const BLUE_TEXT = '#1d4ed8';

type Tone = 'good' | 'warn' | 'bad' | 'neutral';

interface ReportRow {
    label: string;
    value: string;
    tone?: Tone;
}

function rgb(hex: string): [number, number, number] {
    const value = hex.replace('#', '');
    return [
        Number.parseInt(value.slice(0, 2), 16),
        Number.parseInt(value.slice(2, 4), 16),
        Number.parseInt(value.slice(4, 6), 16),
    ];
}

function setFill(pdf: jsPDF, color: string) {
    const [r, g, b] = rgb(color);
    pdf.setFillColor(r, g, b);
}

function setDraw(pdf: jsPDF, color: string) {
    const [r, g, b] = rgb(color);
    pdf.setDrawColor(r, g, b);
}

function setText(pdf: jsPDF, color: string) {
    const [r, g, b] = rgb(color);
    pdf.setTextColor(r, g, b);
}

function fileSafe(value: string) {
    return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function clean(value: string | number | boolean | null | undefined): string {
    const formatted = formatResearchValue(value);
    if (!formatted || formatted === 'null' || formatted === 'undefined' || formatted === 'NaN') {
        return DATA_UNAVAILABLE;
    }
    return formatted;
}

function safeText(value: string | number | boolean | null | undefined): string {
    if (value === null || value === undefined || value === '') return DATA_UNAVAILABLE;
    if (typeof value === 'number' && !Number.isFinite(value)) return DATA_UNAVAILABLE;
    return String(value);
}

function safeJoin(values: string[]): string {
    const filtered = values
        .map(value => safeText(value))
        .filter(value => value !== DATA_UNAVAILABLE);
    return filtered.length ? filtered.join(', ') : DATA_UNAVAILABLE;
}

function coordinateText(profile: ResearchProfile): string {
    if (profile.region.lat === null || profile.region.lon === null) {
        return DATA_UNAVAILABLE;
    }
    return `${profile.region.lat.toFixed(4)}, ${profile.region.lon.toFixed(4)}`;
}

function accessTier(profile: ResearchProfile): string {
    return profile.region.cat_tier === null ? DATA_UNAVAILABLE : `Tier ${profile.region.cat_tier}`;
}

function dataCompleteness(profile: ResearchProfile): string {
    if (!profile.region.has_data_gap) return 'No gap flagged';
    const count = profile.region.missing_fields.length;
    return `${count} missing ${count === 1 ? 'field' : 'fields'} flagged`;
}

function affordabilityTone(status: ResearchProfile['affordability']['status']): Tone {
    if (status === 'affordable') return 'good';
    if (status === 'unaffordable') return 'bad';
    return 'warn';
}

function telehealthTone(status: string): Tone {
    if (status === 'TELEHEALTH_READY') return 'good';
    if (status === 'CLINIC_SUPPORTED') return 'warn';
    if (status === 'NOT_READY') return 'bad';
    return 'neutral';
}

function confidenceTone(confidence: string): Tone {
    if (confidence === 'HIGH') return 'good';
    if (confidence === 'MEDIUM') return 'warn';
    if (confidence === 'LOW' || confidence === 'MISSING') return 'bad';
    return 'neutral';
}

function badgeColors(tone: Tone): [string, string] {
    if (tone === 'good') return [GREEN, GREEN_TEXT];
    if (tone === 'warn') return [AMBER, AMBER_TEXT];
    if (tone === 'bad') return [RED, RED_TEXT];
    return [BLUE, BLUE_TEXT];
}

function equityClassification(profile: ResearchProfile): string {
    const telehealth = formatStatusText(profile.telehealth.status);
    const affordability = formatStatusText(profile.affordability.status);
    if (profile.telehealth.status === 'TELEHEALTH_READY' && profile.affordability.status === 'affordable') {
        return 'Ready - Affordable';
    }
    if (profile.telehealth.status === 'CLINIC_SUPPORTED') {
        return `Clinic Supported - ${affordability}`;
    }
    if (profile.telehealth.status === 'NOT_READY') {
        return `Needs Intervention - ${affordability}`;
    }
    return `${telehealth} - ${affordability}`;
}

function equityTone(profile: ResearchProfile): Tone {
    if (profile.telehealth.status === 'TELEHEALTH_READY' && profile.affordability.status === 'affordable') {
        return 'good';
    }
    if (profile.telehealth.status === 'NOT_READY' || profile.affordability.status === 'unaffordable') {
        return 'bad';
    }
    return 'warn';
}

function valueIndex(profile: ResearchProfile): string {
    const cost = profile.affordability.monthly_cost;
    const speed = profile.connectivity.ookla_download_mbps;
    if (cost === null || speed === null || !Number.isFinite(cost) || !Number.isFinite(speed) || speed <= 0) {
        return DATA_UNAVAILABLE;
    }
    return `$${(cost / speed).toFixed(2)}/Mbps`;
}

function telehealthNeed(profile: ResearchProfile): string {
    return telehealthNeedLabel(profile.healthcare.desert_score);
}

function telehealthNeedTone(profile: ResearchProfile): Tone {
    const score = profile.healthcare.desert_score;
    if (score === null || !Number.isFinite(score)) return 'neutral';
    if (score <= 30) return 'good';
    if (score <= 60) return 'warn';
    return 'bad';
}

function generatedLine(profile: ResearchProfile): string {
    const timestamp = new Date(profile.methodology.generated_at).toLocaleString();
    return `Generated ${timestamp} UTC - Dataset Phase 3 - Season ${formatStatusText(profile.telehealth.season)}`;
}

function interpretation(profile: ResearchProfile): string {
    const status = safeText(profile.telehealth.label);
    const desert = formatResearchValue(profile.healthcare.desert_score, { digits: 1 });
    const confidence = formatStatusText(profile.region.data_confidence);
    const affordability = formatStatusText(profile.affordability.status);
    return `${profile.region.name} is classified as ${status} for the selected season. The healthcare desert score is ${desert}, affordability is ${affordability}, and the evidence confidence is ${confidence}. Use this profile to decide whether telehealth can be delivered directly, needs clinic support, or requires follow-up data validation.`;
}

function keyFindings(profile: ResearchProfile): string[] {
    const findings = [
        `CAT tier: ${accessTier(profile)}.`,
        `Telehealth status: ${safeText(profile.telehealth.label)}.`,
        `Healthcare desert score: ${formatResearchValue(profile.healthcare.desert_score, { digits: 1 })}.`,
        `Nearest facility: ${formatResearchValue(profile.healthcare.nearest_facility_name)}.`,
        `Measured download speed: ${formatResearchValue(profile.connectivity.ookla_download_mbps, { suffix: ' Mbps', digits: 1 })}.`,
    ];

    if (profile.region.has_data_gap) {
        findings.push(`Data quality review needed for: ${safeJoin(profile.region.missing_fields)}.`);
    } else {
        findings.push('No data quality gaps are currently flagged.');
    }

    return findings;
}

function addPageBase(pdf: jsPDF) {
    setFill(pdf, '#ffffff');
    pdf.rect(0, 0, PAGE_WIDTH, PAGE_HEIGHT, 'F');
}

function addHeader(pdf: jsPDF, subtitle?: string) {
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(21);
    setText(pdf, INK);
    pdf.text('TENeT Community Report', MARGIN, 18);

    setDraw(pdf, INK);
    pdf.setLineWidth(0.6);
    pdf.line(MARGIN, 24, PAGE_WIDTH - MARGIN, 24);

    if (subtitle) {
        pdf.setFont('helvetica', 'normal');
        pdf.setFontSize(8.5);
        setText(pdf, MUTED);
        pdf.text(pdf.splitTextToSize(subtitle, CONTENT_WIDTH), MARGIN, 32);
    }
}

function addFooter(pdf: jsPDF, pageNumber: number) {
    setDraw(pdf, LINE);
    pdf.setLineWidth(0.2);
    pdf.line(MARGIN, PAGE_HEIGHT - 15, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 15);

    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(7.5);
    setText(pdf, MUTED);
    pdf.text('TENeT community report. Planning support only; verify conditions with local providers and agencies.', MARGIN, PAGE_HEIGHT - 9);
    pdf.text(`Page ${pageNumber} of 2`, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 9, { align: 'right' });
    setText(pdf, INK);
}

function addSectionTitle(pdf: jsPDF, title: string, x: number, y: number): number {
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(13);
    setText(pdf, BRAND);
    pdf.text(title, x, y);
    return y + 5;
}

function addBadge(pdf: jsPDF, text: string, x: number, y: number, maxWidth: number, tone: Tone) {
    const [bg, fg] = badgeColors(tone);
    const label = safeText(text);
    const badgeWidth = Math.min(maxWidth, Math.max(20, pdf.getTextWidth(label) + 7));

    setFill(pdf, bg);
    setDraw(pdf, bg);
    pdf.roundedRect(x, y - 4.5, badgeWidth, 6.5, 3, 3, 'FD');
    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(8);
    setText(pdf, fg);
    pdf.text(pdf.splitTextToSize(label, badgeWidth - 5)[0], x + 3.5, y);
    setText(pdf, INK);
}

function addReportTable(
    pdf: jsPDF,
    title: string,
    rows: ReportRow[],
    x: number,
    y: number,
    width: number,
    compact = false,
): number {
    y = addSectionTitle(pdf, title, x, y);

    const labelWidth = width * (compact ? 0.43 : 0.36);
    const valueWidth = width - labelWidth;

    rows.forEach((row, index) => {
        const label = safeText(row.label);
        const value = safeText(row.value);
        const labelLines = pdf.splitTextToSize(label, labelWidth - 5);
        const valueLines = pdf.splitTextToSize(value, valueWidth - 7);
        const rowHeight = Math.max(compact ? 7.8 : 8.8, Math.max(labelLines.length, valueLines.length) * 4.2 + 4);

        setFill(pdf, index % 2 === 0 ? ROW : '#ffffff');
        setDraw(pdf, '#e7ebf0');
        pdf.rect(x, y, width, rowHeight, 'FD');

        setFill(pdf, LABEL_BG);
        pdf.rect(x, y, labelWidth, rowHeight, 'F');

        pdf.setFont('helvetica', 'bold');
        pdf.setFontSize(compact ? 7.7 : 8.5);
        setText(pdf, '#2f3542');
        pdf.text(labelLines, x + 3, y + 5.4);

        if (row.tone && value.length <= 32) {
            addBadge(pdf, value, x + labelWidth + 3, y + 5.6, valueWidth - 6, row.tone);
        } else {
            pdf.setFont('helvetica', 'normal');
            pdf.setFontSize(compact ? 7.7 : 8.5);
            setText(pdf, INK);
            pdf.text(valueLines, x + labelWidth + 3, y + 5.4);
        }

        y += rowHeight;
    });

    return y + 7;
}

function addFindings(pdf: jsPDF, profile: ResearchProfile, x: number, y: number, width: number): number {
    y = addSectionTitle(pdf, 'Key Findings', x, y);
    pdf.setFont('helvetica', 'normal');
    pdf.setFontSize(8.3);
    setText(pdf, INK);

    keyFindings(profile).forEach(finding => {
        const lines = pdf.splitTextToSize(`- ${finding}`, width - 4);
        pdf.text(lines, x + 2, y);
        y += lines.length * 4.3 + 1;
    });

    return y;
}

export async function exportResearchProfileReport(
    profile: ResearchProfile,
    _mapElement?: HTMLElement | null,
) {
    const pdf = new jsPDF({ unit: 'mm', format: 'a4', orientation: 'portrait' });
    const missingFields = profile.region.has_data_gap
        ? safeJoin(profile.region.missing_fields)
        : 'No gap flagged';

    addPageBase(pdf);
    addHeader(pdf, generatedLine(profile));

    pdf.setFont('helvetica', 'bold');
    pdf.setFontSize(15);
    setText(pdf, BRAND);
    pdf.text(safeText(profile.region.name), MARGIN, 45);

    let y = 55;
    y = addReportTable(pdf, 'Community Overview', [
        { label: 'Region', value: clean(profile.region.region) },
        { label: 'Region Code', value: clean(profile.region.region_code) },
        { label: 'Population', value: DATA_UNAVAILABLE },
        { label: 'Coordinates', value: coordinateText(profile) },
        { label: 'Access Tier (CAT)', value: accessTier(profile), tone: 'neutral' },
        { label: 'Data Confidence', value: formatStatusText(profile.region.data_confidence), tone: confidenceTone(profile.region.data_confidence) },
        { label: 'Data Completeness', value: dataCompleteness(profile), tone: profile.region.has_data_gap ? 'warn' : 'good' },
        { label: 'Season', value: formatStatusText(profile.telehealth.season) },
    ], MARGIN, y, CONTENT_WIDTH);

    y = addReportTable(pdf, 'Digital Equity Analysis', [
        { label: 'Equity Classification', value: equityClassification(profile), tone: equityTone(profile) },
        { label: 'Telehealth Status', value: safeText(profile.telehealth.label), tone: telehealthTone(profile.telehealth.status) },
        { label: 'Telehealth Need', value: telehealthNeed(profile), tone: telehealthNeedTone(profile) },
        { label: 'Affordability Status', value: formatStatusText(profile.affordability.status), tone: affordabilityTone(profile.affordability.status) },
        { label: 'Affordability Ratio', value: formatResearchValue(profile.affordability.burden_pct, { suffix: '%', digits: 2 }) },
        { label: 'Value Index', value: valueIndex(profile) },
        { label: 'Nearest Facility', value: formatResearchValue(profile.healthcare.nearest_facility_name) },
        { label: 'Facility Distance', value: formatResearchValue(profile.healthcare.nearest_facility_distance_km, { suffix: ' km', digits: 1 }) },
        { label: 'Community Anchor', value: formatResearchValue(profile.telehealth.clinic_supported, { booleanLabels: ['Yes', 'No'] }) },
        { label: 'Facility Count', value: formatResearchValue(profile.healthcare.facility_count) },
        { label: 'Classification Reason', value: interpretation(profile) },
    ], MARGIN, y, CONTENT_WIDTH);
    addFooter(pdf, 1);

    pdf.addPage();
    addPageBase(pdf);
    addHeader(pdf, `${safeText(profile.region.name)} - Evidence Detail`);

    const leftX = MARGIN;
    const rightX = MARGIN + CONTENT_WIDTH / 2 + 5;
    const colWidth = CONTENT_WIDTH / 2 - 5;
    let leftY = 45;
    let rightY = 45;

    leftY = addReportTable(pdf, 'Connectivity Metrics', [
        { label: 'FCC 25 Mbps Coverage', value: formatResearchValue(profile.connectivity.fcc_coverage_25mbps_pct, { suffix: '%', digits: 1 }) },
        { label: 'Ookla Download', value: formatResearchValue(profile.connectivity.ookla_download_mbps, { suffix: ' Mbps', digits: 1 }) },
        { label: 'Ookla Upload', value: formatResearchValue(profile.connectivity.ookla_upload_mbps, { suffix: ' Mbps', digits: 1 }) },
        { label: 'Latency', value: formatResearchValue(profile.connectivity.latency_ms, { suffix: ' ms', digits: 0 }) },
        { label: 'Reliability', value: formatResearchValue(profile.connectivity.reliability_label) },
        { label: 'ISP Name', value: formatResearchValue(profile.connectivity.isp_name) },
        { label: 'Data Source', value: formatResearchValue(profile.connectivity.data_source) },
    ], leftX, leftY, colWidth, true);

    leftY = addReportTable(pdf, 'Affordability', [
        { label: 'Monthly Cost', value: formatResearchValue(profile.affordability.monthly_cost, { prefix: '$', digits: 0 }) },
        { label: 'Median Income', value: formatResearchValue(profile.affordability.median_income, { prefix: '$', digits: 0 }) },
        { label: 'Income Burden', value: formatResearchValue(profile.affordability.burden_pct, { suffix: '%', digits: 2 }) },
        { label: 'Threshold', value: formatResearchValue(profile.affordability.threshold_pct, { suffix: '%', digits: 1 }) },
        { label: 'Status', value: formatStatusText(profile.affordability.status), tone: affordabilityTone(profile.affordability.status) },
        { label: 'Value Index', value: valueIndex(profile) },
    ], leftX, leftY, colWidth, true);

    leftY = addReportTable(pdf, 'Data Quality and Missing Fields', [
        { label: 'Data Confidence', value: formatStatusText(profile.region.data_confidence), tone: confidenceTone(profile.region.data_confidence) },
        { label: 'Data Gap Flag', value: formatResearchValue(profile.region.has_data_gap, { booleanLabels: ['Yes', 'No'] }), tone: profile.region.has_data_gap ? 'warn' : 'good' },
        { label: 'Missing Fields', value: missingFields },
        { label: 'Confidence Notes', value: safeJoin(profile.methodology.confidence_notes) },
    ], leftX, leftY, colWidth, true);

    rightY = addReportTable(pdf, 'Healthcare Access', [
        { label: 'Nearest Facility', value: formatResearchValue(profile.healthcare.nearest_facility_name) },
        { label: 'Facility Type', value: formatResearchValue(profile.healthcare.nearest_facility_type) },
        { label: 'Facility Distance', value: formatResearchValue(profile.healthcare.nearest_facility_distance_km, { suffix: ' km', digits: 1 }) },
        { label: 'Emergency Services', value: formatResearchValue(profile.healthcare.emergency_services, { booleanLabels: ['Yes', 'No'] }) },
        { label: 'Specialists', value: formatResearchValue(profile.healthcare.specialist_available, { booleanLabels: ['Yes', 'No'] }) },
        { label: 'Facility Count', value: formatResearchValue(profile.healthcare.facility_count) },
        { label: 'Desert Score', value: formatResearchValue(profile.healthcare.desert_score, { digits: 1 }) },
    ], rightX, rightY, colWidth, true);

    rightY = addReportTable(pdf, 'Telehealth Feasibility', [
        { label: 'Status', value: safeText(profile.telehealth.label), tone: telehealthTone(profile.telehealth.status) },
        { label: 'Telehealth Need', value: telehealthNeed(profile), tone: telehealthNeedTone(profile) },
        { label: 'Video Feasible', value: formatResearchValue(profile.telehealth.video_feasible, { booleanLabels: ['Yes', 'No'] }) },
        { label: 'Audio Feasible', value: formatResearchValue(profile.telehealth.audio_feasible, { booleanLabels: ['Yes', 'No'] }) },
        { label: 'Clinic Supported', value: formatResearchValue(profile.telehealth.clinic_supported, { booleanLabels: ['Yes', 'No'] }) },
        { label: 'Season', value: formatStatusText(profile.telehealth.season) },
        { label: 'Season Note', value: formatResearchValue(profile.telehealth.season_note) },
    ], rightX, rightY, colWidth, true);

    rightY = addReportTable(pdf, 'Data Sources', [
        { label: 'Sources', value: safeJoin(profile.methodology.sources) },
        { label: 'Generated At', value: new Date(profile.methodology.generated_at).toLocaleString() },
    ], rightX, rightY, colWidth, true);

    const finalY = Math.max(leftY, rightY);
    addFindings(pdf, profile, MARGIN, finalY + 4, CONTENT_WIDTH);

    addFooter(pdf, 2);
    pdf.save(`tenet-community-report-${fileSafe(profile.region.name)}.pdf`);
}
