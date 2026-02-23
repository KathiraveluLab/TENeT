/**
 * API Service for TENeT Backend
 * 
 * Handles all communication with the FastAPI backend.
 * Provides methods for fetching community data with proper error handling.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

/**
 * Fetch all communities (lightweight view for map)
 */
export async function fetchCommunities() {
  try {
    const response = await fetch(`${API_BASE_URL}/communities`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error fetching communities:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Fetch complete data for a specific community
 */
export async function fetchCommunity(communityId) {
  try {
    const response = await fetch(`${API_BASE_URL}/communities/${communityId}`)
    
    if (!response.ok) {
      if (response.status === 404) {
        throw new Error('Community not found')
      }
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error(`Error fetching community ${communityId}:`, error)
    return { data: null, error: error.message }
  }
}

/**
 * Fetch healthcare data for a specific community
 */
export async function fetchCommunityHealthcare(communityId) {
  try {
    const response = await fetch(`${API_BASE_URL}/communities/${communityId}/healthcare`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error(`Error fetching healthcare for ${communityId}:`, error)
    return { data: null, error: error.message }
  }
}

/**
 * Fetch connectivity data for a specific community
 */
export async function fetchCommunityConnectivity(communityId) {
  try {
    const response = await fetch(`${API_BASE_URL}/communities/${communityId}/connectivity`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error(`Error fetching connectivity for ${communityId}:`, error)
    return { data: null, error: error.message }
  }
}

/**
 * Fetch digital equity analysis for a specific community
 */
export async function fetchDigitalEquity(communityId, refresh = false) {
  try {
    const url = `${API_BASE_URL}/communities/${communityId}/digital-equity${refresh ? '?refresh=true' : ''}`
    const response = await fetch(url)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error(`Error fetching digital equity for ${communityId}:`, error)
    return { data: null, error: error.message }
  }
}

/**
 * Fetch digital equity summary for all communities
 */
export async function fetchDigitalEquitySummary() {
  try {
    const response = await fetch(`${API_BASE_URL}/digital-equity/summary`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error fetching digital equity summary:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Trigger batch update of digital equity data
 */
export async function batchUpdateDigitalEquity(limit = null) {
  try {
    const url = limit 
      ? `${API_BASE_URL}/digital-equity/batch-update?limit=${limit}`
      : `${API_BASE_URL}/digital-equity/batch-update`
    
    const response = await fetch(url, { method: 'POST' })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error batch updating digital equity:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Check API health
 */
export async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error checking API health:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Search communities by query
 */
export async function searchCommunities(query) {
  try {
    const response = await fetch(`${API_BASE_URL}/communities/search?q=${encodeURIComponent(query)}`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data: data.results || [], error: null }
  } catch (error) {
    console.error('Error searching communities:', error)
    return { data: [], error: error.message }
  }
}

/**
 * Fetch community statistics
 */
export async function fetchCommunityStats() {
  try {
    const response = await fetch(`${API_BASE_URL}/communities/stats`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error fetching community stats:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Fetch healthcare necessity score for a community
 */
export async function fetchNecessityScore(communityId, season) {
  try {
    const response = await fetch(`${API_BASE_URL}/communities/${communityId}/necessity?season=${season}`)
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error(`Error fetching necessity score for ${communityId}:`, error)
    return { data: null, error: error.message }
  }
}

// ── New endpoints ────────────────────────────────────────────────

/**
 * Fetch data coverage / transparency stats
 */
export async function fetchSystemCoverage() {
  try {
    const response = await fetch(`${API_BASE_URL}/system/coverage`)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error fetching system coverage:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Run sensitivity analysis / simulation with custom thresholds
 */
export async function runSimulation(threshold = 2.0, radius = 5.0) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/simulate?threshold=${threshold}&radius=${radius}`
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return { data, error: null }
  } catch (error) {
    console.error('Error running simulation:', error)
    return { data: null, error: error.message }
  }
}

/**
 * Autocomplete search (lightweight)
 */
export async function autocompleteSearch(query, limit = 10) {
  try {
    const response = await fetch(
      `${API_BASE_URL}/communities/search/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`
    )
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const data = await response.json()
    return { data: data.results || [], error: null }
  } catch (error) {
    console.error('Error in autocomplete:', error)
    return { data: [], error: error.message }
  }
}
