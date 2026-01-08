# TENeT Integration Testing Checklist

Use this checklist to verify the end-to-end data integration pipeline is working correctly.

## Pre-flight Checks

- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] Node.js 16+ installed (`node --version`)
- [ ] npm installed (`npm --version`)
- [ ] Ports 8000 and 5173 are available

---

## Backend Setup Tests

### Installation

- [ ] Created virtual environment successfully
- [ ] Activated virtual environment
- [ ] Installed all dependencies without errors
- [ ] No missing module errors

### Server Startup

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

**Expected output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
✓ Loaded 8 communities into data store
```

- [ ] Server starts without errors
- [ ] "Loaded 8 communities" message appears
- [ ] No import errors
- [ ] Server accessible at http://localhost:8000

### API Endpoints

Test each endpoint:

#### Health Check
```bash
curl http://localhost:8000/api/health
```
- [ ] Returns JSON: `{"status":"healthy","communities_loaded":8}`
- [ ] HTTP 200 status code

#### List Communities
```bash
curl http://localhost:8000/api/communities | jq
```
- [ ] Returns array of 8 communities
- [ ] Each has: community_id, name, location, data_completeness
- [ ] HTTP 200 status code

#### Get Specific Community
```bash
curl http://localhost:8000/api/communities/AK-02185-0001 | jq
```
- [ ] Returns full community object
- [ ] Has healthcare, connectivity, access sections
- [ ] Each section has confidence field
- [ ] HTTP 200 status code

#### Get Healthcare Data
```bash
curl http://localhost:8000/api/communities/AK-02185-0001/healthcare | jq
```
- [ ] Returns healthcare object only
- [ ] Has facility_count, facility_types, source, confidence
- [ ] HTTP 200 status code

#### Get Connectivity Data
```bash
curl http://localhost:8000/api/communities/AK-02185-0001/connectivity | jq
```
- [ ] Returns connectivity object only
- [ ] Has speed metrics, source, confidence
- [ ] HTTP 200 status code

#### Error Handling
```bash
curl http://localhost:8000/api/communities/INVALID-ID
```
- [ ] Returns 404 error
- [ ] Has meaningful error message

### API Documentation

Visit http://localhost:8000/api/docs

- [ ] Swagger UI loads
- [ ] All 5 endpoints visible
- [ ] Can expand each endpoint
- [ ] Can try out endpoints interactively
- [ ] Schemas are documented

---

## Frontend Setup Tests

### Installation

```bash
cd frontend
npm install
```

- [ ] Installs without errors
- [ ] No peer dependency warnings
- [ ] node_modules directory created

### Configuration

- [ ] `.env.example` file exists
- [ ] Can copy to `.env`
- [ ] API URL configured correctly

### Server Startup

```bash
npm run dev
```

**Expected output:**
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

- [ ] Vite starts without errors
- [ ] No module resolution errors
- [ ] Opens at http://localhost:5173

---

## Frontend UI Tests

Open http://localhost:5173 in your browser

### Initial Load

- [ ] Page loads without errors (check console)
- [ ] Alaska map renders
- [ ] Map is centered on Alaska
- [ ] Can zoom in/out
- [ ] Can pan the map
- [ ] Map legend visible in bottom-left
- [ ] Community markers appear after ~1 second

### Map Interaction

- [ ] 8 community markers visible
- [ ] Markers are color-coded (green, yellow, orange, gray)
- [ ] Can hover over markers
- [ ] Can click markers
- [ ] Popup appears on click with "View Details" button

### Marker Colors

Verify marker colors match data completeness:

- [ ] Anchorage - Green (high completeness)
- [ ] Juneau - Green (high completeness)
- [ ] Bethel - Yellow/Green (medium-high)
- [ ] Nome - Yellow/Green (medium-high)
- [ ] Napakiak - Orange/Gray (low completeness)

### Community Info Panel

Click any community marker:

**Panel Behavior:**
- [ ] Panel slides in from right
- [ ] Smooth animation
- [ ] Panel header shows community name
- [ ] Close button (×) visible in top-right

**Data Completeness Section:**
- [ ] Progress bar visible at top
- [ ] Percentage displayed
- [ ] Quality label shows (Good/Moderate/Limited Coverage)
- [ ] Bar color matches quality level

**Community Details Section:**
- [ ] Region displayed (or N/A)
- [ ] Population shown (or N/A)
- [ ] Coordinates formatted correctly
- [ ] Community ID visible

**Healthcare Section:**
- [ ] Section has confidence badge
- [ ] Facility count shown
- [ ] Facility types listed
- [ ] Source attribution visible
- [ ] Notes displayed if present
- [ ] Last updated date (if present)

**Connectivity Section:**
- [ ] Section has confidence badge
- [ ] Download speed in Mbps
- [ ] Upload speed in Mbps
- [ ] Latency in ms (or "No data")
- [ ] Source attribution visible
- [ ] Notes displayed if present

**Access & Transportation Section:**
- [ ] Section has confidence badge
- [ ] Transportation methods listed
- [ ] Seasonal flag if applicable
- [ ] Notes displayed if present

**Raw Data Section:**
- [ ] "📊 Raw Data" section visible
- [ ] Can expand/collapse
- [ ] Shows formatted JSON when expanded
- [ ] JSON is readable and properly indented

### Confidence Badges

For each section (Healthcare, Connectivity, Access):

- [ ] Badge displays (✓, ~, ?, or ✗)
- [ ] Badge has color (green, yellow, orange, or gray)
- [ ] Hover shows tooltip with description
- [ ] Badge matches data quality

### Multiple Communities

Test with different communities:

**Anchorage (Major City):**
- [ ] High data completeness (90%+)
- [ ] All sections have data
- [ ] High confidence badges

**Napakiak (Small Village):**
- [ ] Lower data completeness (<70%)
- [ ] Some "No data" entries
- [ ] Lower confidence badges
- [ ] Notes explain limited data

### Panel Closing

- [ ] Click close button (×) - panel slides out
- [ ] Click another marker - panel updates smoothly
- [ ] Panel shows loading state briefly when switching

---

## Error Handling Tests

### Backend Down

Stop the backend server, then:

- [ ] Frontend shows error state on map
- [ ] Error message is helpful
- [ ] Mentions checking backend server
- [ ] No console errors after timeout

### Invalid Data

Restart backend, then in frontend:

- [ ] Missing fields show "No data" or "N/A"
- [ ] Null values handled gracefully
- [ ] No undefined errors in console

---

## Performance Tests

### Load Time

- [ ] Initial page load < 3 seconds
- [ ] Map renders < 1 second after load
- [ ] Community markers appear < 2 seconds after load
- [ ] Panel opens < 500ms after click

### Interactions

- [ ] Smooth map panning (no lag)
- [ ] Smooth zoom transitions
- [ ] Panel animations fluid (60fps feel)
- [ ] Marker clicks responsive
- [ ] No memory leaks after opening/closing panel multiple times

---

## Browser Compatibility

Test in multiple browsers:

### Chrome
- [ ] All features work
- [ ] No console errors
- [ ] Smooth animations

### Firefox
- [ ] All features work
- [ ] No console errors
- [ ] Smooth animations

### Safari
- [ ] All features work
- [ ] Backdrop blur works
- [ ] No console errors

---

## Responsive Design

### Desktop (1920x1080)
- [ ] Map fills viewport
- [ ] Panel width appropriate
- [ ] Legend readable
- [ ] No overflow

### Laptop (1366x768)
- [ ] Layout adjusts
- [ ] Panel doesn't cover too much map
- [ ] All text readable

### Mobile (375x667)
- [ ] Map responsive
- [ ] Panel takes full width
- [ ] Can close panel easily
- [ ] Touch interactions work

---

## Console Tests

### No Errors

Check browser console:

- [ ] No red errors on load
- [ ] No warnings about missing props
- [ ] No 404s or failed requests
- [ ] No CORS errors
- [ ] API calls succeed

### Network Tab

Check network requests:

- [ ] `/api/communities` loads successfully
- [ ] `/api/communities/{id}` loads on click
- [ ] Reasonable response times (< 1s)
- [ ] Correct status codes (200, 404)

---

## Final Integration Test

Complete end-to-end flow:

1. [ ] Start backend server
2. [ ] Verify health endpoint
3. [ ] Start frontend server
4. [ ] Open browser to localhost:5173
5. [ ] Wait for map to load
6. [ ] See 8 community markers
7. [ ] Click Anchorage marker
8. [ ] Panel slides in with data
9. [ ] Verify all sections populated
10. [ ] Check confidence badges
11. [ ] Expand raw data section
12. [ ] Close panel
13. [ ] Click Napakiak marker
14. [ ] Verify lower data completeness
15. [ ] See "No data" entries
16. [ ] Close panel
17. [ ] Test 2-3 more communities
18. [ ] No errors in console

---

## Documentation Tests

- [ ] README.md is clear and accurate
- [ ] SETUP.md has working instructions
- [ ] PR_SUMMARY.md explains changes
- [ ] Backend README explains API
- [ ] Frontend README explains UI
- [ ] Code comments are helpful
- [ ] API docs at /api/docs are complete

---

## Pass Criteria

✅ **All sections should be checked** for PR to be considered complete.

If any tests fail:
1. Note the specific failure
2. Check error messages
3. Review console output
4. Verify configuration
5. Consult SETUP.md troubleshooting section

---

## Sign-off

- [ ] All backend tests pass
- [ ] All frontend tests pass
- [ ] All integration tests pass
- [ ] No console errors
- [ ] Documentation is complete
- [ ] Code is ready for review

**Tested by:** _____________  
**Date:** _____________  
**Notes:** _____________
