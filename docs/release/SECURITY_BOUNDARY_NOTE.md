# Security Boundary Note

The provider repair and production SDK-load gate must not trade away WebVM isolation. `/provider/` is a deliberately separate helper surface; its exemption is same-origin and path-bounded. `/demo/` continues to require cross-origin isolation.

If future provider integrations need different browser policy, create a separate narrowly scoped helper boundary and qualify it explicitly rather than broadening the `/demo/` exemption.
