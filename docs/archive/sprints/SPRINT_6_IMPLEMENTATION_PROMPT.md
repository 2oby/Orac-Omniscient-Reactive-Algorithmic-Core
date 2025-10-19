# Sprint 6: UI Enhancements Implementation Prompt

## Context
You are implementing Sprint 6 for the ORAC system. Sprint 5 successfully encapsulated dispatchers within backends. Now we're focusing on UI/UX improvements to polish the cyberpunk-themed web interface.

## Current State
- Backend dispatcher integration is complete and working
- The UI has a cyberpunk theme with green/amber/red color scheme
- Some navigation is inconsistent
- Color states don't always match element status
- Hover effects are minimal

## Sprint 6 Objectives
Implement the UI enhancements outlined in SPRINT_6_UI_ENHANCEMENTS.md:

### Phase 1: Navigation Improvements
1. Add "Overview" button to all pages (links to /backends)
2. Fix the backend devices/entities screens that lack navigation
3. Ensure every page has both:
   - Back button (contextual navigation)
   - Overview button (home navigation)
4. Add breadcrumb navigation for deeper pages

### Phase 2: Color Consistency
1. Audit all components for color inconsistencies
2. Fix specific issues:
   - Save/fetch icons should match state colors (not monochrome)
   - Disabled entities should show amber/orange text (not green)
   - Borders should match element state
3. Create CSS utility classes:
   ```css
   .state-active { color: var(--primary-green); }
   .state-disabled { color: var(--warning-amber); }
   .state-error { color: var(--error-red); }
   ```

### Phase 3: Hover Pulse Effects
1. Implement cyberpunk pulse animation:
   ```css
   @keyframes cyberpunk-pulse {
     0% { box-shadow: 0 0 5px var(--glow-color); filter: brightness(1); }
     50% { box-shadow: 0 0 20px var(--glow-color), 0 0 40px var(--glow-color); filter: brightness(1.2); }
     100% { box-shadow: 0 0 5px var(--glow-color); filter: brightness(1); }
   }
   ```
2. Apply to all interactive elements
3. Add subtle scale transform (1 to 1.02)

### Phase 4: Additional Enhancements (Optional)
- Loading spinners with cyberpunk style
- Toast notifications for save/error feedback
- Smooth page transitions
- Better form validation feedback

## Implementation Guidelines

### Files to Modify
- **Templates**: `/orac/templates/*.html`
  - Add navigation bars
  - Update CSS styles
  - Fix color classes

- **Static CSS**: Create `/orac/static/css/cyberpunk-enhancements.css`
  - Centralize new animations
  - State color utilities
  - Hover effects

- **JavaScript**: Update existing JS files
  - Add toast notification system
  - Enhance interactive feedback

### Testing Checklist
- [ ] All pages have Overview navigation
- [ ] Backend entities screen has proper navigation
- [ ] Colors match element states consistently
- [ ] Hover effects work on all interactive elements
- [ ] Animations are smooth (60fps)
- [ ] Mobile responsive
- [ ] No accessibility regressions

## Color Reference
```css
--primary-green: #00ff41;    /* Active/Enabled */
--warning-amber: #ffaa00;    /* Warning/Disabled */
--error-red: #ff0033;        /* Error/Offline */
--dark-bg: #0a0e1b;          /* Background */
--border-color: #1a1f2e;     /* Borders */
```

## Start Command
When ready to begin Sprint 6:
1. Review SPRINT_6_UI_ENHANCEMENTS.md for full details
2. Start with Phase 1 (Navigation) as it's the most critical
3. Test each change before moving to the next phase
4. Create small, focused commits for each improvement
5. Deploy and test on the ORIN after each phase

## Success Criteria
- Users can navigate to Overview from any page
- Visual consistency across all UI elements
- Satisfying hover feedback on all interactions
- UI feels polished and professional
- Maintains cyberpunk aesthetic throughout

## Notes
- Keep backward compatibility
- Test on both desktop and mobile
- Ensure animations don't impact performance
- Consider adding a settings toggle for reduced motion
- Document any new CSS classes or JavaScript functions