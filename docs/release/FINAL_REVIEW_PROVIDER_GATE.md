# Final Review Questions — Provider Gate

Before approving a provider/demo release change:

1. What exact public-origin failure could this change introduce that a fixture would hide?
2. Which service worker controls each affected path?
3. Are `/demo/` and `/provider/` expected isolation states asserted independently?
4. Does the first post-merge deployment run the real external SDK check?
5. Does that check stop before auth/inference?
6. Are real auth/inference claims separately evidenced?
7. Is narrow Chromium being described accurately rather than as physical mobile?
8. Is the exact deployed SHA visible in retained evidence?
9. Is any first failure being preserved?
10. Are any untested layers still marked NOT_RUN/UNKNOWN/BLOCKED?

Any unclear answer is a reason to stop and investigate before merge.
