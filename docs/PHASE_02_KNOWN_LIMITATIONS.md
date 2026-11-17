# Phase 02 Known Limitations

This records the frontend-only Phase 02 boundary. The later backend foundation adds Cognito/NextAuth sign-in, a protected API, database ownership, and private-storage APIs, but the Phase 02 demo state and screenshot picker have not yet been integrated with them.

1. **Demo state is not account-connected:** projects/audits/documents shown by the Phase 02 UI remain browser-local fixtures and are not loaded from the authenticated API or database.
2. **Uploader integration is pending:** screenshots are still previewed through temporary browser object URLs in the Phase 02 UI. The API now supports private presigned uploads, but the UI does not call it yet. Document selection stores only local metadata.
3. **No AI analysis:** no model is called. The only findings and status examples are explicitly labelled illustrative fixtures. Newly created audit records contain no findings and are not represented as a successful clean audit.
4. **No real knowledge processing:** extraction, OCR, chunking, embeddings, vector retrieval, citation validation, duplicate detection, and global administrator permissions are not implemented.
5. **Local persistence only:** project/audit/document metadata and preferences use this browser's local storage. Browser clearing or storage limits may remove/reset data. Screenshot previews do not survive a refresh.
6. **Demo identity and workspace:** profile/workspace/role placeholders remain in the Phase 02 app state. Cognito sign-in and backend membership checks now exist when configured, but team collaboration, account deletion, and binding the demo workspace to the authenticated tenant do not.
7. **No live Stitch integration:** prompt text is composed in the browser, remains editable/copyable, and is not sent to Google Stitch.
8. **Illustrative flow only:** screen order reflects the supplied order in the demo; connectors and sample cross-screen findings do not establish that a real product traverses those screens.
9. **Processing states are presentation fixtures:** sample ready/processing/failed document states are not actual worker states. No retry or extraction operation runs.
10. **Accessibility status:** semantic/keyboard/responsive patterns were implemented, but this phase is not a WCAG 2.2 AA certification; manual and assistive-technology testing remains necessary.
11. **Deployment and product decisions remain:** Cognito and private AWS S3 are selected for the foundation, but live services are not provisioned. Region, retention, quotas, image limits, and AI provider still require approval or evaluation before production.
