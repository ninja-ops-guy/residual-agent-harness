# RESIDUAL v1 external pilot protocol

Status: prepared protocol; no participants contacted or outcomes collected.
Purpose: discover whether an external developer can install the actual evaluation
artifact, understand acceptance/failure and get repeat value from one bounded
engineering workflow. This is descriptive product learning, not a confirmatory
research experiment or a release qualification substitute.

## Before recruitment

Name a coordinator and select one exact artifact/commit/digest, edition, evaluation
terms, supported host and provider. Use the existing #427 scope and release lanes;
do not infer authorization from this protocol. If only an authorized development
checkout is available, label the cohort a source-checkout pilot and leave the
released-artifact installation criterion untested.

Freeze the onboarding instructions, task template and collection fields before
the first attempt. Agree credential/data handling and any cost ceiling before live
inference. Use synthetic or participant-owned disposable repositories. Each
participant controls their own account and approvals; never collect their secrets.

Recruit five external developers who already use a coding agent and have a small
task they want to complete. Prefer several existing workflows within the admitted
support matrix. Maintainers and development swarm agents are not external users.
Avoid claiming platform coverage from five participants.

## Session sequence

1. **Capture baseline.** Record pseudonymous participant ID, prior agent workflow,
   supported host, exact artifact identity and onboarding document revision. Agree
   a useful task with objective checks, allowed files, budget and stop condition.
2. **Observe installation.** Start the clock when the participant opens the guide.
   Include download/setup time; record it separately if prerequisites dominate.
   Do not coach. If help is needed, record it and continue as an assisted attempt.
   Stop the unaided measurement at 15 minutes; preserve the outcome.
3. **Demonstrate understanding.** Run the deterministic first example, then ask:
   what was checked, what was allowed, and what does this result not prove?
   Training success counts as onboarding only.
4. **Complete useful work.** Run the agreed bounded coding task through the selected
   live integration. Retain initial/final commits, diff, checks, acceptance state,
   evidence references, known/unknown usage and every manual intervention. A model
   saying 'done' is not task completion.
5. **Exercise failure.** In the disposable task, use a reviewed failure fixture or
   stop/retry path qualified for that artifact. Ask the user to explain the state
   and recover or stop safely. Do not kill production processes or invent live
   failure-injection authority from the protocol.
6. **Compare value.** Use a comparable task with the user's existing workflow.
   Alternate which workflow is tried first across participants; record task
   differences and learning effects. Report raw observations, not causal claims
   from unmatched tasks. Include setup time and intervention overhead.
7. **Observe return usage.** At 14 days, record whether they voluntarily ran a
   second real task. Mark `NOT_DUE` until the window ends. Distinguish prompted
   sessions from voluntary return. Do not silently count missing follow-up as
   success, and retain withdrawals in the cohort accounting.

No message or reminder is sent by this document. Contacting participants requires
the user's explicit instruction and the appropriate recipient checks.

## Scorecard

Use [pilot-results.csv](pilot-results.csv), initially five unstarted slots. Blank
measurements mean unknown, never zero. Keep contact information separately from
the public result record. Review/redact any evidence before sharing it.

| Measure | Definition | Proposed target |
| --- | --- | --- |
| Unaided onboarding | Correct example and evidence inspection, no live help, elapsed <=15 minutes | 4/5 enrolled participants |
| Useful completion | Predeclared real task checks met and result inspected/accepted by its user | 3/5 |
| Return | Voluntary second real task within 14 days of first session | 2/5 |
| Safety | No observed unauthorized acceptance, unacknowledged duplicate side effect, or false success | Any observation blocks expansion pending triage |
| Value | Time, cost, corrections or audit effort worth the added overhead to that participant | Describe individually; no invented numeric benefit threshold |

Always publish the numerator, denominator, assisted attempts, blocked attempts and
missing outcomes together. Results are tied to the cohort's artifact and documents.
Do not remove failures to meet the target or pool changed versions without saying so.
The targets are product-learning goals, not already approved v1 release gates.

## Feedback prompts

- What did you expect when you opened the first page?
- Where did you hesitate, and what did you think the system was doing?
- Could you identify the allowed files, budget and acceptance requirements?
- Could you distinguish agent output, verified result and accepted integration?
- Could you distinguish verified completion, safe stop, waiting for evidence and
  failure? A safe stop is not counted as useful task completion.
- After a failure, was the next safe action clear?
- What would make you choose this for your next task?
- What existing step did it save, and what new work did it introduce?

## Handling findings

Record symptom, exact artifact, reproduction, expected/observed behavior, severity,
evidence link, proposed owner and existing issue/PR. Reuse an existing lane where
one covers the finding. Credentials/security-sensitive details follow
[SECURITY.md](../../SECURITY.md), not a public pilot issue. Route ordinary setup
friction to onboarding, misleading claims to #477, integration defects to their
owner and authority/release failures to the existing release/security lane.

At cohort review, select at most three highest-impact adoption fixes. Preserve
the original scorecard, change the artifact/document identity and run a new cohort.
Only claim qualified platforms or measured benefits within their evidence scope.

## Invitation draft for owner review

I’m looking for developers to try RESIDUAL on a small coding task they already
care about. It checks bounded work and retains the evidence behind acceptance.
The pilot would cover installation, one useful task and feedback on where the
experience is confusing. I’ll specify the exact evaluation build, permitted use,
supported setup and any model costs before you start. This is an early evaluation;
your feedback will help determine what needs fixing before broader release.

This draft has not been sent. Replace the setup and session details with the
selected artifact's actual terms before using it.
