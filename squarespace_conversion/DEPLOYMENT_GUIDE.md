# Squarespace Deployment Guide
## Hawaii State Budget FY 2026 Departmental Reports

This guide explains how to deploy your departmental budget reports to Squarespace.

## Overview

Your HTML reports have been converted to Squarespace-compatible format with the following changes:
- **Removed base64 images** (charts) - Squarespace has size limits on code blocks
- **Scoped CSS** - All styles are prefixed to avoid conflicts with Squarespace themes
- **Responsive design** - Works on mobile and desktop
- **Self-contained** - Each report is a complete code block

## Deployment Options

### Option 1: Code Blocks (Recommended)
**Pros:** Full control over styling, interactive elements, professional appearance
**Cons:** Manual setup for each department, limited by Squarespace code block size limits

### Option 2: Blog Posts
**Pros:** Easy to manage, good for SEO, can include charts as separate images
**Cons:** Less control over layout, may not match your site design

### Option 3: External Hosting + Embed
**Pros:** No limitations, full functionality, can include charts
**Cons:** Requires separate hosting, more complex setup

## Step-by-Step Instructions

### Method 1: Code Blocks (Recommended)

#### 1. Create Main Navigation Page
1. In Squarespace, create a new page called "Budget Reports"
2. Add a **Code Block** to the page
3. Copy the entire content from `index_squarespace.html`
4. Paste it into the code block
5. Save and preview

#### 2. Create Individual Department Pages
For each department (25 total):

1. **Create a new page:**
   - Go to Pages → Add Page
   - Choose "Standard Page"
   - Name it: "[DEPT CODE] Budget Report" (e.g., "HRD Budget Report")

2. **Add the code block:**
   - Add a **Code Block** to the page
   - Copy the entire content from the corresponding `[dept]_squarespace.html` file
   - Paste it into the code block

3. **Configure page settings:**
   - Set the page URL slug to match the department code (e.g., `/hrd-budget`)
   - Add to navigation if desired
   - Set SEO title: "[Department Name] FY26 Budget Report"

#### 3. Link Pages Together
1. Edit your main navigation page (`index_squarespace.html`)
2. Add links to each department page by modifying the dept-card divs:

```html
<div class="dept-card">
    <a href="/hrd-budget" style="text-decoration: none; color: inherit;">
        <div class="dept-code">HRD</div>
        <div class="dept-name">Department of Human Resources Development</div>
    </a>
</div>
```

### Method 2: Blog Posts

#### 1. Create a Blog
1. Add a Blog page to your site
2. Title it "Budget Reports" or "FY26 Departmental Budgets"

#### 2. Create Posts for Each Department
1. **Create a new blog post** for each department
2. **Title:** "[Department Name] FY26 Budget Report"
3. **Content:** 
   - Add a **Code Block** with the department's HTML content
   - Or convert the HTML to regular Squarespace blocks (text, tables, etc.)

#### 3. Create Categories
- Create blog categories for easy navigation:
  - "Operating Budgets"
  - "Capital Improvements" 
  - "One-Time Appropriations"

### Method 3: External Hosting + Embed

#### 1. Host Files Externally
- Upload your original HTML files to:
  - GitHub Pages (free)
  - Netlify (free)
  - Your own web hosting

#### 2. Embed in Squarespace
- Use **Embed Blocks** to include the external pages
- Or create links to the external reports

## File Structure

Your converted files are organized as follows:

```
squarespace_conversion/
├── index_squarespace.html          # Main navigation page
├── agr_squarespace.html            # Agriculture Department
├── ags_squarespace.html            # Accounting & General Services
├── atg_squarespace.html            # Attorney General
├── bed_squarespace.html            # Business, Economic Dev, Tourism
├── buf_squarespace.html            # Budget & Finance
├── cca_squarespace.html            # Commerce & Consumer Affairs
├── cch_squarespace.html            # City & County of Honolulu
├── coh_squarespace.html            # County of Hawaii
├── cok_squarespace.html            # County of Kauai
├── def_squarespace.html            # Defense
├── edn_squarespace.html            # Education
├── gov_squarespace.html            # Governor's Office
├── hhl_squarespace.html            # Hawaiian Home Lands
├── hms_squarespace.html            # Human Services
├── hrd_squarespace.html            # Human Resources Development
├── hth_squarespace.html            # Health
├── law_squarespace.html            # Law Enforcement
├── lbr_squarespace.html            # Labor & Industrial Relations
├── lnr_squarespace.html            # Land & Natural Resources
├── ltg_squarespace.html            # Lieutenant Governor
├── p_squarespace.html              # General Administration
├── psd_squarespace.html            # Corrections & Rehabilitation
├── tax_squarespace.html            # Taxation
├── trn_squarespace.html            # Transportation
├── uoh_squarespace.html            # University of Hawaii
└── DEPLOYMENT_GUIDE.md             # This guide
```

## Department Code Reference

| Code | Department Name |
|------|----------------|
| AGR  | Department of Agriculture |
| AGS  | Department of Accounting and General Services |
| ATG  | Department of the Attorney General |
| BED  | Department of Business, Economic Development and Tourism |
| BUF  | Department of Budget and Finance |
| CCA  | Department of Commerce and Consumer Affairs |
| CCH  | City and County of Honolulu |
| COH  | County of Hawaii |
| COK  | County of Kauai |
| DEF  | Department of Defense |
| EDN  | Department of Education |
| GOV  | Office of the Governor |
| HHL  | Department of Hawaiian Home Lands |
| HMS  | Department of Human Services |
| HRD  | Department of Human Resources Development |
| HTH  | Department of Health |
| LAW  | Department of Law Enforcement |
| LBR  | Department of Labor and Industrial Relations |
| LNR  | Department of Land and Natural Resources |
| LTG  | Office of the Lieutenant Governor |
| P    | General Administration |
| PSD  | Department of Corrections and Rehabilitation |
| TAX  | Department of Taxation |
| TRN  | Department of Transportation |
| UOH  | University of Hawaii |

## Squarespace Limitations & Workarounds

### Code Block Size Limits
- **Limit:** ~20,000 characters per code block
- **Workaround:** Files have been optimized to stay under this limit
- **If needed:** Split large departments into multiple code blocks

### No External File References
- **Issue:** Can't link to external CSS/JS files
- **Solution:** All CSS is embedded inline (already done)

### Image Handling
- **Issue:** Base64 images removed due to size constraints
- **Solutions:**
  1. Upload chart images separately to Squarespace
  2. Add Image Blocks above/below the code blocks
  3. Link to external charts hosted elsewhere

### Navigation
- **Issue:** No automatic navigation between pages
- **Solution:** Add manual links in the code or use Squarespace's navigation system

## SEO Optimization

### Page Titles
Use descriptive titles for each page:
- "Hawaii Department of Education FY26 Budget Report"
- "Attorney General Budget Allocation FY 2026"

### Meta Descriptions
Add custom descriptions in Squarespace page settings:
- "Detailed budget breakdown for [Department] including operating expenses, capital improvements, and special appropriations for fiscal year 2026."

### URL Structure
Use clean URLs:
- `/budget-reports` (main page)
- `/budget-reports/education` or `/edn-budget`
- `/budget-reports/attorney-general` or `/atg-budget`

## Maintenance & Updates

### Updating Data
1. Regenerate reports using your Python scripts
2. Run the conversion script again
3. Copy new HTML content to Squarespace code blocks

### Adding New Departments
1. Add new department to the conversion script
2. Create new Squarespace page
3. Update navigation links

## Troubleshooting

### Code Block Not Displaying
- Check for HTML syntax errors
- Ensure code block size is under limit
- Try pasting in smaller sections

### Styling Issues
- Squarespace theme CSS may conflict
- Add `!important` to critical styles if needed
- Test on different devices/browsers

### Mobile Display Problems
- All converted files include responsive CSS
- Test on mobile devices
- Adjust breakpoints if needed

## Alternative: Quick Setup with Squarespace Blocks

If code blocks are too complex, you can recreate the reports using standard Squarespace blocks:

1. **Text Blocks** for headers and descriptions
2. **Table Blocks** for budget data (if available in your plan)
3. **Image Blocks** for charts (upload separately)
4. **Spacer Blocks** for layout

This approach is more time-consuming but may be easier to maintain.

## Support

For technical issues with the conversion:
1. Check the original HTML files for reference
2. Validate HTML syntax online
3. Test in a simple HTML file first
4. Contact Squarespace support for platform-specific issues

---

**Generated for Hawaii State Budget FY 2026 Post-Veto Data**  
*Last updated: [Current Date]*
