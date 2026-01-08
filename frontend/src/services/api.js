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
