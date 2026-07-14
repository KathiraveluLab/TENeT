import { useEffect, useMemo, useState } from 'react';
import {
    fetchAffordability,
    fetchAllTelehealthStatus,
    fetchDataGapsSummary,
    fetchHealthcareSummary,
    fetchPerformanceSummary,
    fetchStatistics,
    type AffordabilityResponse,
    type AllTelehealthStatusResponse,
    type DataGapsSummary,
    type HealthcareSummary,
    type PerformanceSummary,
    type StatisticsResponse,
} from '../api/catApi';
import { errorMessage, isAbortError } from '../api/http';

export interface DashboardData {
    statistics: StatisticsResponse | null;
    telehealthStatus: AllTelehealthStatusResponse | null;
    healthcare: HealthcareSummary | null;
    performance: PerformanceSummary | null;
    dataGaps: DataGapsSummary | null;
    affordability: AffordabilityResponse | null;
}

export type DashboardSection = keyof DashboardData;
export type DashboardSectionErrors = Partial<Record<DashboardSection, string>>;

const EMPTY_DATA: DashboardData = {
    statistics: null,
    telehealthStatus: null,
    healthcare: null,
    performance: null,
    dataGaps: null,
    affordability: null,
};

function rejectedMessage(result: PromiseSettledResult<unknown>): string | undefined {
    return result.status === 'rejected' ? errorMessage(result.reason) : undefined;
}

export function useDashboardData() {
    const [data, setData] = useState<DashboardData>(EMPTY_DATA);
    const [sectionErrors, setSectionErrors] = useState<DashboardSectionErrors>({});
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;
        const controller = new AbortController();

        async function loadData() {
            setLoading(true);
            setError(null);
            setSectionErrors({});

            try {
                const results = await Promise.allSettled([
                    fetchStatistics(controller.signal),
                    fetchAllTelehealthStatus(controller.signal),
                    fetchHealthcareSummary(controller.signal),
                    fetchPerformanceSummary(controller.signal),
                    fetchDataGapsSummary(controller.signal),
                    fetchAffordability(120, 2, controller.signal),
                ] as const);

                if (!isMounted || controller.signal.aborted) return;

                const [
                    statisticsResult,
                    telehealthResult,
                    healthcareResult,
                    performanceResult,
                    dataGapsResult,
                    affordabilityResult,
                ] = results;

                const nextData: DashboardData = {
                    statistics: statisticsResult.status === 'fulfilled' ? statisticsResult.value : null,
                    telehealthStatus: telehealthResult.status === 'fulfilled' ? telehealthResult.value : null,
                    healthcare: healthcareResult.status === 'fulfilled' ? healthcareResult.value : null,
                    performance: performanceResult.status === 'fulfilled' ? performanceResult.value : null,
                    dataGaps: dataGapsResult.status === 'fulfilled' ? dataGapsResult.value : null,
                    affordability: affordabilityResult.status === 'fulfilled' ? affordabilityResult.value : null,
                };

                const nextSectionErrors: DashboardSectionErrors = {};
                const resultBySection: Record<DashboardSection, PromiseSettledResult<unknown>> = {
                    statistics: statisticsResult,
                    telehealthStatus: telehealthResult,
                    healthcare: healthcareResult,
                    performance: performanceResult,
                    dataGaps: dataGapsResult,
                    affordability: affordabilityResult,
                };

                (Object.keys(resultBySection) as DashboardSection[]).forEach(section => {
                    const message = rejectedMessage(resultBySection[section]);
                    if (message) nextSectionErrors[section] = message;
                });

                const failedCount = Object.keys(nextSectionErrors).length;
                setData(nextData);
                setSectionErrors(nextSectionErrors);
                setError(failedCount === results.length
                    ? 'Statewide insight sources are currently unavailable. Return to the map and try again later.'
                    : null);
            } catch (caught: unknown) {
                if (!isMounted || isAbortError(caught)) return;
                setData(EMPTY_DATA);
                setError(errorMessage(caught));
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        loadData();
        return () => {
            isMounted = false;
            controller.abort();
        };
    }, []);

    const availableSectionCount = useMemo(
        () => Object.values(data).filter(Boolean).length,
        [data],
    );
    const unavailableSectionCount = Object.keys(sectionErrors).length;

    return {
        data,
        sectionErrors,
        availableSectionCount,
        hasPartialData: availableSectionCount > 0 && unavailableSectionCount > 0,
        loading,
        error,
    };
}
