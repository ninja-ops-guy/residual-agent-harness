# Regression Test Principle

When a production regression escapes, add the durable test at the earliest layer that would have detected the actual failure without depending on downstream behavior. Keep existing lower-layer tests; do not mutate them into a different kind of test and lose their original coverage.

For the provider COI incident, the escaped layer was published-origin external SDK loading, so that is where the new gate lives.
