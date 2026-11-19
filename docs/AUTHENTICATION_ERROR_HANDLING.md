# Authentication and Error Handling

## 401 Unauthorized

The Axios client detects protected-route 401 responses, removes the stored JWT and theme-user cache key, records a session-expired notification, and dispatches `smart-parking-session-expired`. The auth provider clears in-memory user state, so React Router redirects to login. Login and password-change 401 responses are not treated as expired protected sessions.

## 403 Forbidden

403 responses do not clear authentication. Restricted route rendering is guarded in `App.tsx`, and the UI provides a dashboard link.

## HTTP and Network Errors

Existing pages display meaningful API/network feedback where remediated. They must not translate a failed request into an empty dataset.
